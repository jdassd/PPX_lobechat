#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline OCR for images and scanned PDFs."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from api.utils.error_handler import api_success, safe_execute


class OcrMixin:
    """RapidOCR-backed local text recognition with optional searchable PDF output."""

    _ocr_engine = None
    _ocr_lock = threading.Lock()

    @classmethod
    def _get_ocr_engine(cls):
        if cls._ocr_engine is not None:
            return cls._ocr_engine
        with cls._ocr_lock:
            if cls._ocr_engine is None:
                try:
                    from rapidocr import RapidOCR
                except ImportError as exc:
                    raise RuntimeError('离线 OCR 组件未安装，请重新安装 v2.0.0 完整版') from exc
                cls._ocr_engine = RapidOCR()
        return cls._ocr_engine

    @staticmethod
    def _validate_options(options: Dict | None) -> Dict:
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    @staticmethod
    def _source_path(options: Dict, allowed: Sequence[str]) -> Path:
        raw = options.get('filePath') or options.get('file')
        if isinstance(raw, dict):
            raw = raw.get('path')
        if not raw:
            raise ValueError('请选择源文件')
        source = Path(str(raw)).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f'文件不存在：{source}')
        if source.suffix.lower() not in allowed:
            raise ValueError(f'不支持的文件格式：{source.suffix or "未知"}')
        return source

    @staticmethod
    def _unique_output(source: Path, options: Dict, marker: str, extension: str) -> Path:
        raw_dir = options.get('outputDir')
        output_dir = Path(str(raw_dir)).expanduser() if raw_dir else source.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        custom_name = str(options.get('outputName') or '').strip()
        if custom_name:
            filename = Path(custom_name).name
            if not filename.lower().endswith(extension.lower()):
                filename += extension
        else:
            filename = f'{source.stem}_{marker}{extension}'
        target = output_dir / filename
        index = 2
        while target.exists() or target.is_symlink():
            target = output_dir / f'{Path(filename).stem}_{index}{extension}'
            index += 1
        return target

    @staticmethod
    def _parse_result(result) -> List[Dict]:
        if result is None:
            return []
        boxes = getattr(result, 'boxes', None)
        texts = getattr(result, 'txts', None)
        scores = getattr(result, 'scores', None)
        if texts is None and isinstance(result, (tuple, list)) and result:
            rows = result[0] if len(result) == 2 else result
            parsed = []
            for row in rows or []:
                if not isinstance(row, (tuple, list)) or len(row) < 2:
                    continue
                box = row[0]
                text_score = row[1]
                text = text_score[0] if isinstance(text_score, (tuple, list)) else text_score
                score = text_score[1] if isinstance(text_score, (tuple, list)) and len(text_score) > 1 else 0
                parsed.append({'box': box, 'text': str(text), 'score': float(score or 0)})
            return parsed
        texts = list(texts) if texts is not None else []
        boxes = list(boxes) if boxes is not None else [None] * len(texts)
        scores = list(scores) if scores is not None else [0] * len(texts)
        return [
            {'box': boxes[index] if index < len(boxes) else None, 'text': str(text), 'score': float(scores[index] or 0)}
            for index, text in enumerate(texts)
            if str(text).strip()
        ]

    @classmethod
    def _recognize(cls, image) -> List[Dict]:
        import numpy as np

        result = cls._get_ocr_engine()(np.asarray(image.convert('RGB')))
        return cls._parse_result(result)

    @staticmethod
    def _summary(lines: Iterable[Dict]) -> Dict:
        rows = list(lines)
        text = '\n'.join(row['text'] for row in rows)
        average = sum(row['score'] for row in rows) / len(rows) if rows else 0
        return {
            'text': text,
            'preview': text[:4000],
            'lineCount': len(rows),
            'averageConfidence': round(average, 4),
        }

    @staticmethod
    def _parse_pages(page_spec: str, total: int) -> List[int]:
        if not page_spec or not page_spec.strip():
            return list(range(total))
        pages = []
        for part in page_spec.replace('，', ',').split(','):
            token = part.strip()
            if not token:
                continue
            if '-' in token:
                start_text, end_text = token.split('-', 1)
                start, end = int(start_text), int(end_text)
                if start > end:
                    start, end = end, start
                pages.extend(range(start - 1, end))
            else:
                pages.append(int(token) - 1)
        unique = []
        for page in pages:
            if page < 0 or page >= total:
                raise ValueError(f'页码超出范围：{page + 1}（共 {total} 页）')
            if page not in unique:
                unique.append(page)
        if not unique:
            raise ValueError('未选择有效页码')
        return unique

    @safe_execute
    def ocr_image(self, options=None):
        from PIL import Image

        opts = self._validate_options(options)
        source = self._source_path(opts, ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'))
        with Image.open(source) as image:
            lines = self._recognize(image)
        summary = self._summary(lines)
        output = ''
        if bool(opts.get('saveFile', True)):
            target = self._unique_output(source, opts, 'ocr', '.txt')
            target.write_text(summary['text'], encoding='utf-8')
            output = str(target)
        return api_success('OCR 识别完成', output=output, **summary)

    @staticmethod
    def _insert_searchable_text(page, lines: List[Dict], pixel_width: int, pixel_height: int) -> None:
        import fitz

        scale_x = page.rect.width / max(1, pixel_width)
        scale_y = page.rect.height / max(1, pixel_height)
        for line in lines:
            box = line.get('box')
            text = line.get('text', '').strip()
            if box is None or not text:
                continue
            try:
                xs = [float(point[0]) for point in box]
                ys = [float(point[1]) for point in box]
                rect = fitz.Rect(min(xs) * scale_x, min(ys) * scale_y, max(xs) * scale_x, max(ys) * scale_y)
                if rect.is_empty or rect.is_infinite:
                    continue
                font_size = max(4.0, min(24.0, rect.height * 0.8))
                page.insert_textbox(rect, text, fontsize=font_size, fontname='china-s', render_mode=3, overlay=True)
            except Exception:
                # A malformed OCR box should not make the whole document fail.
                continue

    @safe_execute
    def ocr_pdf(self, options=None):
        import fitz
        from PIL import Image

        opts = self._validate_options(options)
        source = self._source_path(opts, ('.pdf',))
        dpi = max(120, min(400, int(opts.get('dpi') or 220)))
        mode = str(opts.get('outputMode') or 'both').lower()
        if mode not in {'text', 'searchable_pdf', 'both'}:
            raise ValueError('输出模式仅支持 text、searchable_pdf 或 both')

        source_doc = fitz.open(source)
        output_doc = None
        try:
            pages = self._parse_pages(str(opts.get('pageSpec') or ''), source_doc.page_count)
            if mode in {'searchable_pdf', 'both'}:
                output_doc = fitz.open()
                output_doc.insert_pdf(source_doc)
            page_results = []
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            for page_index in pages:
                page = source_doc.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
                lines = self._recognize(image)
                page_results.append({'page': page_index + 1, 'lines': lines})
                if output_doc is not None:
                    self._insert_searchable_text(output_doc.load_page(page_index), lines, pixmap.width, pixmap.height)

            text = '\n\n'.join(
                f'--- 第 {item["page"]} 页 ---\n' + '\n'.join(line['text'] for line in item['lines'])
                for item in page_results
            )
            scores = [line['score'] for item in page_results for line in item['lines']]
            outputs = []
            text_output = ''
            pdf_output = ''
            if mode in {'text', 'both'}:
                text_target = self._unique_output(source, opts, 'ocr', '.txt')
                text_target.write_text(text, encoding='utf-8')
                text_output = str(text_target)
                outputs.append(text_output)
            if output_doc is not None:
                pdf_target = self._unique_output(source, opts, 'searchable', '.pdf')
                output_doc.save(pdf_target, garbage=4, deflate=True)
                pdf_output = str(pdf_target)
                outputs.append(pdf_output)
            return api_success(
                'PDF OCR 完成',
                output=pdf_output or text_output,
                outputs=outputs,
                textOutput=text_output,
                pdfOutput=pdf_output,
                preview=text[:4000],
                pageCount=len(pages),
                lineCount=len(scores),
                averageConfidence=round(sum(scores) / len(scores), 4) if scores else 0,
            )
        finally:
            if output_doc is not None:
                output_doc.close()
            source_doc.close()
