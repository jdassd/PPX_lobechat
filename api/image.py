#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理相关 API
"""
from __future__ import annotations

import base64
import io
import math
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFont, ImageOps, ExifTags

from api.utils import (
    ensure_files_payload,
    ensure_file_path,
    api_success,
    api_error,
    format_bytes,
)


class ImageTool:
    """图片相关功能"""

    _valid_formats = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'gif', 'svg'}
    _page_sizes = {
        'a4': (2480, 3508),   # 300 DPI
        'a5': (1748, 2480),
        'letter': (2550, 3300),
        'a3': (3508, 4961),
        'square': (3000, 3000),
        'slide_16_9': (3508, 1973),
    }
    _image_groups: Dict[str, Dict] = {}
    _image_group_root = Path(tempfile.gettempdir()) / 'ppx_image_groups'

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
        """Persist image with reasonable defaults and Pillow-compatible format names."""
        save_kwargs = {}
        fmt = (fmt or 'png').lower()
        if fmt in {'jpg', 'jpeg'}:
            # JPEG does not support alpha; always save as RGB
            image = image.convert('RGB')
            if quality:
                save_kwargs['quality'] = max(30, min(quality, 100))
            save_kwargs.setdefault('optimize', True)
        if fmt == 'png':
            save_kwargs.setdefault('compress_level', 6)

        # Pillow uses 'JPEG' internally; normalize common alias 'jpg'
        if fmt in {'jpg', 'jpeg'}:
            pil_format = 'JPEG'
        else:
            pil_format = fmt.upper()

        image.save(dest, pil_format, **save_kwargs)

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

    def _align_offset(self, container: int, item: int, align: str) -> int:
        mode = (align or 'center').lower()
        if mode in {'start', 'top', 'left'}:
            return 0
        if mode in {'end', 'bottom', 'right'}:
            return max(0, container - item)
        return max(0, (container - item) // 2)

    def _stringify_exif_value(self, value):
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='ignore').strip('\x00')
            except Exception:
                return value.hex()
        if isinstance(value, (list, tuple)):
            return ', '.join(self._stringify_exif_value(item) for item in value)
        return str(value)

    def _ensure_group_root(self) -> Path:
        self._image_group_root.mkdir(parents=True, exist_ok=True)
        return self._image_group_root

    def _normalize_file_name(self, path: Path) -> str:
        name = path.name or f'image_{int(time.time())}.png'
        return name

    def _unique_path(self, directory: Path, name: str) -> Path:
        stem = Path(name).stem
        suffix = Path(name).suffix
        candidate = directory / name
        index = 1
        while candidate.exists():
            index += 1
            candidate = directory / f'{stem}_{index}{suffix}'
        return candidate

    def _serialize_files(self, files: Sequence[Path]) -> List[Dict]:
        payload: List[Dict] = []
        for item in files:
            try:
                size = item.stat().st_size
            except Exception:
                size = 0
            payload.append({
                'path': str(item),
                'name': item.name,
                'size': size,
                'sizeText': format_bytes(size),
            })
        return payload

    def _require_group(self, group_id: str, allow_empty: bool = False) -> Dict:
        if not group_id:
            raise ValueError('缺少图片组 ID')
        group = self._image_groups.get(group_id)
        if not group:
            raise ValueError(f'图片组不存在：{group_id}')
        current_files = group.get('currentFiles') or []
        if not allow_empty and not current_files:
            raise ValueError('图片组为空，请先导入图片')
        return group

    def _next_group_stage(self, group: Dict, stage: str) -> Tuple[int, Path]:
        next_step = int(group.get('step') or 0) + 1
        stage_dir = group['root'] / f'{next_step:03d}_{stage}'
        stage_dir.mkdir(parents=True, exist_ok=True)
        return next_step, stage_dir

    def _update_group_files(self, group: Dict, files: Sequence[Path]):
        normalized = [Path(item) for item in files if item]
        if not normalized:
            raise ValueError('处理后未生成任何图片')
        group['currentFiles'] = normalized

    def _resolve_group_selected(
        self,
        group: Dict,
        selected_raw,
        allow_all: bool = True,
    ) -> List[Path]:
        current_files: List[Path] = [Path(item) for item in (group.get('currentFiles') or [])]
        if not current_files:
            raise ValueError('图片组为空，请先导入图片')
        if not selected_raw:
            if allow_all:
                return list(current_files)
            raise ValueError('请先选择图片')

        lookup = {str(path.resolve()): path for path in current_files}
        selected: List[Path] = []
        seen = set()
        for item in selected_raw:
            if isinstance(item, dict):
                item = item.get('path')
            if not item:
                continue
            key = str(Path(item).resolve())
            target = lookup.get(key)
            if not target or key in seen:
                continue
            seen.add(key)
            selected.append(target)
        if not selected:
            raise ValueError('未匹配到图片组中的有效图片')
        return selected

    def _merge_group_processed_files(
        self,
        group: Dict,
        selected: Sequence[Path],
        outputs: Sequence[Path],
        keep_original: bool,
    ) -> List[Path]:
        current_files: List[Path] = [Path(item) for item in (group.get('currentFiles') or [])]
        selected_list = [Path(item) for item in selected]
        output_list = [Path(item) for item in outputs if item]
        if not output_list:
            raise ValueError('处理后未生成任何图片')

        if keep_original:
            merged = current_files + output_list
        else:
            if len(output_list) != len(selected_list):
                raise ValueError('处理结果数量与选中图片数量不一致，无法替换')
            mapping = {str(src.resolve()): out for src, out in zip(selected_list, output_list)}
            merged = []
            for source in current_files:
                key = str(source.resolve())
                merged.append(mapping.get(key, source))

        deduped: List[Path] = []
        seen = set()
        for item in merged:
            path = Path(item)
            key = str(path.resolve())
            if key in seen:
                continue
            if path.exists():
                deduped.append(path)
                seen.add(key)
        if not deduped:
            raise ValueError('图片组为空，请重新导入图片')
        group['currentFiles'] = deduped
        return deduped

    # -------------------- 图片组流水线 --------------------

    def image_group_create(self, options: Dict | None = None):
        """创建图片组，将源图片复制到临时工作区"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            group_id = opts.get('groupId') or uuid.uuid4().hex
            if group_id in self._image_groups:
                raise ValueError(f'图片组 ID 已存在：{group_id}')
            root = self._ensure_group_root() / group_id
            source_dir = root / '000_source'
            source_dir.mkdir(parents=True, exist_ok=True)

            copied: List[Path] = []
            for file_path in files:
                dest = self._unique_path(source_dir, self._normalize_file_name(file_path))
                shutil.copy2(file_path, dest)
                copied.append(dest)

            group = {
                'id': group_id,
                'root': root,
                'step': 0,
                'createdAt': datetime.now().isoformat(timespec='seconds'),
                'currentFiles': copied,
            }
            self._image_groups[group_id] = group
            return api_success(
                f'图片组已创建，共 {len(copied)} 张',
                groupId=group_id,
                step=0,
                files=self._serialize_files(copied),
                createdAt=group['createdAt'],
            )
        except Exception as exc:
            return api_error(f'创建图片组失败：{exc}')

    def image_group_get(self, options: Dict | None = None):
        """获取图片组当前文件列表"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''), allow_empty=True)
            files = group.get('currentFiles') or []
            return api_success(
                '获取图片组成功',
                groupId=group['id'],
                step=int(group.get('step') or 0),
                files=self._serialize_files(files),
                createdAt=group.get('createdAt'),
            )
        except Exception as exc:
            return api_error(f'获取图片组失败：{exc}')

    def image_group_dispose(self, options: Dict | None = None):
        """释放图片组临时文件"""
        try:
            opts = self._validate(options)
            group_id = str(opts.get('groupId') or '')
            if not group_id:
                raise ValueError('缺少图片组 ID')
            group = self._image_groups.pop(group_id, None)
            if group and group.get('root'):
                shutil.rmtree(group['root'], ignore_errors=True)
            return api_success('图片组已释放', groupId=group_id)
        except Exception as exc:
            return api_error(f'释放图片组失败：{exc}')

    def image_group_compress(self, options: Dict | None = None):
        """对图片组选中项执行批量压缩并回写缓存"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''))
            selected = self._resolve_group_selected(group, opts.get('selectedFiles'))
            keep_original = bool(opts.get('keepOriginal', False))
            next_step, stage_dir = self._next_group_stage(group, 'compress')
            res = self.image_batch_compress({
                'files': [str(path) for path in selected],
                'mode': opts.get('mode', 'quality'),
                'quality': opts.get('quality', 80),
                'targetSizeKB': opts.get('targetSizeKB'),
                'outputDir': str(stage_dir),
            })
            if res.get('code') != 0:
                return res
            output_lookup = {}
            for item in (res.get('items') or []):
                source = item.get('source')
                output = item.get('output')
                if source and output:
                    output_lookup[str(Path(source).resolve())] = Path(output)
            outputs: List[Path] = []
            for source in selected:
                mapped = output_lookup.get(str(source.resolve()))
                if mapped:
                    outputs.append(mapped)
            merged = self._merge_group_processed_files(group, selected, outputs, keep_original)
            group['step'] = next_step
            return api_success(
                f'图片组压缩完成，处理 {len(outputs)} 张',
                groupId=group['id'],
                step=group['step'],
                files=self._serialize_files(merged),
                processedFiles=self._serialize_files(outputs),
            )
        except Exception as exc:
            return api_error(f'图片组压缩失败：{exc}')

    def image_group_watermark(self, options: Dict | None = None):
        """对图片组选中项执行批量水印并回写缓存"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''))
            selected = self._resolve_group_selected(group, opts.get('selectedFiles'))
            keep_original = bool(opts.get('keepOriginal', False))
            next_step, stage_dir = self._next_group_stage(group, 'watermark')
            res = self.image_add_watermark({
                'files': [str(path) for path in selected],
                'watermarkType': opts.get('watermarkType', 'text'),
                'text': opts.get('text'),
                'fontSize': opts.get('fontSize'),
                'color': opts.get('color'),
                'opacity': opts.get('opacity'),
                'position': opts.get('position'),
                'tile': opts.get('tile'),
                'tileSpacing': opts.get('tileSpacing'),
                'rotation': opts.get('rotation'),
                'watermarkImage': opts.get('watermarkImage'),
                'scalePercent': opts.get('scalePercent'),
                'outputDir': str(stage_dir),
            })
            if res.get('code') != 0:
                return res
            outputs = [Path(item) for item in (res.get('files') or []) if item]
            merged = self._merge_group_processed_files(group, selected, outputs, keep_original)
            group['step'] = next_step
            return api_success(
                f'图片组水印完成，处理 {len(outputs)} 张',
                groupId=group['id'],
                step=group['step'],
                files=self._serialize_files(merged),
                processedFiles=self._serialize_files(outputs),
            )
        except Exception as exc:
            return api_error(f'图片组水印失败：{exc}')

    def image_group_crop(self, options: Dict | None = None):
        """对图片组选中项执行批量裁剪并回写缓存"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''))
            selected = self._resolve_group_selected(group, opts.get('selectedFiles'))
            keep_original = bool(opts.get('keepOriginal', False))
            next_step, stage_dir = self._next_group_stage(group, 'crop')
            outputs: List[Path] = []
            for file_path in selected:
                res = self.image_crop({
                    'file': str(file_path),
                    'mode': opts.get('mode', 'custom'),
                    'x': opts.get('x'),
                    'y': opts.get('y'),
                    'width': opts.get('width'),
                    'height': opts.get('height'),
                    'ratio': opts.get('ratio'),
                    'ratioWidth': opts.get('ratioWidth'),
                    'ratioHeight': opts.get('ratioHeight'),
                    'outputDir': str(stage_dir),
                })
                if res.get('code') != 0:
                    return res
                output = res.get('file')
                if output:
                    outputs.append(Path(output))
            merged = self._merge_group_processed_files(group, selected, outputs, keep_original)
            group['step'] = next_step
            return api_success(
                f'图片组裁剪完成，处理 {len(outputs)} 张',
                groupId=group['id'],
                step=group['step'],
                files=self._serialize_files(merged),
                processedFiles=self._serialize_files(outputs),
            )
        except Exception as exc:
            return api_error(f'图片组裁剪失败：{exc}')

    def image_group_format_convert(self, options: Dict | None = None):
        """对图片组选中项执行格式转换并回写缓存"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''))
            selected = self._resolve_group_selected(group, opts.get('selectedFiles'))
            keep_original = bool(opts.get('keepOriginal', False))
            next_step, stage_dir = self._next_group_stage(group, 'convert')
            res = self.image_format_convert({
                'files': [str(path) for path in selected],
                'targetFormat': opts.get('targetFormat', 'png'),
                'quality': opts.get('quality'),
                'keepName': opts.get('keepName', True),
                'outputDir': str(stage_dir),
            })
            if res.get('code') != 0:
                return res
            outputs = [Path(item) for item in (res.get('files') or []) if item]
            merged = self._merge_group_processed_files(group, selected, outputs, keep_original)
            group['step'] = next_step
            return api_success(
                f'图片组格式转换完成，处理 {len(outputs)} 张',
                groupId=group['id'],
                step=group['step'],
                files=self._serialize_files(merged),
                processedFiles=self._serialize_files(outputs),
            )
        except Exception as exc:
            return api_error(f'图片组格式转换失败：{exc}')

    def image_group_rotate(self, options: Dict | None = None):
        """对图片组选中项执行旋转/翻转并回写缓存"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''))
            selected = self._resolve_group_selected(group, opts.get('selectedFiles'))
            keep_original = bool(opts.get('keepOriginal', False))
            next_step, stage_dir = self._next_group_stage(group, 'rotate')
            res = self.image_rotate_flip({
                'files': [str(path) for path in selected],
                'operation': opts.get('operation', 'rotate90'),
                'angle': opts.get('angle'),
                'flipHorizontal': opts.get('flipHorizontal'),
                'flipVertical': opts.get('flipVertical'),
                'outputDir': str(stage_dir),
            })
            if res.get('code') != 0:
                return res
            outputs = [Path(item) for item in (res.get('files') or []) if item]
            merged = self._merge_group_processed_files(group, selected, outputs, keep_original)
            group['step'] = next_step
            return api_success(
                f'图片组旋转/翻转完成，处理 {len(outputs)} 张',
                groupId=group['id'],
                step=group['step'],
                files=self._serialize_files(merged),
                processedFiles=self._serialize_files(outputs),
            )
        except Exception as exc:
            return api_error(f'图片组旋转/翻转失败：{exc}')

    def image_group_remove_files(self, options: Dict | None = None):
        """从图片组中移除选中图片（仅移出缓存）"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''), allow_empty=True)
            current_files: List[Path] = [Path(item) for item in (group.get('currentFiles') or [])]
            if not current_files:
                return api_success('图片组为空', groupId=group['id'], files=[])
            selected = self._resolve_group_selected(group, opts.get('selectedFiles'), allow_all=False)
            remove_keys = {str(path.resolve()) for path in selected}
            remaining = [path for path in current_files if str(path.resolve()) not in remove_keys]
            group['currentFiles'] = remaining
            return api_success(
                f'已移除 {len(selected)} 张图片',
                groupId=group['id'],
                files=self._serialize_files(remaining),
                removedFiles=self._serialize_files(selected),
            )
        except Exception as exc:
            return api_error(f'移除图片失败：{exc}')

    def image_group_export(self, options: Dict | None = None):
        """导出图片组当前文件，可按选中项或整组批量导出"""
        try:
            opts = self._validate(options)
            group = self._require_group(str(opts.get('groupId') or ''))
            current_files: List[Path] = group.get('currentFiles') or []
            output_dir_raw = opts.get('outputDir')
            if not output_dir_raw:
                raise ValueError('请选择导出目录')
            output_dir = Path(output_dir_raw)
            output_dir.mkdir(parents=True, exist_ok=True)

            selected_raw = opts.get('selectedFiles') or []
            selected: List[Path] = []
            if selected_raw:
                lookup = {str(path.resolve()): path for path in current_files}
                for item in selected_raw:
                    if not item:
                        continue
                    key = str(Path(item).resolve())
                    target = lookup.get(key)
                    if target:
                        selected.append(target)
                if not selected:
                    raise ValueError('未匹配到可导出的图片，请重新选择')
            else:
                selected = list(current_files)

            exported: List[Path] = []
            for source in selected:
                dest = self._unique_path(output_dir, self._normalize_file_name(source))
                shutil.copy2(source, dest)
                exported.append(dest)

            return api_success(
                f'已导出 {len(exported)} 张图片',
                groupId=group['id'],
                outputDir=str(output_dir),
                files=self._serialize_files(exported),
                count=len(exported),
            )
        except Exception as exc:
            return api_error(f'导出图片组失败：{exc}')

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
                    if fmt == 'svg':
                        # 使用简单矢量包装：将位图嵌入 SVG 作为 base64 PNG，避免额外依赖
                        rgb = image.convert('RGB')
                        buffer = io.BytesIO()
                        rgb.save(buffer, format='PNG')
                        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
                        svg = (
                            f'<svg xmlns="http://www.w3.org/2000/svg" '
                            f'width="{rgb.width}" height="{rgb.height}">'
                            f'<image href="data:image/png;base64,{encoded}" '
                            f'width="{rgb.width}" height="{rgb.height}"/></svg>'
                        )
                        dest.write_text(svg, encoding='utf-8')
                    else:
                        self._save_image(image, dest, fmt, quality)
                    rewritten.append(str(dest))
            return api_success(f'已转换 {len(rewritten)} 个文件', files=rewritten, outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'转换失败：{exc}')

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

    def image_preview(self, options: Dict | None = None):
        """图片预览 - 返回 data URL，支持避免跨域的 file:/// 资源"""
        try:
            opts = self._validate(options)
            # 支持 file / path 两种参数字段
            file_path = ensure_file_path(opts.get('file') or opts.get('path'))
            try:
                max_size = int(opts.get('maxSize') or 1920)
            except (TypeError, ValueError):
                max_size = 1920
            max_size = max(256, min(max_size, 8192))

            with Image.open(file_path) as img:
                img = img.convert('RGBA')
                orig_w, orig_h = img.size
                # 当图片尺寸超过阈值时，缩小以减轻前端的渲染负担
                if max(orig_w, orig_h) > max_size:
                    img.thumbnail((max_size, max_size), Image.LANCZOS)

                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                encoded = base64.b64encode(buffer.getvalue()).decode('ascii')

            preview = f'data:image/png;base64,{encoded}'
            return api_success('图片预览成功', preview=preview, width=orig_w, height=orig_h)
        except Exception as exc:
            return api_error(f'图片预览失败：{exc}')

    def image_add_watermark(self, options: Dict | None = None):
        """批量添加文字或图片水印，支持平铺与旋转"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_watermark')
            watermark_type = str(opts.get('watermarkType', 'text')).lower()
            position = str(opts.get('position', 'bottom-right')).lower()
            opacity = max(5, min(int(opts.get('opacity') or 60), 100))
            font_size = max(8, int(opts.get('fontSize') or 32))
            color = self._parse_color(opts.get('color'))

            # 平铺与旋转参数
            tile = bool(opts.get('tile', False))
            try:
                tile_spacing = int(opts.get('tileSpacing') or 80)
            except (TypeError, ValueError):
                tile_spacing = 80
            tile_spacing = max(0, min(tile_spacing, 2000))
            try:
                rotation = float(opts.get('rotation') or 0.0)
            except (TypeError, ValueError):
                rotation = 0.0
            rotation = max(-180.0, min(rotation, 180.0))

            results: List[str] = []

            wm_image_path = opts.get('watermarkImage')
            if isinstance(wm_image_path, dict):
                wm_image_path = wm_image_path.get('path')
            watermark_image = ensure_file_path(wm_image_path) if wm_image_path else None

            for file_path in files:
                with Image.open(file_path).convert('RGBA') as base:
                    overlay = Image.new('RGBA', base.size, (255, 255, 255, 0))

                    # 准备单个水印图层
                    if watermark_type == 'image':
                        if not watermark_image:
                            raise ValueError('请提供水印图片')
                        with Image.open(watermark_image).convert('RGBA') as wm:
                            scale_percent = float(opts.get('scalePercent') or opts.get('scale') or 30)
                            scale_percent = max(5.0, min(scale_percent, 100.0)) / 100.0
                            target_width = max(10, int(base.width * scale_percent))
                            target_height = max(10, int(target_width * wm.height / wm.width))
                            stamp = wm.resize((target_width, target_height), Image.LANCZOS)
                            alpha_layer = stamp.getchannel('A') if 'A' in stamp.getbands() else Image.new('L', stamp.size, 255)
                            enhancer = ImageEnhance.Brightness(alpha_layer)
                            stamp.putalpha(enhancer.enhance(opacity / 100.0))
                    else:
                        text_value = str(opts.get('text') or '').strip()
                        if not text_value:
                            raise ValueError('请输入文字水印内容')
                        font = self._resolve_font(font_size, opts.get('fontPath'))
                        # 先测量文本尺寸
                        temp_img = Image.new('RGBA', (10, 10), (255, 255, 255, 0))
                        temp_draw = ImageDraw.Draw(temp_img)
                        bbox = temp_draw.multiline_textbbox((0, 0), text_value, font=font)
                        mark_w = max(1, bbox[2] - bbox[0])
                        mark_h = max(1, bbox[3] - bbox[1])
                        # 在独立图层绘制文字
                        stamp = Image.new('RGBA', (mark_w, mark_h), (255, 255, 255, 0))
                        draw = ImageDraw.Draw(stamp)
                        draw.multiline_text(
                            (0, 0),
                            text_value,
                            font=font,
                            fill=(*color, int(255 * (opacity / 100.0))),
                            align='left',
                        )

                    # 旋转水印（如设置了角度）
                    if rotation and abs(rotation) > 0.1:
                        stamp = stamp.rotate(
                            rotation,
                            expand=True,
                            resample=Image.BICUBIC,
                            fillcolor=(0, 0, 0, 0),
                        )

                    stamp_w, stamp_h = stamp.size
                    if stamp_w <= 0 or stamp_h <= 0:
                        continue

                    if tile:
                        # 平铺模式：按间距覆盖整张图片
                        step_x = max(1, stamp_w + tile_spacing)
                        step_y = max(1, stamp_h + tile_spacing)
                        offset_x = max(0, tile_spacing // 2)
                        offset_y = max(0, tile_spacing // 2)
                        y = offset_y
                        while y < base.height:
                            x = offset_x
                            while x < base.width:
                                overlay.paste(stamp, (int(x), int(y)), stamp)
                                x += step_x
                            y += step_y
                    else:
                        # 单个水印：沿用九宫格定位
                        pos = self._resolve_position(base.size, stamp.size, position)
                        overlay.paste(stamp, pos, stamp)

                    composed = Image.alpha_composite(base, overlay)
                    fmt = file_path.suffix.lstrip('.').lower() or 'png'
                    dest = output_dir / f'{file_path.stem}_wm.{fmt}'
                    self._save_image(composed, dest, fmt)
                    results.append(str(dest))

            return api_success(f'已完成{len(results)} 个文件水印', files=results, outputDir=str(output_dir))
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
            angle = float(opts.get('angle') or 0.0)
            flip_horizontal = bool(opts.get('flipHorizontal'))
            flip_vertical = bool(opts.get('flipVertical'))
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
                    elif operation == 'custom':
                        processed = image
                        if angle:
                            processed = processed.rotate(angle, expand=True)
                        if flip_horizontal:
                            processed = ImageOps.mirror(processed)
                        if flip_vertical:
                            processed = ImageOps.flip(processed)
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

    # -------------------- P2 功能 --------------------

    def image_concat(self, options: Dict | None = None):
        """图片拼接"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            layout = str(opts.get('direction', 'horizontal')).lower()
            if layout not in {'horizontal', 'vertical', 'grid'}:
                layout = 'horizontal'
            spacing = max(0, int(opts.get('spacing') or 0))
            align = str(opts.get('align', 'center')).lower()
            fmt = str(opts.get('outputFormat') or 'png').lower().lstrip('.')
            if fmt not in self._valid_formats:
                fmt = 'png'
            quality = None
            if opts.get('quality') is not None:
                try:
                    quality = int(opts.get('quality'))
                except (TypeError, ValueError):
                    quality = None
            bg_color = (*self._parse_color(opts.get('background') or '#ffffff'), 255)
            output_dir = self._prepare_output_dir(files, opts.get('outputDir'), 'image_concat')
            images: List[Image.Image] = []
            widths: List[int] = []
            heights: List[int] = []
            try:
                for path in files:
                    img = Image.open(path).convert('RGBA')
                    images.append(img)
                    widths.append(img.width)
                    heights.append(img.height)
                if layout == 'vertical':
                    canvas_width = max(widths)
                    canvas_height = sum(heights) + spacing * max(0, len(images) - 1)
                    canvas = Image.new('RGBA', (canvas_width, canvas_height), bg_color)
                    offset_y = 0
                    for img in images:
                        offset_x = self._align_offset(canvas_width, img.width, align)
                        canvas.paste(img, (offset_x, offset_y), img)
                        offset_y += img.height + spacing
                elif layout == 'grid':
                    columns = max(1, int(opts.get('columns') or 2))
                    max_width = max(widths)
                    max_height = max(heights)
                    rows = math.ceil(len(images) / columns)
                    canvas_width = columns * max_width + spacing * max(0, columns - 1)
                    canvas_height = rows * max_height + spacing * max(0, rows - 1)
                    canvas = Image.new('RGBA', (canvas_width, canvas_height), bg_color)
                    for idx, img in enumerate(images):
                        row = idx // columns
                        col = idx % columns
                        cell_x = col * (max_width + spacing)
                        cell_y = row * (max_height + spacing)
                        offset_x = cell_x + self._align_offset(max_width, img.width, 'center')
                        offset_y = cell_y + self._align_offset(max_height, img.height, 'center')
                        canvas.paste(img, (offset_x, offset_y), img)
                else:
                    canvas_width = sum(widths) + spacing * max(0, len(images) - 1)
                    canvas_height = max(heights)
                    canvas = Image.new('RGBA', (canvas_width, canvas_height), bg_color)
                    offset_x = 0
                    for img in images:
                        offset_y = self._align_offset(canvas_height, img.height, align)
                        canvas.paste(img, (offset_x, offset_y), img)
                        offset_x += img.width + spacing
            finally:
                for img in images:
                    img.close()
            dest_name = opts.get('outputName') or f'{files[0].stem}_concat.{fmt}'
            if not dest_name.lower().endswith(f'.{fmt}'):
                dest_name = f'{dest_name}.{fmt}'
            dest = output_dir / dest_name
            self._save_image(canvas, dest, fmt, quality)
            return api_success('图片拼接完成', file=str(dest), outputDir=str(output_dir))
        except Exception as exc:
            return api_error(f'拼接失败：{exc}')

    def image_batch_rename(self, options: Dict | None = None):
        """图片批量重命名/复制"""
        try:
            opts = self._validate(options)
            files = ensure_files_payload(opts)
            mode = str(opts.get('mode', 'sequence')).lower()
            digits = max(1, int(opts.get('digits') or len(str(len(files) + 1))))
            start_index = int(opts.get('startIndex') or 1)
            prefix = opts.get('prefix') or 'img_'
            suffix = opts.get('suffix') or ''
            timestamp_fmt = opts.get('timestampFormat') or '%Y%m%d_%H%M%S'
            pattern = opts.get('pattern') or '{name}_{index}'
            keep_extension = bool(opts.get('keepExtension', True))
            override_ext = opts.get('extension')
            if override_ext:
                override_ext = override_ext if override_ext.startswith('.') else f'.{override_ext}'
            dry_run = bool(opts.get('dryRun', True))
            copy_mode = bool(opts.get('copyMode', False))
            conflict_policy = str(opts.get('conflictPolicy', 'skip')).lower()
            output_dir = opts.get('outputDir')
            target_dir = None
            if output_dir:
                target_dir = Path(output_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
            if copy_mode and target_dir is None:
                target_dir = self._prepare_output_dir(files, None, 'image_rename')
            operations: List[Dict[str, str]] = []
            skipped: List[str] = []
            timestamp_cache = datetime.now().strftime(timestamp_fmt)

            def build_name(path: Path, number: int) -> str:
                digits_str = str(number).zfill(digits)
                if mode == 'timestamp':
                    base = f'{prefix}{timestamp_cache}_{digits_str}{suffix}'
                elif mode == 'custom':
                    context = {
                        'index': digits_str,
                        'number': digits_str,
                        'name': path.stem,
                        'original': path.stem,
                        'timestamp': int(time.time()),
                        'datetime': timestamp_cache,
                    }
                    try:
                        base = pattern.format(**context)
                    except Exception:
                        base = f'{prefix}{digits_str}{suffix}'
                else:
                    base = f'{prefix}{digits_str}{suffix}'
                if keep_extension or not override_ext:
                    ext = path.suffix or '.png'
                else:
                    ext = override_ext
                return base + ext

            for offset, path in enumerate(files):
                index = start_index + offset
                new_name = build_name(path, index)
                if target_dir:
                    dest = target_dir / new_name
                else:
                    dest = path.with_name(new_name)
                if dest.exists() and dest != path:
                    if conflict_policy == 'overwrite' and not dry_run:
                        dest.unlink()
                    else:
                        skipped.append(str(path))
                        continue
                operations.append({'from': str(path), 'to': str(dest)})
                if dry_run:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                if copy_mode:
                    shutil.copy2(path, dest)
                else:
                    path.rename(dest)
            message = '重命名预览' if dry_run else '批量重命名完成'
            payload = {
                'operations': operations,
                'skipped': skipped,
                'dryRun': dry_run,
            }
            if target_dir:
                payload['outputDir'] = str(target_dir)
            return api_success(message, **payload)
        except Exception as exc:
            return api_error(f'批量重命名失败：{exc}')

    def image_get_exif(self, options: Dict | None = None):
        """获取 EXIF 信息"""
        try:
            opts = self._validate(options)
            file_path = self._ensure_single_file(opts)
            with Image.open(file_path) as image:
                exif = image.getexif()
                if not exif:
                    return api_success('未检测到 EXIF 信息', exif=[], gps={}, file=str(file_path))
                readable = []
                gps_info = {}
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, f'Tag {tag_id}')
                    if tag_name == 'GPSInfo' and isinstance(value, dict):
                        gps_info = {
                            ExifTags.GPSTAGS.get(key, str(key)): self._stringify_exif_value(val)
                            for key, val in value.items()
                        }
                        continue
                    readable.append({
                        'tag': tag_name,
                        'value': self._stringify_exif_value(value),
                    })
            return api_success('EXIF 读取完成', file=str(file_path), exif=readable, gps=gps_info)
        except Exception as exc:
            return api_error(f'读取 EXIF 失败：{exc}')


