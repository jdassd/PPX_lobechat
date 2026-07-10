#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2025-07-04
Description: PDF 工具相关 API
'''

from datetime import datetime, timezone
import random
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List
import zipfile

import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from api.utils.validators import ensure_output_directory


class PDF():
    '''PDF 相关功能'''

    _image_formats = ('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp', 'gif', 'svg')
    _raster_image_formats = {
        'png': 'PNG',
        'jpg': 'JPEG',
        'jpeg': 'JPEG',
        'tiff': 'TIFF',
        'bmp': 'BMP',
        'webp': 'WEBP',
        'gif': 'GIF',
    }

    def _ensure_pdf_file(self, file_path: str) -> Path:
        if not file_path:
            raise ValueError('请选择 PDF 文件')
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'文件不存在：{path}')
        if path.suffix.lower() != '.pdf':
            raise ValueError('仅支持 PDF 文件')
        return path

    def _ensure_output_dir(self, source: Path, preferred: str, suffix: str) -> Path:
        # 复用通用输出目录创建逻辑，保持与其它模块一致
        return ensure_output_directory(source, preferred, suffix)

    def _resolve_output_path(self, source: Path, output_path: str, suffix: str) -> Path:
        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest = source.parent / f'{source.stem}_{suffix}_{self._timestamp()}.pdf'
        return dest

    def _compose_output_path(self, directory: str, filename: str) -> str:
        if directory and filename:
            safe_dir = Path(directory)
            safe_dir.mkdir(parents=True, exist_ok=True)
            safe_name = filename if filename.lower().endswith('.pdf') else f'{filename}.pdf'
            return str(safe_dir / safe_name)
        return ''

    def _timestamp(self) -> str:
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    def _pil_from_pixmap(self, pixmap: fitz.Pixmap) -> Image.Image:
        if pixmap.alpha:
            pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
        return Image.frombytes('RGB', [pixmap.width, pixmap.height], pixmap.samples)

    def _validate_image_export_format(self, value) -> str:
        fmt = str(value or 'png').strip().lower().lstrip('.')
        if fmt not in self._image_formats:
            raise ValueError(f'不支持的图片格式：{fmt}')
        if fmt == 'svg':
            return fmt

        Image.init()
        pil_format = self._raster_image_formats.get(fmt)
        if not pil_format or pil_format not in Image.SAVE:
            raise ValueError(f'当前环境不支持导出 {fmt.upper()} 图片')
        return fmt

    def _apply_scan_effect(self, image: Image.Image, noise_level: float, tilt: bool, texture: bool) -> Image.Image:
        img = image.convert('RGB')
        if tilt:
            angle = random.uniform(-1.2, 1.2)
            img = img.rotate(angle, expand=True, fillcolor='#f8f5ed')
        img = ImageEnhance.Color(img).enhance(0.92)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Brightness(img).enhance(1.04)
        if noise_level > 0:
            noise = Image.effect_noise(img.size, noise_level * 10)
            noise = noise.filter(ImageFilter.GaussianBlur(1.2))
            noise = ImageOps.colorize(noise, '#f9f6ef', '#dcd7c5')
            img = Image.blend(img, noise, 0.07)
        if texture:
            paper = Image.effect_noise(img.size, 2).filter(ImageFilter.GaussianBlur(3))
            paper = ImageOps.colorize(paper, '#fdfbf5', '#f0ebe0')
            img = Image.blend(img, paper, 0.05)
        return img

    def _write_simple_docx(self, paragraphs: List[str], dest: Path, title: str) -> None:
        """生成一个最小可用的 docx 文档，仅包含基本段落文本。"""
        from xml.sax.saxutils import escape as xml_escape

        dest.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        def _paragraph_xml(text: str) -> str:
            return f'<w:p><w:r><w:t>{xml_escape(text)}</w:t></w:r></w:p>'

        body_xml = '\n'.join(_paragraph_xml(line) for line in paragraphs)
        document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
{body_xml}
    <w:sectPr/>
  </w:body>
</w:document>
'''
        content_types_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
