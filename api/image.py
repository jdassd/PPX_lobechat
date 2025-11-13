#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理相关 API
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List

from PIL import Image

from api.utils import (
    ensure_files_payload,
    api_success,
    api_error,
    format_bytes,
    parse_percentage,
)


class ImageTool:
    """图片相关功能"""

    _valid_formats = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

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
                            # thumbnail 会保持比例，最大不超过指定尺寸
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
                    current_quality = quality
                    if mode == 'size' and target_kb:
                        # 逐步降低质量
                        for level in range(quality, 30, -5):
                            buffer.seek(0)
                            buffer.truncate(0)
                            image.convert('RGB').save(buffer, 'JPEG', optimize=True, quality=level)
                            size_kb = buffer.tell() / 1024
                            current_quality = level
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
