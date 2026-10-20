"""CAJ conversion coverage for embedded-PDF containers and batch contracts."""
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fitz

from api.core.context import TaskContext, task_context
from api.operations import OPERATIONS, enrich_result
from api.pdf import PDF
from api.utils.caj import caj_to_pdf_bytes
from pyapp.config.config import Config


def make_embedded_pdf_caj(text='CAJ fixture text', pages=1, page_ids=None, parent_ids=None, extra_objects=b''):
    """Build the upstream CAJ layout: page count + pointer + object-only PDF."""
    objects = []
    for index in range(pages):
        page_number = page_ids[index] if page_ids else 3 + index * 3
        parent_number = parent_ids[index] if parent_ids else 2
        font_number = page_number + 1
        content_number = page_number + 2
        stream = f'BT /F1 18 Tf 35 180 Td ({text} {index + 1}) Tj ET'.encode('ascii')
        objects.extend([
            f'{page_number} 0 obj\r<< /Type /Page /Parent {parent_number} 0 R /MediaBox [0 0 300 240] '
            f'/Resources << /Font << /F1 {font_number} 0 R >> >> /Contents {content_number} 0 R >>\rendobj\r'.encode(),
            f'{font_number} 0 obj\r<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\rendobj\r'.encode(),
            f'{content_number} 0 obj\r<< /Length {len(stream)} >>\rstream\r\n'.encode() + stream + b'\r\nendstream\rendobj\r',
        ])
    payload = b''.join(objects) + extra_objects
    pointer_offset = 0x80
    embedded_offset = 0x100
    header = bytearray(embedded_offset)
    header[:4] = b'CAJ\0'
    struct.pack_into('<i', header, 0x10, pages)
    struct.pack_into('<i', header, 0x14, pointer_offset)
    struct.pack_into('<i', header, pointer_offset, embedded_offset)
    return bytes(header) + payload


class CajToPdfTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ppx-caj-pdf-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.api = PDF()

    def test_reconstructs_missing_pages_and_catalog_without_losing_page_content(self):
        source = self.root / 'paper.caj'
        source.write_bytes(make_embedded_pdf_caj(pages=2))

        result = self.api.pdf_caj_to_pdf({'files': [str(source)]})

        self.assertEqual(result['code'], 0, result)
        self.assertEqual(result['successCount'], 1)
        output = Path(result['files'][0])
        self.assertEqual(output.parent, source.parent)
        with fitz.open(output) as document:
            self.assertEqual(document.page_count, 2)
            self.assertIn('CAJ fixture text 1', document[0].get_text())
            self.assertIn('CAJ fixture text 2', document[1].get_text())
            self.assertGreater(len(document[0].get_pixmap().samples), 0)

    def test_malformed_hn_and_invalid_pdf_payloads_fail_without_outputs(self):
        malformed = self.root / 'malformed.caj'
        malformed.write_bytes(b'CAJ\0bad')
        unsupported = self.root / 'unsupported.caj'
        unsupported.write_bytes(b'KDH \0opaque')
        hn = self.root / 'scan.caj'
        hn.write_bytes(b'HN\xc8\0' + bytes(512))
        invalid_pdf = self.root / 'bad_pdf.caj'
        invalid_pdf.write_bytes(b'%PDF-1.7\nnot a PDF')

        result = self.api.pdf_caj_to_pdf({'files': [str(malformed), str(unsupported), str(hn), str(invalid_pdf)]})

        self.assertEqual(result['successCount'], 0, result)
        self.assertEqual(result['failedCount'], 4, result)
        self.assertTrue(any('不支持' in item['error'] for item in result['items']))
        self.assertTrue(any('HN/C8' in item['error'] for item in result['items']))
        self.assertFalse(list(self.root.glob('*.pdf')))
        self.assertFalse(list(self.root.glob('.*.tmp.pdf')))

    def test_missing_page_tree_preserves_payload_order_instead_of_object_id_order(self):
        output = caj_to_pdf_bytes(make_embedded_pdf_caj(pages=2, page_ids=[30, 3]))
        with fitz.open(stream=output, filetype='pdf') as document:
            self.assertIn('text 1', document[0].get_text())
            self.assertIn('text 2', document[1].get_text())

    def test_existing_intermediate_pages_node_can_reference_missing_root(self):
        intermediate = b'20 0 obj\r<< /Type /Pages /Parent 2 0 R /Kids [3 0 R 6 0 R] /Count 2 >>\rendobj\r'
        output = caj_to_pdf_bytes(make_embedded_pdf_caj(pages=2, parent_ids=[20, 20], extra_objects=intermediate))
        with fitz.open(stream=output, filetype='pdf') as document:
            self.assertEqual(document.page_count, 2)
            self.assertIn('text 2', document[1].get_text())

    def test_multiple_missing_parent_ids_do_not_collide_with_synthesized_root(self):
        output = caj_to_pdf_bytes(make_embedded_pdf_caj(pages=2, parent_ids=[9, 10]))
        with fitz.open(stream=output, filetype='pdf') as document:
            self.assertEqual(document.page_count, 2)
            self.assertIn('text 1', document[0].get_text())
            self.assertIn('text 2', document[1].get_text())

    def test_encrypted_payload_fails_without_publishing_pdf(self):
        source = self.root / 'encrypted.caj'
        with fitz.open() as document:
            document.new_page()
            source.write_bytes(document.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,
                                               user_pw='fixture-password', owner_pw='fixture-owner'))
        result = self.api.pdf_caj_to_pdf({'files': [str(source)]})
        self.assertEqual(result['failedCount'], 1, result)
        self.assertIn('加密', result['items'][0]['error'])
        self.assertFalse(list(self.root.glob('*.pdf')))

    def test_each_source_directory_remains_the_default_across_multiple_inputs(self):
        second_dir = self.root / 'other'
        second_dir.mkdir()
        sources = [self.root / 'a.caj', second_dir / 'b.caj']
        original = make_embedded_pdf_caj()
        for source in sources:
            source.write_bytes(original)
        result = self.api.pdf_caj_to_pdf({'files': [str(source) for source in sources]})
        self.assertEqual(result['output'], '')
        self.assertEqual([Path(path).parent for path in result['files']], [source.parent for source in sources])
        self.assertTrue(all(source.read_bytes() == original for source in sources))

    def test_cancelled_task_does_not_publish_output(self):
        source = self.root / 'cancelled.caj'
        source.write_bytes(make_embedded_pdf_caj())
        context = TaskContext()
        context.cancel.set()
        with task_context(context):
            self.api.pdf_caj_to_pdf({'files': [str(source)]})
        self.assertFalse(list(self.root.glob('*.pdf')))

    def test_pdf_signature_disguised_as_caj_is_repaired_and_output_conflicts_are_renamed(self):
        first = self.root / 'same.caj'
        second_dir = self.root / 'other'
        second_dir.mkdir()
        second = second_dir / 'same.caj'
        for source, label in ((first, 'first'), (second, 'second')):
            document = fitz.open()
            page = document.new_page()
            page.insert_text((30, 40), label)
            source.write_bytes(document.tobytes())
            document.close()

        result = self.api.pdf_caj_to_pdf({'files': [str(first), str(second)], 'outputDir': str(self.root / 'out')})

        self.assertEqual(result['successCount'], 2, result)
        self.assertEqual(result['output'], str(self.root / 'out'))
        self.assertEqual(Path(result['files'][0]).name, 'same.pdf')
        self.assertEqual(Path(result['files'][1]).name, 'same_2.pdf')
        with fitz.open(result['files'][0]) as document:
            self.assertIn('first', document[0].get_text())
        with fitz.open(result['files'][1]) as document:
            self.assertIn('second', document[0].get_text())

    def test_batch_failure_continues_and_retry_inputs_can_recover_failed_source(self):
        valid = self.root / 'valid.caj'
        broken = self.root / 'broken.caj'
        valid.write_bytes(make_embedded_pdf_caj())
        broken.write_bytes(b'not CAJ')

        first = self.api.pdf_caj_to_pdf({'files': [str(valid), str(broken)], 'outputDir': str(self.root / 'out')})

        self.assertEqual(first['successCount'], 1, first)
        self.assertEqual(first['failedCount'], 1, first)
        self.assertTrue(first['partial'])
        self.assertEqual([item['status'] for item in first['items']], ['success', 'error'])
        broken.write_bytes(make_embedded_pdf_caj('recovered'))

        retried = self.api.pdf_caj_to_pdf({'files': [str(valid), str(broken)],
                                           '_retryInputs': [str(broken)], 'outputDir': str(self.root / 'out')})

        self.assertEqual(retried['successCount'], 1, retried)
        self.assertEqual(retried['items'][0]['source'], str(broken))
        self.assertTrue(Path(retried['files'][0]).exists())

    def test_operation_is_available_for_workflows_with_selectable_file_results(self):
        self.assertIn('pdf_caj_to_pdf', OPERATIONS)
        result = enrich_result('pdf_caj_to_pdf', {'code': 0, 'files': [str(self.root / 'result.pdf')]})
        self.assertEqual(result['outputPaths'], [str(self.root / 'result.pdf')])

    def test_workflow_resume_retains_successful_pdf_and_merges_recovered_file(self):
        from api.api import API
        valid = self.root / 'valid.caj'
        broken = self.root / 'broken.caj'
        valid.write_bytes(make_embedded_pdf_caj('retained'))
        broken.write_bytes(b'HN unsupported')
        with mock.patch.object(Config, 'appDataDir', str(self.root / 'state')):
            api = API()
            self.addCleanup(api.task_shutdown)
            self.addCleanup(api.workflow_stop)
            saved = api.workflow_save({'name': 'CAJ to merged PDF', 'steps': [
                {'id': 'convert', 'method': 'pdf_caj_to_pdf', 'onPartial': 'stop',
                 'args': {'files': [str(valid), str(broken)], 'outputDir': str(self.root / 'out')}},
                {'id': 'merge', 'method': 'pdf_merge', 'args': {
                    'files': '{{steps.convert.outputPaths}}', 'outputDir': str(self.root / 'merged'), 'outputName': 'all.pdf'}},
            ]})['workflow']
            first = api.workflow_run({'id': saved['id']})
            self.assertTrue(first['partial'], first)
            retained = Path(first['context']['steps']['convert']['outputPaths'][0])
            original = retained.read_bytes()
            broken.write_bytes(make_embedded_pdf_caj('recovered'))
            resumed = api.workflow_run({'id': saved['id'], '_resumeRunId': first['run']['id']})
            self.assertEqual(resumed['run']['status'], 'success', resumed)
            self.assertEqual(resumed['run']['steps'][0]['resumeInfo']['processedInputCount'], 1)
            self.assertEqual(resumed['run']['steps'][0]['resumeInfo']['retainedOutputCount'], 1)
            self.assertEqual(retained.read_bytes(), original)
            with fitz.open(resumed['context']['steps']['merge']['output']) as document:
                self.assertEqual(document.page_count, 2)
                self.assertIn('retained', document[0].get_text())
                self.assertIn('recovered', document[1].get_text())


if __name__ == '__main__':
    unittest.main()
