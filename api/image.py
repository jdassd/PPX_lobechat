#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理相关 API
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFont, ImageOps

from api.utils import (
    ensure_files_payload,
    ensure_file_path,
    api_success,
    api_error,
    format_bytes,
    parse_percentage,
)


class ImageTool:
    """图片相关功能"""

    _valid_formats = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}
    _page_sizes = {
        'a4': (2480, 3508),   # 300 DPI
        'a5': (1748, 2480),
        'letter': (2550, 3300),
    }

    def _validate(self, options: Dict | None) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _prepare_output_dir(self, files: List[Path], preferred: str | None, suffix: str) -> Path:
        if preferred:
            output = Path(preferred)
            output.mkdir(parents=True, exist_ok=True)
            return output
        base = files[0].parent / suffix
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _save_image(self, image: Image.Image, dest: Path, fmt: str, quality: int | None = None):
        save_kwargs = {}
        if fmt in {'jpg', 'jpeg'}:
            image = image.convert('RGB')
            if quality:
                save_kwargs['quality'] = max(30, min(quality, 100))
            save_kwargs.setdefault('optimize', True)
        if fmt == 'png':
            save_kwargs.setdefault('compress_level', 6)
        image.save(dest, fmt.upper(), **save_kwargs)

    def _resolve_font(self, size: int, font_path: str | None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = []
        if font_path:
            candidates.append(font_path)
        candidates.extend([
            'msyh.ttc',
            'msyh.ttf',
            'Microsoft YaHei.ttf',
            'PingFang.ttc',
            'Arial.ttf',
        ])
        for candidate in candidates:
            if not candidate:
                continue
            try:
                return ImageFont.truetype(candidate, size)
            except (OSError, ValueError):
                continue
        return ImageFont.load_default()

    def _parse_color(self, value: str | None) -> Tuple[int, int, int]:
        try:
            return ImageColor.getrgb(value or '#FFFFFF')
        except ValueError:
            return 255, 255, 255

    def _resolve_position(
        self,
        base_size: Tuple[int, int],
        overlay_size: Tuple[int, int],
        position: str,
        margin: int = 24,
    ) -> Tuple[int, int]:
        width, height = base_size
        mark_w, mark_h = overlay_size
        pos = (position or 'bottom-right').lower()

        if 'left' in pos:
            x = margin
        elif 'right' in pos:
            x = max(margin, width - mark_w - margin)
        else:
            x = max(margin, (width - mark_w) // 2)

        if 'top' in pos:
            y = margin
        elif 'bottom' in pos:
            y = max(margin, height - mark_h - margin)
        else:
            y = max(margin, (height - mark_h) // 2)
        return x, y

    def _ensure_single_file(self, options: Dict) -> Path:
        raw = options.get('file')
        if isinstance(raw, dict):
            raw = raw.get('path')
        if raw:
            return ensure_file_path(raw)
        files = ensure_files_payload(options)
        return files[0]

    def _chunk(self, items: Sequence[Path], size: int) -> List[List[Path]]:
        return [list(items[idx: idx + size]) for idx in range(0, len(items), size)]

    def _resolve_page_size(self, options: Dict) -> Tuple[int, int]:
        label = str(options.get('pageSize', 'a4')).lower()
        if label == 'custom':
            width = max(300, int(options.get('customWidth') or 2480))
            height = max(300, int(options.get('customHeight') or 3508))
            return width, height
        return self._page_sizes.get(label, self._page_sizes['a4'])

    def _parse_ratio(self, value: str | None, width: int | None, height: int | None) -> Tuple[int, int]:
        if width and height:
            return max(1, width), max(1, height)
        if not value:
            return 1, 1
        try:
            part_a, part_b = value.split(':', 1)
            return max(1, int(part_a)), max(1, int(part_b))
        except (ValueError, TypeError):
            return 1, 1

    # -------------------- P0 功能 --------------------

    def image_format_convert(self, options: Dict | None = None):
        """图片格式转换"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            fmt = str(opts.get('targetFormat', 'png')).lower().lstrip('.')
            if fmt not in self._valid_formats:
                raise ValueError('不支持的目标格式')
            quality = opts.get('quality')
            try:
                quality = int(quality) if quality is not None else None
            except (TypeError, ValueError):
                quality = None

            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_convert')
            keep_name = bool(opts.get('keepName', True))
            rewritten = []
            for file_path in files:
                with Image.open(file_path) as image:
                    dest_name = f'{file_path.stem}.{fmt}' if keep_name else f'{file_path.stem}_{fmt}'
                    dest = output_dir / dest_name
                    self._save_image(image, dest, fmt, quality)
                    rewritten.append(str(dest))
            return api_success(f'已转换 {len(rewritten)} 个文件', files=rewritten, outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'转换失败：{exc}')

    def image_batch_resize(self, options: Dict | None = None):
        """批量缩放"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            mode = opts.get('mode', 'percent')
            keep_ratio = bool(opts.get('keepRatio', True))
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_resize')
            percent = parse_percentage(opts.get('percent', 100))
            width = opts.get('width')
            height = opts.get('height')

            resized = []
            for file_path in files:
                with Image.open(file_path) as image:
                    if mode == 'pixel':
                        new_width = int(width) if width else image.width
                        new_height = int(height) if height else image.height
                        if keep_ratio:
                            image = image.resize((new_width, new_height), Image.LANCZOS)
                        else:
                            image = image.resize((new_width, new_height))
                    else:
                        ratio = percent / 100.0
                        new_width = max(1, int(image.width * ratio))
                        new_height = max(1, int(image.height * ratio))
                        if keep_ratio:
                            image.thumbnail((new_width, new_height), Image.LANCZOS)
                        else:
                            image = image.resize((new_width, new_height))
                    dest = output_dir / f'{file_path.stem}_resize{file_path.suffix}'
                    self._save_image(image, dest, file_path.suffix.lstrip('.').lower())
                    resized.append(str(dest))
            return api_success(f'已缩放 {len(resized)} 个文件', files=resized, outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'缩放失败：{exc}')

    def image_batch_compress(self, options: Dict | None = None):
        """批量压缩"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            mode = opts.get('mode', 'quality')
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_compress')
            quality = int(opts.get('quality') or 80)
            quality = max(30, min(quality, 95))
            target_kb = opts.get('targetSizeKB')
            if target_kb:
                target_kb = max(16, int(target_kb))

            results = []
            for file_path in files:
                with Image.open(file_path) as image:
                    buffer = io.BytesIO()
                    if mode == 'size' and target_kb:
                        for level in range(quality, 30, -5):
                            buffer.seek(0)
                            buffer.truncate(0)
                            image.convert('RGB').save(buffer, 'JPEG', optimize=True, quality=level)
                            size_kb = buffer.tell() / 1024
                            if size_kb <= target_kb:
                                break
                        save_bytes = buffer.getvalue()
                        save_image = None
                    else:
                        save_bytes = None
                        save_image = image
                    dest_suffix = file_path.suffix if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'} else '.jpg'
                    dest = output_dir / f'{file_path.stem}_compress{dest_suffix}'
                    if mode == 'size' and target_kb:
                        with dest.open('wb') as handler:
                            handler.write(save_bytes if save_bytes is not None else buffer.getvalue())
                    else:
                        self._save_image(save_image, dest, dest_suffix.lstrip('.'), quality)
                    results.append({
                        'source': str(file_path),
                        'output': str(dest),
                        'originalSize': format_bytes(file_path.stat().st_size),
                        'compressedSize': format_bytes(dest.stat().st_size),
                    })
            return api_success(f'已压缩 {len(results)} 个文件', items=results, outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'压缩失败：{exc}')

    # -------------------- Phase 2 功能 --------------------

    def image_add_watermark(self, options: Dict | None = None):
        """批量添加文字或图片水印"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_watermark')
            watermark_type = str(opts.get('watermarkType', 'text')).lower()
            position = str(opts.get('position', 'bottom-right')).lower()
            opacity = max(5, min(int(opts.get('opacity') or 60), 100))
            font_size = max(8, int(opts.get('fontSize') or 32))
            color = self._parse_color(opts.get('color'))
            results = []

            wm_image_path = opts.get('watermarkImage')
            if isinstance(wm_image_path, dict):
                wm_image_path = wm_image_path.get('path')
            watermark_image = ensure_file_path(wm_image_path) if wm_image_path else None

            for file_path in files:
                with Image.open(file_path).convert('RGBA') as base:
                    overlay = Image.new('RGBA', base.size, (255, 255, 255, 0))
                    if watermark_type == 'image':
                        if not watermark_image:
                            raise ValueError('请提供水印图片')
                        with Image.open(watermark_image).convert('RGBA') as wm:
                            scale_percent = float(opts.get('scalePercent') or opts.get('scale') or 30)
                            scale_percent = max(5.0, min(scale_percent, 100.0)) / 100.0
                            target_width = max(10, int(base.width * scale_percent))
                            target_height = max(10, int(target_width * wm.height / wm.width))
                            wm_resized = wm.resize((target_width, target_height), Image.LANCZOS)
                            alpha_layer = wm_resized.getchannel('A') if 'A' in wm_resized.getbands() else Image.new('L', wm_resized.size, 255)
                            enhancer = ImageEnhance.Brightness(alpha_layer)
                            wm_resized.putalpha(enhancer.enhance(opacity / 100.0))
                            pos = self._resolve_position(base.size, wm_resized.size, position)
                            overlay.paste(wm_resized, pos, mask=wm_resized)
                    else:
                        text = str(opts.get('text') or '').strip()
                        if not text:
                            raise ValueError('请输入文字水印内容')
                        font = self._resolve_font(font_size, opts.get('fontPath'))
                        draw = ImageDraw.Draw(overlay)
                        bbox = draw.multiline_textbbox((0, 0), text, font=font)
                        mark_w = bbox[2] - bbox[0]
                        mark_h = bbox[3] - bbox[1]
                        pos = self._resolve_position(base.size, (mark_w, mark_h), position)
                        draw.multiline_text(
                            pos,
                            text,
                            font=font,
                            fill=(*color, int(255 * (opacity / 100.0))),
                            align='left',
                        )
                    composed = Image.alpha_composite(base, overlay)
                    fmt = file_path.suffix.lstrip('.').lower() or 'png'
                    dest = output_dir / f'{file_path.stem}_wm.{fmt}'
                    self._save_image(composed, dest, fmt)
                    results.append(str(dest))
            return api_success(f'已完成 {len(results)} 个文件水印', files=results, outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'水印处理失败：{exc}')

    def image_crop(self, options: Dict | None = None):
        """图片裁剪"""
        try:
            opts = self._validate(options)
            source = self._ensure_single_file(opts)
            output_dir = self._prepare_output_dir([source], opts.get('outputDir'), 'image_crop')
            mode = str(opts.get('mode', 'custom')).lower()
            with Image.open(source) as image:
                if mode == 'ratio':
                    ratio_w, ratio_h = self._parse_ratio(opts.get('ratio'), opts.get('ratioWidth'), opts.get('ratioHeight'))
                    base_w, base_h = image.size
                    target_w = base_w
                    target_h = int(target_w * ratio_h / ratio_w)
                    if target_h > base_h:
                        target_h = base_h
                        target_w = int(target_h * ratio_w / ratio_h)
                    x = max(0, (base_w - target_w) // 2)
                    y = max(0, (base_h - target_h) // 2)
                else:
                    x = max(0, int(opts.get('x') or 0))
                    y = max(0, int(opts.get('y') or 0))
                    width = int(opts.get('width') or image.width)
                    height = int(opts.get('height') or image.height)
                    target_w = max(1, min(width, image.width - x))
                    target_h = max(1, min(height, image.height - y))
                box = (x, y, x + target_w, y + target_h)
                cropped = image.crop(box)
                dest = output_dir / f'{source.stem}_crop{source.suffix}'
                self._save_image(cropped, dest, source.suffix.lstrip('.') or 'png')
            return api_success('裁剪完成', file=str(dest), outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'裁剪失败：{exc}')

    def image_rotate_flip(self, options: Dict | None = None):
        """旋转/翻转"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            operation = str(opts.get('operation', 'rotate90')).lower()
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_rotate')
            results = []
            for file_path in files:
                with Image.open(file_path) as image:
                    if operation == 'rotate180':
                        processed = image.rotate(180, expand=True)
                    elif operation == 'rotate270':
                        processed = image.rotate(270, expand=True)
                    elif operation == 'mirror':
                        processed = ImageOps.mirror(image)
                    elif operation == 'flip':
                        processed = ImageOps.flip(image)
                    else:
                        processed = image.rotate(90, expand=True)
                    dest = output_dir / f'{file_path.stem}_{operation}{file_path.suffix}'
                    self._save_image(processed, dest, file_path.suffix.lstrip('.') or 'png')
                    results.append(str(dest))
            return api_success(f'已处理 {len(results)} 张图片', files=results, outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'旋转/翻转失败：{exc}')

    def image_to_pdf(self, options: Dict | None = None):
        """图片集合导出为 PDF"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            per_page = int(opts.get('perPage') or 1)
            per_page = per_page if per_page in {1, 2, 4} else 1
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_pdf')
            page_width, page_height = self._resolve_page_size(opts)
            layout_map = {1: (1, 1), 2: (1, 2), 4: (2, 2)}
            columns, rows = layout_map.get(per_page, (1, 1))
            margin = int(opts.get('margin') or 36)

            pages: List[Image.Image] = []
            for chunk in self._chunk(files, per_page):
                canvas = Image.new('RGB', (page_width, page_height), 'white')
                cell_w = page_width // columns
                cell_h = page_height // rows
                for idx, img_path in enumerate(chunk):
                    row = idx // columns
                    col = idx % columns
                    region = (
                        col * cell_w + margin,
                        row * cell_h + margin,
                        (col + 1) * cell_w - margin,
                        (row + 1) * cell_h - margin,
                    )
                    max_w = max(10, region[2] - region[0])
                    max_h = max(10, region[3] - region[1])
                    with Image.open(img_path) as src:
                        prepared = src.convert('RGB')
                        fitted = ImageOps.contain(prepared, (max_w, max_h))
                    offset_x = region[0] + max(0, (max_w - fitted.width) // 2)
                    offset_y = region[1] + max(0, (max_h - fitted.height) // 2)
                    canvas.paste(fitted, (offset_x, offset_y))
                pages.append(canvas)

            filename = opts.get('outputName') or f'{files[0].stem}_merge.pdf'
            if not filename.lower().endswith('.pdf'):
                filename = f'{filename}.pdf'
            dest = output_dir / filename
            first, rest = pages[0], pages[1:]
            first.save(dest, 'PDF', save_all=bool(rest), append_images=rest)
            return api_success('PDF 导出完成', file=str(dest), outputDir=str(output_dir), pages=len(pages))
        except Exception as exc:
            return api_error(f'导出 PDF 失败：{exc}')
