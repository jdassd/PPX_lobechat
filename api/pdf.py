#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2025-07-04
Description: PDF 工具相关 API
'''

from datetime import datetime
import random
from pathlib import Path
from typing import Dict, Iterable, List

import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class PDF():
    '''PDF 相关功能'''

    _image_formats = ('png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp')

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
        if preferred:
            out_dir = Path(preferred)
        else:
            out_dir = source.parent / f'{source.stem}_{suffix}'
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

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

    def _parse_page_spec(self, spec: str, total_pages: int) -> List[int]:
        pages: List[int] = []
        if not spec:
            return pages
        for chunk in spec.replace('，', ',').split(','):
            chunk = chunk.strip()
            if not chunk:
                continue
            if '-' in chunk:
                start_str, end_str = chunk.split('-', 1)
                start = int(start_str)
                end = int(end_str)
                if start > end:
                    start, end = end, start
                for page in range(start, end + 1):
                    if 1 <= page <= total_pages:
                        pages.append(page)
            else:
                page = int(chunk)
                if 1 <= page <= total_pages:
                    pages.append(page)
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

    def pdf_convert_to_images(self, options: Dict = None):
        '''PDF 转高清图片'''
        try:
            opts = self._validate_payload(options)
            file_path = opts.get('filePath', '')
            output_dir = opts.get('outputDir', '')
            dpi = int(opts.get('dpi') or 320)
            fmt = str(opts.get('format') or 'png').lower()
            if fmt not in self._image_formats:
                fmt = 'png'

            source = self._ensure_pdf_file(file_path)
            out_dir = self._ensure_output_dir(source, output_dir, 'images')

            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)

            exported: List[str] = []
            with fitz.open(source) as doc:
                for index in range(doc.page_count):
                    page = doc.load_page(index)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    filename = f'{source.stem}_p{index + 1:03}.{fmt}'
                    dest = out_dir / filename
                    pix.save(dest)
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
            file_list = []
            for item in candidates:
                if isinstance(item, dict):
                    path = item.get('path', '')
                else:
                    path = str(item)
                file_list.append(self._ensure_pdf_file(path))

            dest = self._resolve_output_path(file_list[0], output_path, 'merged')
            writer = PdfWriter()
            for pdf in file_list:
                reader = PdfReader(str(pdf))
                for page in reader.pages:
                    writer.add_page(page)
            with dest.open('wb') as fp:
                writer.write(fp)

            return {
                'code': 0,
                'msg': f'合并成功，共 {len(file_list)} 个文件',
                'output': str(dest)
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
