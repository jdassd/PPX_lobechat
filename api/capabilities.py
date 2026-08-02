#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runtime capability discovery exposed to the desktop frontend."""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

from api.utils.error_handler import api_success, safe_execute
from pyapp.config.config import Config


class CapabilitiesMixin:
    """Report optional dependencies without importing heavyweight runtimes."""

    @staticmethod
    def _module_available(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (ImportError, AttributeError, ValueError):
            return False

    @staticmethod
    def _find_libreoffice() -> str:
        candidates = []
        if sys.platform == 'darwin':
            candidates.append('/Applications/LibreOffice.app/Contents/MacOS/soffice')
        elif sys.platform.startswith('win'):
            candidates.extend([
                r'C:\Program Files\LibreOffice\program\soffice.exe',
                r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
            ])
        candidates.extend(filter(None, (shutil.which('soffice'), shutil.which('libreoffice'))))
        return next((path for path in candidates if Path(path).exists()), '')

    @safe_execute
    def capabilities_get(self):
        rapidocr_ready = self._module_available('rapidocr')
        onnx_ready = self._module_available('onnxruntime')
        ffmpeg_path = shutil.which('ffmpeg') or ''
        ffprobe_path = shutil.which('ffprobe') or ''
        libreoffice_path = self._find_libreoffice()
        playwright_ready = self._module_available('playwright')
        chromium_ready = False
        if playwright_ready and hasattr(self, '_wa_chromium_installed'):
            try:
                chromium_ready = bool(self._wa_chromium_installed())
            except Exception:
                chromium_ready = False

        capabilities = {
            'ocr': {
                'id': 'ocr',
                'name': '离线 OCR',
                'available': rapidocr_ready and onnx_ready,
                'detail': 'RapidOCR 与 ONNX Runtime 已就绪' if rapidocr_ready and onnx_ready else '缺少 RapidOCR 或 ONNX Runtime',
            },
            'ffmpeg': {
                'id': 'ffmpeg',
                'name': '视频工具链',
                'available': bool(ffmpeg_path and ffprobe_path),
                'detail': 'FFmpeg 与 ffprobe 已就绪' if ffmpeg_path and ffprobe_path else '需要安装 FFmpeg 并加入 PATH',
            },
            'libreoffice': {
                'id': 'libreoffice',
                'name': 'Word 真实分页',
                'available': bool(libreoffice_path),
                'detail': libreoffice_path or '按页处理 Word 需要安装 LibreOffice',
            },
            'playwright': {
                'id': 'playwright',
                'name': '网页自动化',
                'available': playwright_ready and chromium_ready,
                'detail': 'Playwright 与 Chromium 已就绪' if playwright_ready and chromium_ready else '需要安装 Playwright Chromium 内核',
            },
            'system': {
                'id': 'system',
                'name': '系统高级功能',
                'available': Config.appSystem == 'Windows',
                'detail': '支持只读启动项与进程查看' if Config.appSystem == 'Windows' else '高级系统功能仅支持 Windows',
            },
        }
        return api_success(platform=Config.appSystem, capabilities=capabilities)