'''
        rels_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'''
        core_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:dcmitype="http://purl.org/dc/dcmitype"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_escape(title)}</dc:title>
  <dc:creator>PPX</dc:creator>
  <cp:lastModifiedBy>PPX</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
'''
        app_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>PPX</Application>
</Properties>
'''
        doc_rels_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>
'''

        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', content_types_xml)
            zf.writestr('_rels/.rels', rels_xml)
            zf.writestr('docProps/core.xml', core_xml)
            zf.writestr('docProps/app.xml', app_xml)
            zf.writestr('word/document.xml', document_xml)
            zf.writestr('word/_rels/document.xml.rels', doc_rels_xml)

    def _parse_page_spec(self, spec: str, total_pages: int) -> List[int]:
        pages: List[int] = []
        if not spec:
            return pages
        for chunk in spec.replace('，', ',').split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                if '-' in chunk:
                    start_str, end_str = chunk.split('-', 1)
                    start = int(start_str.strip())
                    end = int(end_str.strip())
                    if start > end:
                        start, end = end, start
                    for page in range(start, end + 1):
                        if 1 <= page <= total_pages:
                            pages.append(page)
                else:
                    page = int(chunk)
                    if 1 <= page <= total_pages:
                        pages.append(page)
            except (ValueError, TypeError):
                # 忽略无效的页码格式
                continue
        # 去重并保持顺序
        unique_pages: List[int] = []
        seen = set()
        for page in pages:
            if page not in seen:
                seen.add(page)
                unique_pages.append(page)
        return unique_pages

    def _validate_payload(self, options: Dict) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _guess_page_title(self, page, page_no: int) -> str:
        """
        尝试根据字体大小 / 位置，推断当前页面的“标题”文本，用于自动生成目录。
        规则尽量温和：优先取页面上方、字号较大的非空文本，失败时退回到首行文本。
        """
        best = None
        try:
            data = page.get_text('dict')
        except Exception:
            data = None

        if isinstance(data, dict):
            for block in data.get('blocks', []):
                # type 0 为文本块，其余为图片等
                if block.get('type', 0) != 0:
                    continue
                bbox = block.get('bbox') or [0, 0, 0, 0]
                top = float(bbox[1]) if len(bbox) >= 2 else 0.0
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        text = (span.get('text') or '').strip()
                        if not text:
                            continue
                        # 过滤明显无意义的内容：纯数字页码等
                        if len(text) <= 1:
                            continue
                        if text.isdigit() and len(text) <= 4:
                            continue
                        # 简单过滤常见页码样式：Page 1 / 第 1 页
                        normalized = ''.join(ch for ch in text if not ch.isspace())
                        lower_norm = normalized.lower()
                        if lower_norm.startswith('page') and lower_norm[4:].strip().isdigit():
                            continue
                        # 记录候选项：字号越大、位置越靠上优先
                        try:
                            size = float(span.get('size') or 0)
                        except (TypeError, ValueError):
                            size = 0.0
                        if size <= 0:
                            continue
                        candidate = {'text': text, 'size': size, 'top': top}
                        if best is None:
                            best = candidate
                        else:
                            if size > best['size'] + 0.5:
                                best = candidate
                            elif abs(size - best['size']) <= 0.5 and top < best['top'] - 2:
                                best = candidate

        if best is not None:
            return best['text'].strip()

        # 兜底：使用首个有效的文本行作为标题
        try:
            raw = page.get_text('text') or ''
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                if len(line) <= 1:
                    continue
                if line.isdigit() and len(line) <= 4:
                    continue
                return line
        except Exception:
            pass

        return ''

    def pdf_convert_to_images(self, options: Dict = None):
        '''PDF 转高清图片'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            output_dir = opts.get('outputDir', '')
            dpi = int(opts.get('dpi') or 320)
            fmt = self._validate_image_export_format(opts.get('format') or 'png')
            max_pages = int(opts.get('maxPages') or 0)

            source = self._ensure_pdf_file(file_path)
            out_dir = self._ensure_output_dir(source, output_dir, 'images')

            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)

            exported: List[str] = []
            with fitz.open(source) as doc:
                total_pages = doc.page_count
                limit = total_pages if max_pages <= 0 else min(total_pages, max_pages)
                for index in range(limit):
                    page = doc.load_page(index)
                    filename = f'{source.stem}_p{index + 1:03}.{fmt}'
                    dest = out_dir / filename
                    if fmt == 'svg':
                        svg_text = page.get_svg_image(matrix=matrix)
                        dest.write_text(svg_text, encoding='utf-8')
                    else:
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        image = self._pil_from_pixmap(pix)
                        save_kwargs = {'quality': 95} if fmt in ('jpg', 'jpeg', 'webp') else {}
                        image.save(dest, format=self._raster_image_formats[fmt], **save_kwargs)
                    exported.append(str(dest))

            return {
                'code': 0,
                'msg': f'已导出 {len(exported)} 张图片',
                'files': exported,
                'outputDir': str(out_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'转换失败：{exc}'}

    def pdf_convert_to_scan(self, options: Dict = None):
        '''PDF 转扫描件效果'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            output_dir = opts.get('outputDir', '')
            dpi = int(opts.get('dpi') or 220)
            fmt = str(opts.get('format') or 'jpg').lower()
            tilt = bool(opts.get('tilt', True))
            texture = bool(opts.get('texture', True))
            noise = float(opts.get('noise') or 6)
            if fmt not in self._image_formats:
                fmt = 'jpg'

            source = self._ensure_pdf_file(file_path)
            out_dir = self._ensure_output_dir(source, output_dir, 'scan')

            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)

            exported: List[str] = []
            with fitz.open(source) as doc:
                for index in range(doc.page_count):
                    page = doc.load_page(index)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    image = self._pil_from_pixmap(pix)
                    scanned = self._apply_scan_effect(image, noise, tilt, texture)
                    filename = f'{source.stem}_scan_{index + 1:03}.{fmt}'
                    dest = out_dir / filename
                    save_kwargs = {'quality': 95} if fmt in ('jpg', 'jpeg') else {}
                    scanned.save(dest, **save_kwargs)
                    exported.append(str(dest))

            return {
                'code': 0,
                'msg': f'扫描件效果已生成 {len(exported)} 张',
                'files': exported,
                'outputDir': str(out_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'生成失败：{exc}'}

    def pdf_merge(self, options: Dict = None):
        '''多个 PDF 合并'''
        try:
            opts = self._validate_payload(options)
            files = opts.get('files', [])
            output_path = opts.get('outputPath') or self._compose_output_path(
                opts.get('outputDir', ''), opts.get('outputName', '')
            )
            if not isinstance(files, Iterable):
                raise ValueError('参数格式错误')
            candidates = list(files)
            if len(candidates) < 2:
                raise ValueError('请至少选择 2 个 PDF 文件')

            # 兼容旧格式（直接传路径字符串）与新格式（{path, pageSpec}）
            merge_entries = []
            for item in candidates:
                if isinstance(item, dict):
                    path = item.get('path', '')
                    page_spec = str(item.get('pageSpec') or '').strip()
                else:
                    path = str(item)
                    page_spec = ''
                pdf_path = self._ensure_pdf_file(path)
                merge_entries.append({'path': pdf_path, 'page_spec': page_spec})

            dest = self._resolve_output_path(merge_entries[0]['path'], output_path, 'merged')
            writer = PdfWriter()
            merged_pages = 0
            for entry in merge_entries:
                pdf = entry['path']
                reader = PdfReader(str(pdf))
                total = len(reader.pages)
                if entry['page_spec']:
                    pages = self._parse_page_spec(entry['page_spec'], total)
                else:
                    pages = list(range(1, total + 1))
                if not pages:
                    continue
                for page_no in pages:
                    idx = page_no - 1
                    if 0 <= idx < total:
                        writer.add_page(reader.pages[idx])
                        merged_pages += 1

            if merged_pages == 0:
                raise ValueError('未选择有效的页码')

            with dest.open('wb') as fp:
                writer.write(fp)

            return {
                'code': 0,
                'msg': f'合并成功，共 {len(merge_entries)} 个文件，合并 {merged_pages} 页',
                'output': str(dest),
                'mergedPages': merged_pages,
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'合并失败：{exc}'}

    def pdf_split(self, options: Dict = None):
        '''PDF 拆分为多个文件'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            output_dir = opts.get('outputDir', '')
            pages_per_file = int(opts.get('pagesPerFile') or 1)
            pages_per_file = max(1, pages_per_file)

            source = self._ensure_pdf_file(file_path)
            out_dir = self._ensure_output_dir(source, output_dir, 'split')

            reader = PdfReader(str(source))
            total = len(reader.pages)
            exported: List[str] = []
            part = 1
            for start in range(0, total, pages_per_file):
                writer = PdfWriter()
                end = min(start + pages_per_file, total)
                for page in range(start, end):
                    writer.add_page(reader.pages[page])
                dest = out_dir / f'{source.stem}_part{part:03}.pdf'
                with dest.open('wb') as fp:
                    writer.write(fp)
                exported.append(str(dest))
                part += 1

            return {
                'code': 0,
                'msg': f'拆分完成，共 {len(exported)} 个文件',
                'files': exported,
                'outputDir': str(out_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'拆分失败：{exc}'}

    def pdf_cut(self, options: Dict = None):
        '''按页码切割 PDF'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            output_path = opts.get('outputPath') or self._compose_output_path(
                opts.get('outputDir', ''), opts.get('outputName', '')
            )
            mode = opts.get('mode', 'range')
            start_page = int(opts.get('startPage') or 1)
            end_page = int(opts.get('endPage') or start_page)
            page_spec = str(opts.get('pageSpec') or '')

            source = self._ensure_pdf_file(file_path)
            reader = PdfReader(str(source))
            total = len(reader.pages)

            if mode == 'range':
                start = max(1, start_page)
                end = min(total, end_page)
                if start > end:
                    raise ValueError('开始页不能大于结束页')
                targets = list(range(start, end + 1))
            else:
                targets = self._parse_page_spec(page_spec, total)

            if not targets:
                raise ValueError('请设置有效的页码')

            writer = PdfWriter()
            for page_no in targets:
                idx = page_no - 1
                if 0 <= idx < total:
                    writer.add_page(reader.pages[idx])

            suffix = 'range' if mode == 'range' else 'custom'
            dest = self._resolve_output_path(source, output_path, suffix)
            with dest.open('wb') as fp:
                writer.write(fp)

            return {'code': 0, 'msg': f'已导出 {len(targets)} 页', 'output': str(dest)}
        except Exception as exc:
            return {'code': -1, 'msg': f'切割失败：{exc}'}

    def pdf_multi_cut(self, options: Dict = None):
        '''按多个页码区间或页码集合一次性切割为多个 PDF 文件'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            mode = opts.get('mode', 'custom')
            page_spec = str(opts.get('pageSpec') or '')

            if mode != 'custom':
                # 仅在自定义页码模式下才有意义，其余情况直接提示前端继续走 pdf_cut
                raise ValueError('多文件切割仅支持自定义页码模式')

            source = self._ensure_pdf_file(file_path)
            reader = PdfReader(str(source))
            total = len(reader.pages)

            raw = page_spec.replace('\r', '\n')
            # 使用分号或换行分隔多个区间，每个区间内部沿用原有 pageSpec 语法（1-3,5,8）
            segments_raw = []
            for line in raw.split('\n'):
                line = line.strip()
                if not line:
                    continue
                segments_raw.extend(part.strip() for part in line.split(';') if part.strip())

            segment_pages: List[List[int]] = []
            for seg in segments_raw:
                pages = self._parse_page_spec(seg, total)
                if pages:
                    segment_pages.append(pages)

            if not segment_pages:
                raise ValueError('未提供有效的页码区间')

            output_dir_opt = opts.get('outputDir', '')
            if output_dir_opt:
                out_dir = Path(output_dir_opt)
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = self._ensure_output_dir(source, '', 'cut')

            base_name = opts.get('outputName') or source.stem
            if base_name.lower().endswith('.pdf'):
                base_name = base_name[:-4]

            exported: List[str] = []
            for index, pages in enumerate(segment_pages, start=1):
                writer = PdfWriter()
                for page_no in pages:
                    idx = page_no - 1
                    if 0 <= idx < total:
                        writer.add_page(reader.pages[idx])
                filename = f'{base_name}_part{index:02}.pdf'
                dest = out_dir / filename
                with dest.open('wb') as fp:
                    writer.write(fp)
                exported.append(str(dest))

            return {
                'code': 0,
                'msg': f'已按 {len(exported)} 个区间导出 {len(exported)} 个 PDF',
                'files': exported,
                'outputDir': str(out_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'页码多文件切割失败：{exc}'}

    def pdf_compress(self, options: Dict = None):
        '''通过图片栅格化压缩 PDF'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            mode = str(opts.get('mode') or 'medium')
            custom_dpi = int(opts.get('customDpi') or 200)
            output_path = opts.get('outputPath') or self._compose_output_path(
                opts.get('outputDir', ''), opts.get('outputName', '')
            )

            dpi_presets = {
                'low': 280,      # 压缩率低：更高清
                'medium': 200,   # 平衡
                'high': 130      # 压缩率高：更小
            }
            quality_presets = {
                'low': 92,
                'medium': 88,
                'high': 82,
                'custom': 90
            }

            if mode == 'custom':
                dpi = max(72, min(400, custom_dpi))
            else:
                dpi = dpi_presets.get(mode, dpi_presets['medium'])
            jpg_quality = quality_presets.get(mode, quality_presets['medium'])

            source = self._ensure_pdf_file(file_path)
            dest = self._resolve_output_path(source, output_path, 'compressed')

            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)

            result_doc = fitz.open()
            try:
                with fitz.open(source) as doc:
                    if doc.page_count == 0:
                        raise ValueError('PDF 内无页面')
                    for page_index in range(doc.page_count):
                        page = doc.load_page(page_index)
                        pix = page.get_pixmap(matrix=matrix, alpha=False)
                        image = self._pil_from_pixmap(pix)
                        buffer = BytesIO()
                        image.save(buffer, format='JPEG', quality=jpg_quality)
                        img_bytes = buffer.getvalue()
                        new_page = result_doc.new_page(width=page.rect.width, height=page.rect.height)
                        new_page.insert_image(new_page.rect, stream=img_bytes)

                if result_doc.page_count == 0:
                    raise ValueError('压缩失败：生成页面为空')
                result_doc.save(str(dest))
            finally:
                result_doc.close()

            return {
                'code': 0,
                'msg': f'压缩完成，DPI={dpi}',
                'output': str(dest),
                'dpi': dpi
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'压缩失败：{exc}'}

    def pdf_extract_text(self, options: Dict = None):
        '''提取 PDF 文本'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_pdf_file(opts.get('filePath', ''))
            page_spec = str(opts.get('pageSpec') or '').strip()
            start_page = int(opts.get('startPage') or 1)
            end_page = int(opts.get('endPage') or start_page)
            text_mode = str(opts.get('textMode', 'plain')).lower()
            save_file = bool(opts.get('saveFile', True))
            segments: List[Dict] = []
            with fitz.open(source) as doc:
                total = doc.page_count
                if page_spec:
                    pages = self._parse_page_spec(page_spec, total)
                else:
                    start = max(1, start_page)
                    end = min(total, max(start, end_page))
                    pages = list(range(start, end + 1))
                if not pages:
                    pages = list(range(1, total + 1))
                for page_no in pages:
                    page = doc.load_page(page_no - 1)
                    if text_mode == 'markdown':
                        content = page.get_text('markdown')
                    elif text_mode == 'html':
                        content = page.get_text('html')
                    elif text_mode == 'blocks':
                        blocks = page.get_text('blocks')
                        content = '\n'.join(block[4] for block in blocks if len(block) > 4)
                    else:
                        content = page.get_text('text')
                    segments.append({
                        'page': page_no,
                        'content': content.strip()
                    })
            joined = '\n\n'.join(f'=== Page {seg["page"]} ===\n{seg["content"]}' for seg in segments)
            preview = joined[:2000]
            output_path = ''
            if save_file:
                out_dir = self._ensure_output_dir(source, opts.get('outputDir', ''), 'text')
                filename = opts.get('outputName') or f'{source.stem}_text.txt'
                if not filename.lower().endswith('.txt'):
                    filename = f'{filename}.txt'
                dest = out_dir / filename
                with dest.open('w', encoding='utf-8') as handler:
                    handler.write(joined)
                output_path = str(dest)
            return {
                'code': 0,
                'msg': '文本提取完成',
                'pages': len(segments),
                'preview': preview,
                'segments': segments[:min(len(segments), 10)],
                'output': output_path
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'文本提取失败：{exc}'}


    def pdf_to_word(self, options: Dict = None):
        '''PDF 转 Word 文档'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_pdf_file(opts.get('filePath', ''))
            text_mode = str(opts.get('textMode', 'plain')).lower()
            if text_mode not in {'plain', 'markdown', 'html'}:
                text_mode = 'plain'
            output_dir = opts.get('outputDir', '')
            out_dir = self._ensure_output_dir(source, output_dir, 'word')
            output_name = opts.get('outputName') or f'{source.stem}.docx'
            if not output_name.lower().endswith('.docx'):
                output_name = f'{output_name}.docx'
            dest = out_dir / output_name

            paragraphs: List[str] = []
            with fitz.open(source) as doc:
                total = doc.page_count
                for page_no in range(total):
                    page = doc.load_page(page_no)
                    if text_mode == 'markdown':
                        content = page.get_text('markdown')
                    elif text_mode == 'html':
                        content = page.get_text('html')
                    else:
                        content = page.get_text('text')
                    lines = (content or '').splitlines()
                    for line in lines:
                        paragraphs.append(line.rstrip())
                    if lines:
                        paragraphs.append('')  # 页面间空行分隔

            if not paragraphs:
                paragraphs.append('（文档无可提取文本）')

            self._write_simple_docx(paragraphs, dest, title=source.name)

            return {
                'code': 0,
                'msg': '已生成 Word 文档',
                'output': str(dest),
                'outputDir': str(out_dir),
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'转换失败：{exc}'}
    def pdf_extract_images(self, options: Dict = None):
        '''提取 PDF 内嵌图片'''
        try:
            opts = self._validate_payload(options)
            source = self._ensure_pdf_file(opts.get('filePath', ''))
            page_spec = str(opts.get('pageSpec') or '').strip()
            start_page = int(opts.get('startPage') or 1)
            end_page = int(opts.get('endPage') or start_page)
            img_format = str(opts.get('format') or 'png').lower()
            if img_format not in self._image_formats:
                img_format = 'png'
            min_width = int(opts.get('minWidth') or 0)
            min_height = int(opts.get('minHeight') or 0)
            out_dir = self._ensure_output_dir(source, opts.get('outputDir', ''), 'images')
            exported: List[str] = []
            with fitz.open(source) as doc:
                total = doc.page_count
                if page_spec:
                    pages = self._parse_page_spec(page_spec, total)
                else:
                    start = max(1, start_page)
                    end = min(total, max(start, end_page))
                    pages = list(range(start, end + 1))
                if not pages:
                    pages = list(range(1, total + 1))
                for page_no in pages:
                    page = doc.load_page(page_no - 1)
                    images = page.get_images(full=True)
                    for idx, img in enumerate(images, start=1):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        if min_width and pix.width < min_width:
                            continue
                        if min_height and pix.height < min_height:
                            continue
                        if pix.alpha:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        filename = f'{source.stem}_p{page_no}_{idx}.{img_format}'
                        dest = out_dir / filename
                        pix.save(dest)
                        exported.append(str(dest))
                        pix = None
            return {
                'code': 0,
                'msg': f'已导出 {len(exported)} 张图片',
                'files': exported[:50],
                'count': len(exported),
                'outputDir': str(out_dir)
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'提取图片失败：{exc}'}
