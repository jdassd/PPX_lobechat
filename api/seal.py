#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2025-07-04
Description: 印章生成相关 API
'''

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from math import cos, pi, sin, tan
from pathlib import Path
from random import randint
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from pyapp.config.config import Config

_CHINESE_BRACKETS = '（）【】《》「」『』'
_CHINESE_PUNCT = '，。！？；：·…—～、'

_FONT_CANDIDATES_ZH = [
    'C:/Windows/Fonts/simsun.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
    '/System/Library/Fonts/PingFang.ttc',
    '/System/Library/Fonts/STHeiti Medium.ttc',
    '/System/Library/Fonts/Songti.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/arphic/ukai.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
]

_FONT_CANDIDATES_LATIN = [
    'C:/Windows/Fonts/arial.ttf',
    'C:/Windows/Fonts/segoeui.ttf',
    '/System/Library/Fonts/SFNS.ttf',
    '/System/Library/Fonts/Helvetica.ttc',
    '/Library/Fonts/Arial.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
]


def _is_cjk(ch: str) -> bool:
    if not ch:
        return False
    if ch in _CHINESE_BRACKETS or ch in _CHINESE_PUNCT:
        return True
    code = ord(ch)
    return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF


def _pentagram(x: float, y: float, R: float, y_degree: float = 0):
    rad = pi / 180
    r = R * sin(18 * rad) / cos(36 * rad)
    outer = [(x - (R * cos((90 + k * 72 + y_degree) * rad)), y - (R * sin((90 + k * 72 + y_degree) * rad))) for k in range(5)]
    inner = [(x - (r * cos((90 + 36 + k * 72 + y_degree) * rad)), y - (r * sin((90 + 36 + k * 72 + y_degree) * rad))) for k in range(5)]
    return [point for pair in zip(outer, inner) for point in pair]


def _circle(x: float, y: float, r: float):
    return (x - r, y - r, x + r, y + r)


class Seal():
    '''公章相关 API'''

    def _validate_payload(self, options: Optional[Dict]) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _timestamp(self) -> str:
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    def _auto_font_path(self, candidates, user_path: str = '') -> str:
        if user_path:
            path = Path(user_path).expanduser()
            if path.exists():
                return str(path)
            raise FileNotFoundError(f'字体文件不存在：{user_path}')
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        return ''

    def _ensure_font(self, kind: str, user_path: str = '') -> str:
        if kind == 'chinese':
            path = self._auto_font_path(_FONT_CANDIDATES_ZH, user_path)
            if not path:
                raise FileNotFoundError('未找到可用的中文字体，请在设置中指定 fontChinesePath')
            return path
        else:
            path = self._auto_font_path(_FONT_CANDIDATES_LATIN, user_path)
            if not path:
                raise FileNotFoundError('未找到可用的英文字体，请在设置中指定 fontLatinPath')
            return path

    def _int_option(self, opts: Dict, key: str, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
        try:
            value = int(float(opts.get(key, default)))
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def _float_option(self, opts: Dict, key: str, default: float, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
        try:
            value = float(opts.get(key, default))
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def _parse_seal_color(self, color_value, alpha: int) -> Tuple[int, int, int, int]:
        alpha = self._int_option({'alpha': alpha}, 'alpha', alpha, 0, 255)
        if isinstance(color_value, str):
            value = color_value.strip()
            if value.startswith('#'):
                value = value[1:]
            if len(value) == 3:
                value = ''.join(ch * 2 for ch in value)
            if len(value) != 6:
                raise ValueError('颜色格式需为 #RRGGBB')
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
        elif isinstance(color_value, (list, tuple)) and len(color_value) >= 3:
            r, g, b = color_value[:3]
        else:
            raise ValueError('颜色参数无效')
        return (
            self._int_option({'v': r}, 'v', r, 0, 255),
            self._int_option({'v': g}, 'v', g, 0, 255),
            self._int_option({'v': b}, 'v', b, 0, 255),
            alpha
        )

    def _resolve_output_path(self, config: Dict) -> Path:
        if config.get('outputPath'):
            dest = Path(config['outputPath']).expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)
            return dest
        output_dir = config.get('outputDir') or Path(Config.staticDir) / 'seals'
        dest_dir = Path(output_dir).expanduser()
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = config.get('outputName') or f'seal_{self._timestamp()}.png'
        if not filename.lower().endswith('.png'):
            filename = f'{filename}.png'
        return dest_dir / filename

    def _build_renderer_config(self, opts: Dict) -> Dict:
        config: Dict = {}
        mode = str(opts.get('mode', 'preview')).lower()
        if mode not in ('preview', 'export'):
            mode = 'preview'
        config['mode'] = mode
        config['template'] = str(opts.get('template', 'round'))
        if config['template'] != 'round':
            raise ValueError('当前仅支持圆形印章模板')

        config['words_up'] = str(opts.get('topText', '某某科技有限公司')).strip()
        config['words_mid'] = str(opts.get('middleText', '专用章')).strip()
        config['words_down'] = str(opts.get('bottomText', '统一社会信用代码')).strip()

        config['outer_radius'] = self._int_option(opts, 'outerRadius', 240, 120, 400)
        config['edge'] = self._int_option(opts, 'edge', 8, 2, 40)
        config['border'] = self._int_option(opts, 'border', 14, 6, 40)
        config['star_radius'] = self._int_option(opts, 'starRadius', 86, 30, 200)
        config['middle_radius'] = self._int_option(opts, 'middleRadius', 150, 60, 260)
        config['star_enabled'] = bool(opts.get('starEnabled', True))

        config['font_size_up'] = self._int_option(opts, 'fontSizeTop', 86, 24, 160)
        config['font_size_mid'] = self._int_option(opts, 'fontSizeMiddle', 60, 20, 120)
        config['font_size_down'] = self._int_option(opts, 'fontSizeBottom', 32, 12, 80)

        config['font_ratio_up'] = self._float_option(opts, 'fontRatioTop', 0.66, 0.3, 1.2)
        config['font_ratio_mid'] = self._float_option(opts, 'fontRatioMiddle', 0.72, 0.3, 1.2)
        config['font_ratio_down'] = self._float_option(opts, 'fontRatioBottom', 1.0, 0.3, 1.5)

        config['stroke_up'] = self._int_option(opts, 'strokeTop', 2, 0, 4)
        config['stroke_mid'] = self._int_option(opts, 'strokeMiddle', 1, 0, 4)
        config['stroke_down'] = self._int_option(opts, 'strokeBottom', 1, 0, 4)

        config['angle_up'] = self._float_option(opts, 'topAngle', 270)
        config['angle_mid'] = self._float_option(opts, 'middleAngle', 72)
        config['angle_down'] = self._float_option(opts, 'bottomAngle', 60)
        config['bracket_offset_up'] = self._float_option(opts, 'bracketOffsetTop', 0)
        config['bracket_offset_down'] = self._float_option(opts, 'bracketOffsetBottom', 0)

        alpha = self._int_option(opts, 'alpha', 220, 30, 255)
        config['fill'] = self._parse_seal_color(opts.get('color', '#d4252c'), alpha)

        texture_path = str(opts.get('texturePath') or '').strip()
        if texture_path:
            path = Path(texture_path).expanduser()
            if not path.exists():
                raise FileNotFoundError(f'纹理图不存在：{texture_path}')
            config['texture_path'] = str(path)
        else:
            config['texture_path'] = ''

        config['outputDir'] = opts.get('outputDir', '')
        config['outputName'] = opts.get('outputName', '')
        config['outputPath'] = opts.get('outputPath', '')

        config['font_chinese'] = self._ensure_font('chinese', opts.get('fontChinesePath', '') or opts.get('font_chinese_path', ''))
        config['font_latin'] = self._ensure_font('latin', opts.get('fontLatinPath', '') or opts.get('font_latin_path', ''))

        return config

    def _encode_preview(self, image: Image.Image) -> str:
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f'data:image/png;base64,{encoded}'

    def seal_generate(self, options: Dict = None):
        '''生成电子公章'''
        try:
            opts = self._validate_payload(options)
            config = self._build_renderer_config(opts)
            renderer = _RoundSealRenderer(config)
            image = renderer.render()
            preview = self._encode_preview(image)

            output_path = ''
            if config['mode'] == 'export':
                dest = self._resolve_output_path(config)
                image.save(dest, format='PNG')
                output_path = str(dest)

            msg = '预览已生成' if config['mode'] == 'preview' else f'印章已导出：{output_path}'
            return {
                'code': 0,
                'msg': msg,
                'preview': preview,
                'output': output_path
            }
        except Exception as exc:
            return {'code': -1, 'msg': f'生成失败：{exc}'}


class _RoundSealRenderer:
    '''圆形印章渲染'''

    def __init__(self, config: Dict):
        self.cfg = config
        self.edge = config['edge']
        self.outer_radius = config['outer_radius']
        self.border = config['border']
        self.star_radius = config['star_radius']
        self.middle_radius = config['middle_radius']
        self.words_up = config['words_up']
        self.words_mid = config['words_mid']
        self.words_down = config['words_down']
        self.fill = config['fill']
        self.star_enabled = config['star_enabled']
        self.angle_up = config['angle_up']
        self.angle_mid = config['angle_mid']
        self.angle_down = config['angle_down']
        self.bracket_offset_up = config['bracket_offset_up']
        self.bracket_offset_down = config['bracket_offset_down']
        self.font_ratio_up = config['font_ratio_up']
        self.font_ratio_mid = config['font_ratio_mid']
        self.font_ratio_down = config['font_ratio_down']
        self.font_size_up = config['font_size_up']
        self.font_size_mid = config['font_size_mid']
        self.font_size_down = config['font_size_down']
        self.stroke_up = config['stroke_up']
        self.stroke_mid = config['stroke_mid']
        self.stroke_down = config['stroke_down']
        self.font_chinese = config['font_chinese']
        self.font_latin = config['font_latin']
        self.texture_path = config.get('texture_path', '')
        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

    def _canvas_size(self) -> int:
        return int(2 * (self.outer_radius + self.edge))

    def _get_font(self, size: int, has_chinese: bool) -> ImageFont.FreeTypeFont:
        path = self.font_chinese if has_chinese else self.font_latin
        key = (path, size)
        if key not in self._font_cache:
            self._font_cache[key] = ImageFont.truetype(path, size, encoding='utf-8')
        return self._font_cache[key]

    def _load_texture(self) -> Optional[Image.Image]:
        if not self.texture_path:
            return None
        path = Path(self.texture_path)
        if not path.exists():
            return None
        with Image.open(path) as texture:
            return texture.convert('RGBA')

    def _draw_rotated_text(self, image: Image.Image, angle: float, xy: Tuple[float, float], radius: float,
                           word: str, font_size: int, font_ratio: float, stroke_width: int,
                           font_flip: bool = False, bracket_angle_offset: float = 0):
        if isinstance(word, bytes):
            word = word.decode('utf-8')
        word = str(word)
        draw_angle = angle
        if word in _CHINESE_BRACKETS:
            draw_angle += bracket_angle_offset
        has_chinese = _is_cjk(word)
        font = self._get_font(font_size, has_chinese)
        width, height = image.size
        max_dim = max(width, height)
        mask_size = (max_dim * 2, max_dim * 2)
        mask_resize = (int(max_dim * 2 * font_ratio), max_dim * 2)
        mask = Image.new('L', mask_size, 0)
        draw = ImageDraw.Draw(mask)
        bbox = draw.textbbox((max_dim, max_dim), word, font=font, align='center')
        font_w = bbox[2] - bbox[0]
        font_h = bbox[3] - bbox[1]
        if font_flip:
            word_pos = (int(max_dim - font_w / 2), max_dim + radius - font_h)
        else:
            word_pos = (int(max_dim - font_w / 2), max_dim - radius)
        draw.text(word_pos, word, 255, font=font, align='center', stroke_width=stroke_width)
        if draw_angle % 90 == 0:
            rotated_mask = mask.resize(mask_resize).rotate(draw_angle)
        else:
            bigger_mask = mask.resize((int(max_dim * 8 * font_ratio), max_dim * 8), resample=Image.BICUBIC)
            rotated_mask = bigger_mask.rotate(draw_angle, resample=Image.BICUBIC).resize(mask_resize, resample=Image.LANCZOS)
        mask_xy = (max_dim * font_ratio - xy[0], max_dim - xy[1])
        b_box = mask_xy + (mask_xy[0] + width, mask_xy[1] + height)
        mask = rotated_mask.crop(b_box)
        color_image = Image.new('RGBA', image.size, self.fill)
        image.paste(color_image, mask)

    def _apply_texture(self, image: Image.Image) -> Image.Image:
        texture = self._load_texture()
        if not texture:
            return image.filter(ImageFilter.GaussianBlur(0.3))
        src_w, src_h = texture.size
        dst_w, dst_h = image.size
        if src_w > dst_w and src_h > dst_h:
            max_x = src_w - dst_w
            max_y = src_h - dst_h
            left = randint(0, max_x)
            top = randint(0, max_y)
            texture = texture.crop((left, top, left + dst_w, top + dst_h))
        texture = texture.resize((dst_w, dst_h)).convert('L').filter(ImageFilter.GaussianBlur(1))
        for y in range(dst_h):
            for x in range(dst_w):
                pixel = image.getpixel((x, y))
                alpha = int(texture.getpixel((x, y)) / 255 * pixel[3])
                image.putpixel((x, y), pixel[:3] + (alpha,))
        return image.filter(ImageFilter.GaussianBlur(0.6))

    def render(self) -> Image.Image:
        canvas_size = self._canvas_size()
        scale = 4
        scaled_size = canvas_size * scale
        img = Image.new('RGBA', (scaled_size, scaled_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        center = (self.outer_radius + self.edge) * scale
        draw.arc(_circle(center, center, self.outer_radius * scale), start=0, end=360, fill=self.fill, width=self.border * scale)
        if self.star_enabled:
            star_points = _pentagram(center, center, self.star_radius * scale)
            draw.polygon(star_points, fill=self.fill, outline=self.fill)
        img = img.resize((canvas_size, canvas_size), Image.LANCZOS)
        draw = ImageDraw.Draw(img)
        if self.words_up:
            angle_step = self.angle_up / len(self.words_up)
            angle = ((len(self.words_up) - 1) / 2) * angle_step
            for ch in self.words_up:
                self._draw_rotated_text(
                    img, angle, (self.outer_radius + self.edge, self.outer_radius + self.edge),
                    self.outer_radius - self.border * 2, ch, self.font_size_up, self.font_ratio_up,
                    self.stroke_up, bracket_angle_offset=self.bracket_offset_up
                )
                angle -= angle_step
        if self.words_mid:
            angle_step = self.angle_mid / len(self.words_mid)
            angle = -((len(self.words_mid) - 1) / 2) * angle_step
            for ch in self.words_mid:
                offset_x = self.middle_radius * tan(angle * pi / 180)
                self._draw_rotated_text(
                    img, 0,
                    (self.outer_radius + self.edge + offset_x, self.outer_radius + self.edge),
                    self.middle_radius, ch, self.font_size_mid, self.font_ratio_mid,
                    self.stroke_mid, font_flip=True
                )
                angle += angle_step
        if self.words_down:
            angle_step = self.angle_down / len(self.words_down)
            angle = -((len(self.words_down) - 1) / 2) * angle_step
            for ch in self.words_down:
                self._draw_rotated_text(
                    img, angle, (self.outer_radius + self.edge, self.outer_radius + self.edge),
                    self.outer_radius - self.border * 2, ch, self.font_size_down, self.font_ratio_down,
                    self.stroke_down, font_flip=True, bracket_angle_offset=self.bracket_offset_down
                )
                angle += angle_step
        return self._apply_texture(img)
