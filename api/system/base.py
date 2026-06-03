#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 公共基础 Mixin（共享辅助方法、窗口对象、状态文件读写）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    import psutil
except ImportError:
    psutil = None

from api.utils.error_handler import api_error
from pyapp.config.config import Config


class SystemBaseMixin():
    '''系统类公共基础 Mixin：共享窗口对象、子进程辅助、状态文件读写等'''

    _window = None
    _close_timer = None

    @staticmethod
    def _subprocess_creationflags() -> int:
        if platform.system() == 'Windows' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            return subprocess.CREATE_NO_WINDOW
        return 0

    def _run_subprocess(self, args, **kwargs):
        options = dict(kwargs or {})
        options.setdefault('capture_output', True)
        options.setdefault('text', True)
        if platform.system() == 'Windows':
            options.setdefault('creationflags', self._subprocess_creationflags())
        return subprocess.run(args, **options)

    @staticmethod
    def _psutil_missing_response():
        return api_error('psutil 模块未安装，请先运行 pnpm run init 安装依赖后重试')

    @staticmethod
    def _format_create_time(timestamp):
        if not timestamp:
            return ''
        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError, OSError):
            return ''

    def _format_duration(self, seconds: float) -> str:
        seconds = max(0, int(seconds or 0))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        if days:
            return f'{days} 天 {hours} 小时'
        if hours:
            return f'{hours} 小时 {minutes} 分'
        if minutes:
            return f'{minutes} 分 {secs} 秒'
        return f'{secs} 秒'

    def _safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _estimate_path_size(self, target: Path) -> int:
        try:
            if target.is_file():
                return target.stat().st_size
            total = 0
            for child in target.rglob('*'):
                try:
                    if child.is_file():
                        total += child.stat().st_size
                except (PermissionError, OSError):
                    continue
            return total
        except (PermissionError, OSError):
            return 0

    # ==================== 状态文件读写 ====================

    def _startup_rules_file(self) -> Path:
        base_dir = Path(Config.appDataDir or Config.staticDir)
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / 'process_rules.json'

    def _c_drive_clean_state_file(self) -> Path:
        base_dir = Path(Config.appDataDir or Config.staticDir)
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / 'c_drive_clean_state.json'

    def _load_c_drive_clean_state(self) -> Dict[str, Any]:
        path = self._c_drive_clean_state_file()
        default_state = {
            'whitelist': [],
            'customRules': []
        }
        if not path.exists():
            return default_state
        try:
            with path.open('r', encoding='utf-8') as handler:
                data = json.load(handler)
            if not isinstance(data, dict):
                return default_state
            whitelist = data.get('whitelist') if isinstance(data.get('whitelist'), list) else []
            custom_rules = data.get('customRules') if isinstance(data.get('customRules'), list) else []
            return {
                'whitelist': [str(item) for item in whitelist if item],
                'customRules': custom_rules
            }
        except Exception:
            return default_state

    def _save_c_drive_clean_state(self, state: Dict[str, Any]):
        path = self._c_drive_clean_state_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'whitelist': state.get('whitelist', []),
            'customRules': state.get('customRules', [])
        }
        with path.open('w', encoding='utf-8') as handler:
            json.dump(payload, handler, ensure_ascii=False, indent=2)

    def _load_startup_rules(self) -> List[Dict]:
        path = self._startup_rules_file()
        if not path.exists():
            return []
        try:
            with path.open('r', encoding='utf-8') as handler:
                data = json.load(handler)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _save_startup_rules(self, rules: List[Dict]):
        path = self._startup_rules_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as handler:
            json.dump(rules, handler, ensure_ascii=False, indent=2)
