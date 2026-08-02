#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 开机启动项 Mixin（v2.0 仅保留只读查看）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, List

if platform.system() == 'Windows':
    import winreg

from api.utils.error_handler import api_error, api_success, safe_execute


class StartupMixin():
    '''开机启动项 Mixin：只读查看系统启动项'''

    @safe_execute
    def system_listStartupRules(self):
        '''列出系统自动启动项。v2.0 不再加载或执行自定义命令。'''
        return api_success(rules=self._load_system_startup_items(), readOnly=True)

    def _load_system_startup_items(self) -> List[Dict]:
        '''读取系统开机启动项'''
        items = []
        if platform.system() != 'Windows':
            return items

        # 注册表路径
        reg_paths = [
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Run', 'HKCU'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Run', 'HKLM'),
            (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\RunOnce', 'HKCU_Once'),
            (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\RunOnce', 'HKLM_Once'),
        ]

        for hkey, subkey, source in reg_paths:
            try:
                with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            items.append({
                                'id': f'sys_{source}_{name}',
                                'name': name,
                                'command': value,
                                'description': f'系统启动项 ({source})',
                                'autoStart': True,
                                'isSystem': True,
                                'source': source,
                                'regKey': subkey
                            })
                            i += 1
                        except OSError:
                            break
            except (OSError, PermissionError):
                continue

        # 启动文件夹
        startup_folders = [
            (Path(os.environ.get('APPDATA', '')) / r'Microsoft\Windows\Start Menu\Programs\Startup', '用户启动文件夹'),
            (Path(os.environ.get('PROGRAMDATA', '')) / r'Microsoft\Windows\Start Menu\Programs\Startup', '公共启动文件夹'),
        ]

        for folder, desc in startup_folders:
            if folder.exists() and folder.is_dir():
                for item in folder.iterdir():
                    if item.is_file() and item.suffix.lower() in ('.lnk', '.exe', '.bat', '.cmd', '.vbs'):
                        items.append({
                            'id': f'sys_folder_{item.name}',
                            'name': item.stem,
                            'command': str(item),
                            'description': desc,
                            'autoStart': True,
                            'isSystem': True,
                            'source': 'StartupFolder',
                            'filePath': str(item)
                        })

        return items

    @safe_execute
    def system_saveStartupRule(self, rule):
        '''v2.0 已移除任意启动命令写入能力。'''
        return api_error('v2.0 已移除自定义启动命令，请使用系统设置管理启动项')

    @safe_execute
    def system_removeStartupRule(self, payload=None):
        '''v2.0 已移除应用内启动项修改能力。'''
        return api_error('v2.0 的启动项页面为只读，请使用系统设置修改')

    @safe_execute
    def system_runStartupRule(self, payload=None):
        '''v2.0 禁止执行用户提供的任意命令。'''
        return api_error('v2.0 已移除任意启动命令执行能力')

    @safe_execute
    def system_runSystemStartup(self, payload=None):
        '''v2.0 禁止执行系统启动项中的任意命令。'''
        return api_error('v2.0 的启动项页面为只读')

    @safe_execute
    def system_openStartupLocation(self, payload=None):
        '''打开启动项所在位置'''
        source = None
        reg_key = None
        file_path = None
        if isinstance(payload, dict):
            source = payload.get('source')
            reg_key = payload.get('regKey')
            file_path = payload.get('filePath')

        if platform.system() != 'Windows':
            return api_error('仅支持 Windows 平台')

        # 如果是启动文件夹中的项目，打开文件夹并选中文件
        if source == 'StartupFolder' and file_path:
            file_obj = Path(file_path)
            if file_obj.exists():
                subprocess.Popen(['explorer', '/select,', str(file_obj)])
                return api_success()
            else:
                return api_error('文件不存在')

        # 如果是注册表项，打开注册表编辑器
        if reg_key:
            # 构建完整的注册表路径
            if source in ('HKCU', 'HKCU_Once'):
                full_path = f'HKEY_CURRENT_USER\\{reg_key}'
            else:
                full_path = f'HKEY_LOCAL_MACHINE\\{reg_key}'

            # 设置注册表编辑器的最后访问路径
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Applets\Regedit',
                    0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, 'LastKey', 0, winreg.REG_SZ, f'Computer\\{full_path}')
            except Exception:
                pass

            # 打开注册表编辑器
            subprocess.Popen(['regedit'])
            return api_success()

        return api_error('无法确定启动项位置')
