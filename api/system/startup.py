#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 开机启动项 Mixin（自定义启动规则、系统启动项管理）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

if platform.system() == 'Windows':
    import winreg

from api.utils.error_handler import api_success, api_error, safe_execute
from pyapp.config.config import Config


class StartupMixin():
    '''开机启动项 Mixin：自定义启动规则、系统启动项管理'''

    @safe_execute
    def system_listStartupRules(self):
        '''列出自动启动规则（包括系统启动项）'''
        # 自定义规则
        custom_rules = self._load_startup_rules()
        # 系统启动项
        system_rules = self._load_system_startup_items()
        # 合并：系统项在前，自定义在后
        all_rules = system_rules + custom_rules
        return api_success(rules=all_rules)

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
        '''新增或更新自动启动规则'''
        if not isinstance(rule, dict):
            raise ValueError('参数格式错误')
        name = (rule.get('name') or '').strip() or '未命名规则'
        command = (rule.get('command') or '').strip()
        if not command:
            raise ValueError('请设置启动命令')
        auto_start = bool(rule.get('autoStart', True))
        description = rule.get('description', '')
        rules = self._load_startup_rules()
        rule_id = rule.get('id') or ''
        now = datetime.now(timezone.utc).isoformat()
        updated = False
        if rule_id:
            for item in rules:
                if item.get('id') == rule_id:
                    item.update({
                        'name': name,
                        'command': command,
                        'autoStart': auto_start,
                        'description': description,
                        'updatedAt': now
                    })
                    updated = True
                    break
            if not updated:
                raise ValueError('规则不存在')
        else:
            rule_id = uuid.uuid4().hex
            rules.append({
                'id': rule_id,
                'name': name,
                'command': command,
                'autoStart': auto_start,
                'description': description,
                'createdAt': now,
                'updatedAt': now,
                'lastRun': '',
                'lastPid': None
            })
        self._save_startup_rules(rules)
        return api_success(id=rule_id, rules=rules)

    @safe_execute
    def system_removeStartupRule(self, payload=None):
        '''删除自动启动规则'''
        rule_id = None
        if isinstance(payload, dict):
            rule_id = payload.get('id')
        else:
            rule_id = payload
        if not rule_id:
            raise ValueError('请提供规则 ID')
        rules = self._load_startup_rules()
        new_rules = [rule for rule in rules if rule.get('id') != rule_id]
        if len(new_rules) == len(rules):
            raise ValueError('规则不存在')
        self._save_startup_rules(new_rules)
        return api_success(rules=new_rules)

    @safe_execute
    def system_runStartupRule(self, payload=None):
        '''运行自动启动规则'''
        rule_id = None
        if isinstance(payload, dict):
            rule_id = payload.get('id')
        else:
            rule_id = payload
        if not rule_id:
            raise ValueError('请提供规则 ID')
        rules = self._load_startup_rules()
        target = next((rule for rule in rules if rule.get('id') == rule_id), None)
        if not target:
            raise ValueError('规则不存在')
        command = target.get('command')
        if not command:
            raise ValueError('规则未设置命令')
        creationflags = 0
        if platform.system() == 'Windows' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creationflags = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(command, shell=True, creationflags=creationflags)
        target['lastRun'] = datetime.now(timezone.utc).isoformat()
        target['lastPid'] = process.pid
        self._save_startup_rules(rules)
        return api_success(pid=process.pid, rule=target)

    @safe_execute
    def system_runSystemStartup(self, payload=None):
        '''运行系统启动项'''
        command = None
        file_path = None
        if isinstance(payload, dict):
            command = payload.get('command')
            file_path = payload.get('filePath')
        if not command and not file_path:
            return api_error('请提供启动命令')

        # 如果是启动文件夹中的文件，使用 os.startfile 打开
        if file_path and Path(file_path).exists():
            if Config.appIsMacOS:
                subprocess.Popen(['open', file_path])
            else:
                os.startfile(file_path)
            return api_success()

        # 否则执行命令
        creationflags = 0
        if platform.system() == 'Windows' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creationflags = subprocess.CREATE_NO_WINDOW
        subprocess.Popen(command, shell=True, creationflags=creationflags)
        return api_success()

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
