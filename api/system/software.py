#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Description: 系统类 - 软件管理 / 强力清理 Mixin（仅 Windows）
    扫描已安装软件、调用软件自带卸载程序、打开安装目录、强力粉碎安装目录。
    “强力粉碎”会自动结束占用目录的进程、清除只读属性解锁文件，然后永久删除（不进回收站）。
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

if platform.system() == 'Windows':
    import winreg

from api.utils import format_bytes
from api.utils.error_handler import api_error, api_success, safe_execute


# 注册表卸载信息根（显式读取 WOW6432Node，不依赖 WOW64 标志位）
def _uninstall_roots():
    return [
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM', 'x64'),
        (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall', 'HKLM-WOW64', 'x86'),
        (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall', 'HKCU', ''),
    ]


# 视为“更新补丁”而非独立软件，扫描时过滤
_RELEASE_TYPE_SKIP = {'update', 'hotfix', 'security update', 'servicepack'}
_KB_PATTERN = re.compile(r'^KB\d+', re.IGNORECASE)
_GUID_PATTERN = re.compile(r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}')


class SoftwareMixin():
    '''软件管理 / 强力清理 Mixin（仅 Windows）'''

    # ==================== 平台护栏 ====================

    @staticmethod
    def _software_supported() -> bool:
        return platform.system() == 'Windows'

    @staticmethod
    def _software_unsupported_error():
        return api_error('当前功能仅支持 Windows 平台')

    # ==================== 注册表读取辅助 ====================

    @staticmethod
    def _reg_get(item, name, default=''):
        '''安全读取注册表值，类型不符/不存在时返回默认值'''
        try:
            value, _ = winreg.QueryValueEx(item, name)
            return value
        except (FileNotFoundError, OSError):
            return default

    @staticmethod
    def _reg_get_int(item, name, default=0):
        try:
            value, _ = winreg.QueryValueEx(item, name)
            return int(value)
        except (FileNotFoundError, OSError, TypeError, ValueError):
            return default

    @staticmethod
    def _parse_msi_product_code(uninstall_string: str) -> str:
        '''从卸载命令中提取 MSI ProductCode（{GUID}）'''
        if not uninstall_string:
            return ''
        match = _GUID_PATTERN.search(str(uninstall_string))
        return match.group(0) if match else ''

    @staticmethod
    def _normalize_install_date(raw) -> str:
        '''InstallDate 通常为 YYYYMMDD，规范化为 YYYY-MM-DD'''
        if not raw:
            return ''
        text = str(raw).strip()
        try:
            return datetime.strptime(text, '%Y%m%d').strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            return text

    def _read_uninstall_entry(self, item, child_name, source, arch, include_system, compute_size) -> Optional[Dict]:
        '''读取并过滤单个卸载注册表项，返回标准化字典或 None（被过滤）'''
        name = str(self._reg_get(item, 'DisplayName', '') or '').strip()
        if not name:
            return None

        system_component = self._reg_get_int(item, 'SystemComponent', 0)
        if system_component == 1 and not include_system:
            return None

        # 子补丁项（依附于其它产品）
        if str(self._reg_get(item, 'ParentKeyName', '') or '').strip():
            return None

        release_type = str(self._reg_get(item, 'ReleaseType', '') or '').strip().lower()
        if release_type in _RELEASE_TYPE_SKIP:
            return None

        if _KB_PATTERN.match(name):
            return None

        uninstall_string = str(self._reg_get(item, 'UninstallString', '') or '').strip()
        quiet_uninstall = str(self._reg_get(item, 'QuietUninstallString', '') or '').strip()
        install_location = str(self._reg_get(item, 'InstallLocation', '') or '').strip().strip('"')
        publisher = str(self._reg_get(item, 'Publisher', '') or '').strip()

        # 完全没有卸载命令、安装目录和发行商的项目，多为噪声
        if not uninstall_string and not quiet_uninstall and not install_location and not publisher:
            return None

        is_msi = self._reg_get_int(item, 'WindowsInstaller', 0) == 1 or 'msiexec' in uninstall_string.lower()
        msi_code = self._parse_msi_product_code(quiet_uninstall or uninstall_string)

        # 大小：优先 EstimatedSize(KB)，缺失时按需回退实际目录测算
        estimated_size = self._reg_get_int(item, 'EstimatedSize', 0) * 1024
        if estimated_size <= 0 and compute_size and install_location:
            loc = Path(install_location)
            if loc.exists() and loc.is_dir():
                estimated_size = self._estimate_path_size(loc)

        location_exists = bool(install_location) and Path(install_location).exists()
        can_shred = location_exists and self._is_safe_to_shred(install_location)[0]

        return {
            'id': f'{source}|{child_name}',
            'name': name,
            'publisher': publisher,
            'version': str(self._reg_get(item, 'DisplayVersion', '') or '').strip(),
            'installDate': self._normalize_install_date(self._reg_get(item, 'InstallDate', '')),
            'installLocation': install_location,
            'estimatedSize': estimated_size,
            'estimatedSizeText': format_bytes(estimated_size) if estimated_size else '',
            'uninstallString': uninstall_string,
            'quietUninstallString': quiet_uninstall,
            'isMsi': is_msi,
            'msiProductCode': msi_code,
            'arch': arch,
            'source': source,
            'canUninstall': bool(uninstall_string or quiet_uninstall),
            'canOpen': location_exists,
            'canShred': can_shred,
        }

    def _iter_uninstall_entries(self, include_system=False, compute_size=True) -> List[Dict]:
        '''遍历三处注册表根，枚举并去重已安装软件'''
        merged: Dict[str, Dict] = {}

        for root, subkey, source, arch in _uninstall_roots():
            try:
                parent = winreg.OpenKey(root, subkey, 0, winreg.KEY_READ)
            except (OSError, PermissionError):
                continue
            with parent:
                i = 0
                while True:
                    try:
                        child_name = winreg.EnumKey(parent, i)
                        i += 1
                    except OSError:
                        break
                    try:
                        with winreg.OpenKey(parent, child_name, 0, winreg.KEY_READ) as item:
                            entry = self._read_uninstall_entry(
                                item, child_name, source, arch, include_system, compute_size
                            )
                    except (OSError, PermissionError):
                        continue
                    if not entry:
                        continue
                    # 去重 key：MSI ProductCode 优先，否则 名称|版本
                    dedupe_key = (entry['msiProductCode'] or '').lower() \
                        or f"{entry['name'].lower()}|{entry['version'].lower()}"
                    if dedupe_key in merged:
                        # 已存在则补齐缺失字段（HLKM 记录为权威，后到的仅补空缺）
                        kept = merged[dedupe_key]
                        for field in ('installLocation', 'uninstallString', 'quietUninstallString',
                                      'publisher', 'version', 'installDate'):
                            if not kept.get(field) and entry.get(field):
                                kept[field] = entry[field]
                        if kept.get('estimatedSize', 0) <= 0 and entry.get('estimatedSize', 0) > 0:
                            kept['estimatedSize'] = entry['estimatedSize']
                            kept['estimatedSizeText'] = entry['estimatedSizeText']
                        continue
                    merged[dedupe_key] = entry

        result = list(merged.values())
        result.sort(key=lambda e: e.get('name', '').lower())
        return result

    def _find_software_by_id(self, soft_id: str) -> Optional[Dict]:
        '''据 id 回查注册表，返回权威记录（破坏性操作不信任前端数据）'''
        if not soft_id:
            return None
        for entry in self._iter_uninstall_entries(include_system=True, compute_size=False):
            if entry.get('id') == soft_id:
                return entry
        return None

    # ==================== 安全护栏 ====================

    @staticmethod
    def _norm(path) -> str:
        return str(path).rstrip('\\/').lower()

    def _protected_dirs(self) -> set:
        '''按环境变量构造受保护目录集，兼容任意盘符/语言'''
        sysdrive = os.environ.get('SystemDrive', 'C:') + os.sep
        windir = os.environ.get('WINDIR') or os.environ.get('SystemRoot') or r'C:\Windows'
        userprofile = os.environ.get('USERPROFILE', r'C:\Users\Default')
        candidates = [
            sysdrive,
            windir,
            os.path.join(windir, 'System32'),
            os.path.join(windir, 'SysWOW64'),
            os.environ.get('ProgramFiles', r'C:\Program Files'),
            os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
            os.environ.get('ProgramData', r'C:\ProgramData'),
            os.environ.get('PUBLIC', r'C:\Users\Public'),
            os.path.dirname(userprofile) if userprofile else r'C:\Users',  # C:\Users
            userprofile,
        ]
        protected = set()
        for c in candidates:
            if not c:
                continue
            try:
                protected.add(self._norm(Path(c).resolve()))
            except Exception:
                protected.add(self._norm(Path(c)))
        return protected

    def _is_safe_to_shred(self, raw_path):
        '''返回 (ok, reason)。仅允许删除受保护目录的“子目录”，拒绝根/系统目录本身及其祖先'''
        if not raw_path or not str(raw_path).strip():
            return False, '路径为空'
        try:
            p = Path(raw_path).resolve()
        except Exception:
            return False, '路径无效'
        if not p.exists():
            return False, '目录不存在'
        if not p.is_dir():
            return False, '目标不是目录'
        # 磁盘根目录（C:\）：parent 等于自身
        if p.parent == p:
            return False, '禁止删除磁盘根目录'
        if len(p.parts) < 2:
            return False, '路径层级过浅，禁止删除'

        np = self._norm(p)
        for prot in self._protected_dirs():
            if np == prot:
                return False, f'禁止删除受保护目录: {p}'
            # 目标是受保护目录的祖先（如目标=C:\，受保护=C:\Windows）
            if prot.startswith(np + os.sep):
                return False, f'目标包含受保护目录，禁止删除: {p}'
        return True, ''

    # ==================== 强力删除（解锁 + 永久粉碎） ====================

    def _kill_processes_in_dir(self, dir_path: Path) -> List[Dict]:
        '''结束 exe / cwd / 打开句柄位于目标目录下的进程（自动解锁占用）'''
        killed: List[Dict] = []
        if psutil is None:
            return killed
        target = self._norm(dir_path)
        own_pid = os.getpid()

        def _under_target(path_str) -> bool:
            if not path_str:
                return False
            try:
                np = self._norm(Path(path_str))
            except Exception:
                return False
            return np == target or np.startswith(target + os.sep)

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cwd']):
            try:
                pid = proc.info.get('pid')
                if not pid or pid == own_pid or pid in (0, 4):
                    continue
                hit = _under_target(proc.info.get('exe')) or _under_target(proc.info.get('cwd'))
                if not hit:
                    # 尽力检查打开的文件句柄（可能需要权限）
                    try:
                        for f in proc.open_files():
                            if _under_target(f.path):
                                hit = True
                                break
                    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                        pass
                if not hit:
                    continue
                name = proc.info.get('name') or ''
                result = self.system_killProcess(pid)
                if isinstance(result, dict) and result.get('code') == 0:
                    killed.append({'pid': pid, 'name': name})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return killed

    def _force_delete_tree(self, path: Path) -> List[str]:
        '''清除只读属性并重试删除，返回仍无法删除的路径列表'''
        failed: List[str] = []

        def on_error(func, p, exc_info):
            try:
                os.chmod(p, stat.S_IWRITE)
            except Exception:
                pass
            try:
                func(p)
            except Exception:
                failed.append(str(p))

        # 最多重试 3 次以应对 AV / 句柄临时占用
        for _attempt in range(3):
            failed = []
            try:
                if sys.version_info >= (3, 12):
                    shutil.rmtree(path, onexc=lambda f, p, e: on_error(f, p, e))
                else:
                    shutil.rmtree(path, onerror=on_error)
            except FileNotFoundError:
                return []
            except Exception as exc:
                failed.append(f'{path}: {exc}')
            if not path.exists():
                return []
            if not failed:
                break
        return failed

    # ==================== 对外 API ====================

    @safe_execute
    def system_listInstalledSoftware(self, payload=None):
        '''扫描已安装软件列表'''
        if not self._software_supported():
            return api_success('当前平台不支持软件扫描', total=0, list=[])

        keyword = ''
        include_system = False
        compute_size = True
        if isinstance(payload, dict):
            keyword = str(payload.get('keyword', '') or '').strip().lower()
            include_system = bool(payload.get('includeSystemComponents', False))
            compute_size = bool(payload.get('computeSize', True))

        entries = self._iter_uninstall_entries(include_system=include_system, compute_size=compute_size)
        if keyword:
            entries = [
                e for e in entries
                if keyword in e['name'].lower() or keyword in (e.get('publisher') or '').lower()
            ]
        return api_success('获取成功', total=len(entries), list=entries)

    @safe_execute
    def system_uninstallSoftware(self, payload=None):
        '''调用软件自带卸载程序'''
        if not self._software_supported():
            return self._software_unsupported_error()

        quiet = False
        if isinstance(payload, dict):
            soft_id = payload.get('id')
            quiet = bool(payload.get('quiet', False))
        else:
            soft_id = payload

        if not soft_id:
            return api_error('缺少软件标识，请刷新列表后重试')
        entry = self._find_software_by_id(soft_id)
        if not entry:
            return api_error('未找到该软件，请刷新列表后重试')

        uninstall_string = (entry.get('uninstallString') or '').strip()
        quiet_uninstall = (entry.get('quietUninstallString') or '').strip()
        is_msi = entry.get('isMsi')
        msi_code = entry.get('msiProductCode') or self._parse_msi_product_code(quiet_uninstall or uninstall_string)

        creationflags = self._subprocess_creationflags()

        # MSI：用 msiexec /x 显式构造，避免 UninstallString 中可能的 /I（安装）参数
        if (is_msi or 'msiexec' in (uninstall_string or '').lower()) and msi_code:
            args = ['msiexec', '/x', msi_code]
            if quiet:
                args += ['/qn', '/norestart']
            process = subprocess.Popen(args, creationflags=creationflags)
            return api_success('已启动卸载程序', pid=process.pid, mode='quiet' if quiet else 'ui')

        command = quiet_uninstall if (quiet and quiet_uninstall) else (uninstall_string or quiet_uninstall)
        if not command:
            return api_error('该软件未提供卸载命令')

        # 命令只取自刚刚回查的注册表权威记录；不经过 cmd.exe，避免解释 shell 元字符。
        process = subprocess.Popen(command, shell=False, creationflags=creationflags)
        return api_success('已启动卸载程序，完成后请刷新列表', pid=process.pid,
                           mode='quiet' if (quiet and quiet_uninstall) else 'ui')

    @safe_execute
    def system_openSoftwareDir(self, payload=None):
        '''在资源管理器中打开软件安装目录'''
        if not self._software_supported():
            return self._software_unsupported_error()

        soft_id = payload.get('id') if isinstance(payload, dict) else payload
        if not soft_id:
            return api_error('缺少软件标识，请刷新列表后重试')
        entry = self._find_software_by_id(soft_id)
        if not entry:
            return api_error('未找到该软件，请刷新列表后重试')
        path = entry.get('installLocation')

        if not path:
            return api_error('该软件未提供安装目录')
        target = Path(path)
        if not target.exists():
            return api_error('安装目录不存在')
        subprocess.Popen(['explorer', str(target)])
        return api_success('已打开安装目录', path=str(target))

    @safe_execute
    def system_shredSoftwareDir(self, payload=None):
        '''强力粉碎安装目录：结束占用进程 → 解锁 → 永久删除（不进回收站）'''
        if not self._software_supported():
            return self._software_unsupported_error()

        kill_processes = True
        if isinstance(payload, dict):
            kill_processes = bool(payload.get('killProcesses', True))
            soft_id = payload.get('id')
        else:
            soft_id = payload

        if not soft_id:
            return api_error('缺少软件标识，请刷新列表后重试')
        entry = self._find_software_by_id(soft_id)
        if not entry:
            return api_error('未找到该软件，请刷新列表后重试')
        path = entry.get('installLocation')
        if not path:
            return api_error('该软件未记录安装目录，无法粉碎')

        # 安全护栏：破坏性操作必须先过
        ok, reason = self._is_safe_to_shred(path)
        if not ok:
            if reason == '目录不存在':
                return api_error('安装目录不存在或已被删除')
            return api_error(f'禁止删除受保护的系统目录：{reason}')

        target = Path(path).resolve()
        freed_bytes = self._estimate_path_size(target)

        killed_processes = []
        if kill_processes:
            killed_processes = self._kill_processes_in_dir(target)

        failed_items = self._force_delete_tree(target)

        freed_text = format_bytes(freed_bytes) if freed_bytes else '0 B'

        if not target.exists() and not failed_items:
            return api_success('已彻底粉碎安装目录', path=str(target),
                               freedBytes=freed_bytes, freedText=freed_text,
                               killedProcesses=killed_processes)
        if not failed_items:
            # 目录已不存在但 onerror 记录为空，视为成功
            return api_success('已彻底粉碎安装目录', path=str(target),
                               freedBytes=freed_bytes, freedText=freed_text,
                               killedProcesses=killed_processes)
        # 还有文件未删
        deleted_any = freed_bytes > 0 and target.exists()
        if target.exists() and len(failed_items) > 0 and not deleted_any:
            return api_error('粉碎失败，可能需要管理员权限或文件被占用',
                             path=str(target), failedItems=failed_items,
                             killedProcesses=killed_processes)
        return api_success(f'部分文件已粉碎，{len(failed_items)} 项仍被占用，请关闭相关程序后重试',
                           path=str(target), freedBytes=freed_bytes, freedText=freed_text,
                           failedItems=failed_items, killedProcesses=killed_processes)
