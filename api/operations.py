"""Versioned operation contracts shared by the bridge, queue and workflow editor."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from api.core.context import TaskCancelled, checkpoint, current_context, record_inputs, report_progress
from api.core.outputs import output_asset
from api.utils.error_handler import api_error, api_success


@dataclass
class OutputAsset:
    path: str
    name: str
    kind: str = 'file'
    exists: bool = True
    size: int | None = None


@dataclass
class TaskSnapshot:
    id: str
    method: str
    status: str
    progress: int | None = None
    current: int = 0
    total: int = 0
    outputs: list[dict] = field(default_factory=list)


@dataclass
class OperationDescriptor:
    id: str
    tool: str
    feature: str
    label: str
    fields: list[dict] = field(default_factory=list)
    batchKey: str | None = None


_CATALOG = json.loads(Path(__file__).with_name('operation_catalog.json').read_text(encoding='utf-8'))
OPERATIONS = {item['id']: OperationDescriptor(**item) for item in _CATALOG}

# Explicit legacy result contracts. Values identify outputs, never arbitrary text.
_OUTPUT_FIELDS = {
    'webauto_collect': ['outputPath'], 'webauto_export': ['outputPath'],
    'image_format_convert': ['files'], 'image_batch_compress': ['items.output'],
    'image_add_watermark': ['files'], 'image_rotate_flip': ['files'],
    'image_crop': ['file'], 'image_concat': ['file'], 'image_to_pdf': ['file'],
    'image_batch_rename': ['operations.to'],
    'excel_process': ['groupFiles', 'combinedPath', 'jsonPath'],
    'excel_merge_tables': ['output'], 'excel_split_by_column': ['files'],
    'excel_quality_report': ['output'], 'excel_column_profile': [],
    'pdf_convert_to_images': ['files'], 'pdf_convert_to_scan': ['files'],
    'pdf_compress': ['output'], 'pdf_merge': ['output'], 'pdf_split': ['files'],
    'pdf_cut': ['output'], 'pdf_multi_cut': ['files'], 'pdf_extract_text': ['output'],
    'pdf_to_word': ['output'], 'pdf_extract_images': ['files'],
    'pdf_page_workbench': ['output'], 'pdf_secure': ['output'],
    'word_split': ['files'], 'word_cut': ['output'], 'word_merge': ['output'],
    'ocr_image': ['output'], 'ocr_pdf': ['outputs'], 'ocr_table': ['outputs'],
    'seal_generate': ['output'],
    'video_format_convert': ['file'], 'video_compress': ['file'], 'video_cut': ['file'],
    'video_extract_audio': ['file'], 'video_concat': ['file'],
    'format_center_convert': ['files'], 'format_center_images_to_pdf': ['files'],
    'format_center_merge_pdfs': ['files'],
    'file_search': ['items.path'], 'file_batch_copy': [],
    'file_auto_classify': ['operations.to'], 'file_batch_rename': ['renamed.to'],
    'file_batch_rename_undo': ['restored.to'], 'file_classify_undo': ['restored.to'], 'file_compress': ['file'],
    'image_batch_rename_undo': ['files'],
    'file_decompress': ['files'], 'file_recycle_restore': ['restored.to'],
    'file_deduplicate': [], 'file_batch_delete': [], 'file_recycle_purge': [],
    'text_format_json': [], 'text_case_transform': [], 'text_deduplicate_sort': [],
    'text_batch_replace': [], 'document_index_build': [], 'workflow_run': [],
}


def _values(value, parts):
    if isinstance(value, list):
        for item in value:
            yield from _values(item, parts)
    elif not parts:
        if isinstance(value, str) and value:
            yield value
    elif isinstance(value, dict):
        yield from _values(value.get(parts[0]), parts[1:])


def enrich_result(method, result):
    if not isinstance(result, dict) or method not in OPERATIONS:
        return result
    result = dict(result)
    if 'outputAssets' not in result:
        paths = []
        for contract in _OUTPUT_FIELDS.get(method, []):
            paths.extend(_values(result, contract.split('.')))
        result['outputAssets'] = [output_asset(path) for path in dict.fromkeys(paths)]
    if result.get('dryRun'):
        result['outputAssets'] = []
    result['outputPaths'] = [asset['path'] for asset in result['outputAssets'] if asset.get('kind') != 'directory']
    directories = {str(Path(asset['path']).parent) for asset in result['outputAssets'] if asset.get('kind') != 'directory'}
    if len(directories) == 1 and not result.get('outputDir'):
        result['outputDir'] = directories.pop()
    if result.get('code', 0) != 0 and not result.get('errorCode'):
        result['errorCode'] = 'OPERATION_FAILED'
    return result


def execute_operation(method, handler, args):
    descriptor = OPERATIONS.get(method)
    options = args[0] if args and isinstance(args[0], dict) else {}
    batch_key = descriptor.batchKey if descriptor else None
    batch = options.get(batch_key) if batch_key else None
    if not isinstance(batch, list) or not batch:
        checkpoint()
        return enrich_result(method, handler(*args))
    results, failures, assets = [], [], []
    record_inputs([item.get('path', '') if isinstance(item, dict) else item for item in batch])
    combined = {}
    for index, item in enumerate(batch):
        report_progress(index, len(batch), f'正在处理第 {index + 1}/{len(batch)} 个文件')
        checkpoint()
        item_options = {**options, batch_key: [item]}
        try:
            result = enrich_result(method, handler(item_options, *args[1:]))
        except TaskCancelled:
            raise
        except Exception as exc:
            result = api_error(str(exc))
        success = isinstance(result, dict) and (result.get('code') == 0 or result.get('success') is True)
        input_path = item.get('path', '') if isinstance(item, dict) else str(item)
        results.append({'input': input_path, 'status': 'success' if success else 'failed',
                        'message': result.get('msg') or result.get('message') or '',
                        'outputs': result.get('outputAssets', [])})
        context = current_context()
        if context:
            context.emit(itemResult=results[-1])
        assets.extend(result.get('outputAssets', []))
        if not success:
            failures.append({'input': input_path, 'error': result.get('msg') or '处理失败'})
        for key, value in result.items():
            if isinstance(value, list):
                combined.setdefault(key, []).extend(value)
            else:
                combined[key] = value
    report_progress(len(batch), len(batch), '批次处理完成')
    succeeded = len(batch) - len(failures)
    combined.update(code=0 if succeeded else -1, msg=f'{succeeded} 个成功，{len(failures)} 个失败',
                    itemResults=results, failures=failures, partial=bool(succeeded and failures), outputAssets=assets)
    if not failures:
        combined.pop('errorCode', None)
    elif succeeded:
        combined['errorCode'] = 'PARTIAL_FAILURE'
    elif failures:
        combined['msg'] += '：' + failures[0]['error']
    return combined


class OperationService:
    def operations_list(self):
        from api.workflow import WORKFLOW_METHODS
        operations = []
        for item in OPERATIONS.values():
            preview = f'{item.id}_preview'
            if item.tool == 'image' and item.id in {'image_batch_compress', 'image_add_watermark', 'image_rotate_flip', 'image_crop', 'image_format_convert'}:
                preview = 'image_operation_preview'
            elif item.tool == 'word':
                preview = 'word_preview'
            elif item.id == 'pdf_page_workbench':
                preview = 'pdf_page_preview'
            dependencies = ['flyingmouse'] if item.tool == 'conversion' else ['ffmpeg', 'ffprobe'] if item.tool == 'video' else ['rapidocr'] if item.id.startswith('ocr_') else []
            operations.append({**asdict(item), 'workflow': item.id in WORKFLOW_METHODS, 'cancellable': True,
                               'preview': preview if hasattr(self._host, preview) else None, 'dependencies': dependencies,
                               'inputTypes': [field['type'] for field in item.fields if field['type'] in {'file', 'files', 'directory'}],
                               'outputTypes': ['asset'] if _OUTPUT_FIELDS.get(item.id) else ['data'],
                               'kind': 'query' if item.id in {'file_search', 'file_deduplicate', 'excel_column_profile'} else 'operation'})
        return api_success(schemaVersion=1, operations=operations)

    def operations_validate(self, options=None):
        options = options or {}
        method = options.get('method')
        descriptor = OPERATIONS.get(method)
        if descriptor is None:
            return api_error('未知操作', errorCode='UNKNOWN_OPERATION')
        args = options.get('args', {})
        if not isinstance(args, dict):
            return api_error('参数必须为对象', errorCode='INVALID_ARGUMENT')
        errors = []
        for field_info in descriptor.fields:
            value = args.get(field_info['name'])
            if value is None or value == '' or value == []:
                if field_info.get('required'):
                    errors.append(f'{field_info["label"]}不能为空')
                continue
            if isinstance(value, str) and '{{' in value:
                continue
            kind = field_info['type']
            if kind == 'number' and (isinstance(value, bool) or not isinstance(value, (int, float))):
                errors.append(f'{field_info["label"]}必须是数字')
            elif kind == 'number' and not math.isfinite(value):
                errors.append(f'{field_info["label"]}必须是有限数字')
            if kind == 'boolean' and not isinstance(value, bool):
                errors.append(f'{field_info["label"]}必须为开关值')
            if kind in {'files', 'list', 'paths', 'directories', 'tables'} and not isinstance(value, list):
                errors.append(f'{field_info["label"]}必须为列表')
            if kind == 'json' and not isinstance(value, (dict, list)):
                errors.append(f'{field_info["label"]}必须是对象或列表')
            if kind in {'object', 'mapping', 'mapping-number'} and not isinstance(value, dict):
                errors.append(f'{field_info["label"]}必须是映射对象')
            if kind == 'select' and field_info.get('options'):
                choices = [item.get('value') if isinstance(item, dict) else item for item in field_info['options']]
                if value not in choices:
                    errors.append(f'{field_info["label"]}不在支持的选项中')
            if kind == 'number' and isinstance(value, (int, float)) and not isinstance(value, bool):
                if field_info.get('min') is not None and value < field_info['min']:
                    errors.append(f'{field_info["label"]}不能小于 {field_info["min"]}')
                if field_info.get('max') is not None and value > field_info['max']:
                    errors.append(f'{field_info["label"]}不能大于 {field_info["max"]}')
        return api_error('；'.join(errors), errors=errors, errorCode='INVALID_ARGUMENT') if errors else api_success('参数检查通过')
