#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 清理 Mixin（垃圾清理、C 盘专清、注册表清理）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import fnmatch
import os
import platform
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

if platform.system() == 'Windows':
    import winreg

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

from api.utils import format_bytes
from api.utils.error_handler import api_success, api_error


class CleanupMixin():
    '''清理 Mixin：垃圾清理、C 盘专清、注册表清理'''

    # ==================== 垃圾清理 ====================

    def _get_junk_locations(self) -> List[Dict]:
        '''获取垃圾文件扫描位置'''
        locations = []

        # Windows 临时文件
        temp_dir = os.environ.get('TEMP') or os.environ.get('TMP')
        if temp_dir and Path(temp_dir).exists():
            locations.append({
                'category': 'temp_user',
                'name': '用户临时文件',
                'path': temp_dir,
                'patterns': ['*']
            })

        # Windows 系统临时文件
        if platform.system() == 'Windows':
            win_temp = Path('C:/Windows/Temp')
            if win_temp.exists():
                locations.append({
                    'category': 'temp_system',
                    'name': '系统临时文件',
                    'path': str(win_temp),
                    'patterns': ['*']
                })

            # Windows 更新缓存
            update_cache = Path('C:/Windows/SoftwareDistribution/Download')
            if update_cache.exists():
                locations.append({
                    'category': 'windows_update',
                    'name': 'Windows 更新缓存',
                    'path': str(update_cache),
                    'patterns': ['*']
                })

            # Windows 预读取
            prefetch = Path('C:/Windows/Prefetch')
            if prefetch.exists():
                locations.append({
                    'category': 'prefetch',
                    'name': '预读取文件',
                    'path': str(prefetch),
                    'patterns': ['*.pf']
                })

        # 浏览器缓存
        appdata_local = os.environ.get('LOCALAPPDATA', '')
        if appdata_local:
            # Chrome 缓存
            chrome_cache = Path(appdata_local) / 'Google/Chrome/User Data/Default/Cache'
            if chrome_cache.exists():
                locations.append({
                    'category': 'browser_chrome',
                    'name': 'Chrome 浏览器缓存',
                    'path': str(chrome_cache),
                    'patterns': ['*']
                })

            # Edge 缓存
            edge_cache = Path(appdata_local) / 'Microsoft/Edge/User Data/Default/Cache'
            if edge_cache.exists():
                locations.append({
                    'category': 'browser_edge',
                    'name': 'Edge 浏览器缓存',
                    'path': str(edge_cache),
                    'patterns': ['*']
                })

        # Firefox 缓存
        appdata_roaming = os.environ.get('APPDATA', '')
        if appdata_roaming:
            firefox_profiles = Path(appdata_roaming) / 'Mozilla/Firefox/Profiles'
            if firefox_profiles.exists():
                for profile in firefox_profiles.iterdir():
                    if profile.is_dir():
                        cache_dir = profile / 'cache2'
                        if cache_dir.exists():
                            locations.append({
                                'category': 'browser_firefox',
                                'name': f'Firefox 缓存 ({profile.name})',
                                'path': str(cache_dir),
                                'patterns': ['*']
                            })
                            break  # 只取第一个 profile

        # 回收站 (Windows)
        if platform.system() == 'Windows':
            locations.append({
                'category': 'recycle_bin',
                'name': '回收站',
                'path': '$Recycle.Bin',
                'patterns': ['*'],
                'special': True
            })

        return locations

    @staticmethod
    def _normalize_categories(categories):
        if not isinstance(categories, list):
            return set()
        return {str(item).strip() for item in categories if str(item).strip()}

    @staticmethod
    def _is_on_drive(path: Path, drive_letter: str) -> bool:
        raw = str(path).replace('/', '\\')
        if len(raw) >= 2 and raw[1] == ':':
            return raw[0].upper() == drive_letter.upper()
        try:
            resolved = path.resolve()
            resolved_raw = str(resolved).replace('/', '\\')
            return len(resolved_raw) >= 2 and resolved_raw[1] == ':' and resolved_raw[0].upper() == drive_letter.upper()
        except (OSError, RuntimeError):
            return False

    def _existing_paths_on_drive(self, candidates, drive_letter='C') -> List[str]:
        paths = []
        seen = set()
        for candidate in candidates or []:
            if not candidate:
                continue
            path_obj = Path(candidate)
            if not path_obj.exists():
                continue
            if not self._is_on_drive(path_obj, drive_letter):
                continue
            key = str(path_obj).lower()
            if key in seen:
                continue
            seen.add(key)
            paths.append(str(path_obj))
        return paths

    def _resolve_location_paths(self, location: Dict) -> List[str]:
        paths = []
        seen = set()
        dir_values = location.get('paths', [])
        file_values = location.get('files', [])
        has_multi_targets = bool(dir_values) or bool(file_values)

        if has_multi_targets:
            values = []
            if isinstance(dir_values, list):
                values.extend(dir_values)
            if isinstance(file_values, list):
                values.extend(file_values)
            for value in values:
                if not value:
                    continue
                key = str(value).lower()
                if key in seen:
                    continue
                seen.add(key)
                paths.append(str(value))
            return paths

        single_path = location.get('path')
        if isinstance(single_path, str) and single_path and not location.get('pathHint'):
            key = single_path.lower()
            if key not in seen:
                seen.add(key)
                paths.append(single_path)
        return paths

    def _location_display_path(self, location: Dict) -> str:
        if location.get('path'):
            return location.get('path')
        paths = self._resolve_location_paths(location)
        if not paths:
            return location.get('pathHint', '')
        if len(paths) <= 2:
            return '；'.join(paths)
        return f'{paths[0]}；{paths[1]} 等 {len(paths)} 项'

    def _get_documents_roots(self, drive_letter='C') -> List[Path]:
        roots = []
        seen = set()
        user_profile = Path(os.environ.get('USERPROFILE') or Path.home())
        candidates = [
            user_profile / 'Documents',
            user_profile / 'OneDrive' / 'Documents',
            Path.home() / 'Documents'
        ]
        for candidate in candidates:
            key = str(candidate).lower()
            if key in seen:
                continue
            seen.add(key)
            if candidate.exists() and candidate.is_dir() and self._is_on_drive(candidate, drive_letter):
                roots.append(candidate)
        return roots

    def _get_c_drive_clean_locations(self) -> List[Dict]:
        locations = []
        if platform.system() != 'Windows':
            return locations

        c_drive = 'C'
        local_appdata = Path(os.environ.get('LOCALAPPDATA', ''))
        appdata = Path(os.environ.get('APPDATA', ''))
        user_profile = Path(os.environ.get('USERPROFILE') or Path.home())
        program_data = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData'))

        def add_location(
            category: str,
            name: str,
            description: str,
            paths=None,
            files=None,
            patterns=None,
            risk='low',
            special=None
        ):
            entry = {
                'category': category,
                'name': name,
                'description': description,
                'risk': risk,
                'patterns': patterns or ['*']
            }
            if special:
                entry['special'] = special
                entry['driveLetter'] = c_drive
                entry['path'] = f'{c_drive}:\\$Recycle.Bin'
                locations.append(entry)
                return

            existing_dirs = self._existing_paths_on_drive(paths or [], c_drive)
            existing_files = self._existing_paths_on_drive(files or [], c_drive)
            if existing_dirs:
                entry['paths'] = existing_dirs
            if existing_files:
                entry['files'] = existing_files
            if not existing_dirs and not existing_files:
                entry['pathHint'] = '未检测到对应目录'
            locations.append(entry)

        add_location(
            'c_recycle_bin',
            '回收站',
            '清空 C 盘回收站文件',
            special='recycle_bin'
        )
        add_location(
            'c_windows_temp',
            'Windows 临时目录',
            '系统运行产生的临时文件',
            paths=['C:/Windows/Temp']
        )
        add_location(
            'c_user_temp',
            '用户临时目录',
            '应用临时缓存与残留安装文件',
            paths=[local_appdata / 'Temp']
        )
        add_location(
            'c_windows_update',
            '系统更新缓存',
            'Windows 更新下载缓存',
            paths=['C:/Windows/SoftwareDistribution/Download']
        )
        add_location(
            'c_delivery_optimization',
            '传递优化缓存',
            'Windows 更新 P2P 缓存',
            paths=[program_data / 'Microsoft/Windows/DeliveryOptimization/Cache']
        )
        add_location(
            'c_prefetch',
            '预读取缓存',
            '应用启动预读取缓存（.pf）',
            paths=['C:/Windows/Prefetch'],
            patterns=['*.pf']
        )
        add_location(
            'c_windows_logs',
            '系统日志',
            'Windows 日志与跟踪文件',
            paths=['C:/Windows/Logs', 'C:/Windows/System32/LogFiles'],
            patterns=['*.log', '*.etl', '*.tmp']
        )
        add_location(
            'c_crash_dump',
            '崩溃转储文件',
            '系统蓝屏/崩溃生成的转储文件',
            paths=['C:/Windows/Minidump'],
            files=['C:/Windows/MEMORY.DMP'],
            patterns=['*.dmp']
        )
        add_location(
            'c_wer_reports',
            '错误报告缓存',
            'Windows 错误报告队列与归档',
            paths=[
                program_data / 'Microsoft/Windows/WER/ReportArchive',
                program_data / 'Microsoft/Windows/WER/ReportQueue'
            ]
        )
        add_location(
            'c_thumbnail_cache',
            '缩略图缓存',
            '资源管理器缩略图/Icon 缓存',
            paths=[local_appdata / 'Microsoft/Windows/Explorer'],
            patterns=['thumbcache_*.db', 'iconcache_*.db']
        )
        add_location(
            'c_d3d_shader_cache',
            'DirectX 着色器缓存',
            '显卡着色器缓存文件',
            paths=[local_appdata / 'D3DSCache']
        )
        add_location(
            'c_chrome_cache',
            'Chrome 缓存',
            'Chrome 浏览器缓存',
            paths=[
                local_appdata / 'Google/Chrome/User Data/Default/Cache',
                local_appdata / 'Google/Chrome/User Data/Default/Code Cache'
            ]
        )
        add_location(
            'c_edge_cache',
            'Edge 缓存',
            'Edge 浏览器缓存',
            paths=[
                local_appdata / 'Microsoft/Edge/User Data/Default/Cache',
                local_appdata / 'Microsoft/Edge/User Data/Default/Code Cache'
            ]
        )

        firefox_paths = []
        profiles_root = appdata / 'Mozilla/Firefox/Profiles'
        if profiles_root.exists():
            for profile in profiles_root.iterdir():
                if not profile.is_dir():
                    continue
                firefox_paths.append(profile / 'cache2')
                firefox_paths.append(profile / 'startupCache')
        add_location(
            'c_firefox_cache',
            'Firefox 缓存',
            'Firefox 浏览器缓存',
            paths=firefox_paths
        )

        add_location(
            'c_npm_cache',
            'NPM 缓存',
            'npm 下载缓存与索引缓存',
            paths=[
                appdata / 'npm-cache',
                local_appdata / 'npm-cache',
                user_profile / '.npm/_cacache'
            ],
            risk='medium'
        )
        add_location(
            'c_pnpm_cache',
            'PNPM 缓存',
            'pnpm store 缓存',
            paths=[
                local_appdata / 'pnpm-store',
                local_appdata / 'pnpm/store',
                user_profile / '.pnpm-store'
            ],
            risk='medium'
        )
        add_location(
            'c_yarn_cache',
            'Yarn 缓存',
            'yarn 包缓存',
            paths=[
                local_appdata / 'Yarn/Cache',
                appdata / 'Yarn/Cache'
            ],
            risk='medium'
        )
        add_location(
            'c_pip_cache',
            'PIP 缓存',
            'pip 下载缓存',
            paths=[local_appdata / 'pip/Cache'],
            risk='medium'
        )

        wechat_recv_paths = []
        qq_recv_paths = []
        for docs_root in self._get_documents_roots(c_drive):
            for base_name in ('WeChat Files', '微信文件'):
                wechat_root = docs_root / base_name
                if not wechat_root.exists():
                    continue
                for account_dir in wechat_root.iterdir():
                    if not account_dir.is_dir():
                        continue
                    wechat_recv_paths.append(account_dir / 'FileStorage/File')
            qq_root = docs_root / 'Tencent Files'
            if qq_root.exists():
                for account_dir in qq_root.iterdir():
                    if not account_dir.is_dir():
                        continue
                    qq_recv_paths.append(account_dir / 'FileRecv')

        add_location(
            'c_wechat_recv',
            '微信接收文件',
            '微信 FileStorage/File 目录中的接收文件',
            paths=wechat_recv_paths,
            risk='high'
        )
        add_location(
            'c_qq_recv',
            'QQ 接收文件',
            'QQ FileRecv 目录中的接收文件',
            paths=qq_recv_paths,
            risk='high'
        )

        for item in locations:
            item['path'] = self._location_display_path(item)
        return locations

    def _scan_directory(self, path: str, patterns: List[str], max_files: int = 5000) -> tuple:
        '''扫描目录中的文件，返回(文件列表, 总大小)'''
        files = []
        total_size = 0
        seen = set()
        try:
            target = Path(path)
            if not target.exists():
                return files, total_size

            if target.is_file():
                if any(fnmatch.fnmatch(target.name, pattern) for pattern in patterns):
                    stat = target.stat()
                    size = stat.st_size
                    modified_at = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    files.append({
                        'path': str(target),
                        'name': target.name,
                        'size': size,
                        'sizeText': format_bytes(size),
                        'ext': target.suffix.lower(),
                        'modifiedAt': stat.st_mtime,
                        'modifiedAtText': modified_at
                    })
                    total_size += size
                return files, total_size

            for pattern in patterns:
                if len(files) >= max_files:
                    break
                for item in target.rglob(pattern):
                    if len(files) >= max_files:
                        break
                    key = str(item).lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        if item.is_file():
                            stat = item.stat()
                            size = stat.st_size
                            modified_at = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                            files.append({
                                'path': str(item),
                                'name': item.name,
                                'size': size,
                                'sizeText': format_bytes(size),
                                'ext': item.suffix.lower(),
                                'modifiedAt': stat.st_mtime,
                                'modifiedAtText': modified_at
                            })
                            total_size += size
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass
        return files, total_size

    def _get_recycle_bin_size(self, drive_letter=None) -> tuple:
        '''获取回收站大小'''
        files = []
        total_size = 0
        if platform.system() != 'Windows':
            return files, total_size

        try:
            if drive_letter:
                command = (
                    f"$sum = Get-ChildItem -LiteralPath '{drive_letter}:\\$Recycle.Bin' -Force -Recurse -File "
                    f"-ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum | "
                    "Select-Object -ExpandProperty Sum; if ($null -eq $sum) { 0 } else { $sum }"
                )
                recycle_path = f'{drive_letter}:\\$Recycle.Bin'
            else:
                command = (
                    "(New-Object -ComObject Shell.Application).NameSpace(10).Items() | "
                    "ForEach-Object { $_.Size } | Measure-Object -Sum | Select-Object -ExpandProperty Sum"
                )
                recycle_path = '$Recycle.Bin'

            result = self._run_subprocess(
                ['powershell', '-NoProfile', '-Command', command],
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    total_size = int(float(result.stdout.strip()))
                except ValueError:
                    total_size = 0

            if total_size > 0:
                files.append({
                    'path': recycle_path,
                    'name': '回收站',
                    'size': total_size,
                    'sizeText': format_bytes(total_size)
                })
        except Exception:
            pass
        return files, total_size

    def _scan_location(self, location: Dict) -> tuple:
        if location.get('special') and str(location.get('category', '')).endswith('recycle_bin'):
            return self._get_recycle_bin_size(location.get('driveLetter'))

        patterns = location.get('patterns', ['*'])
        max_files = int(location.get('maxFiles', 5000))
        files = []
        total_size = 0
        remaining = max_files

        min_size_bytes = int(location.get('minSizeBytes', 0) or 0)
        older_than_days = int(location.get('olderThanDays', 0) or 0)
        ext_filters = location.get('extFilters', []) if isinstance(location.get('extFilters'), list) else []
        ext_filters = [str(ext).lower() for ext in ext_filters if str(ext).strip()]

        now_ts = time.time()

        for target in self._resolve_location_paths(location):
            if remaining <= 0:
                break
            current_files, current_size = self._scan_directory(target, patterns, remaining)

            if min_size_bytes > 0 or older_than_days > 0 or ext_filters:
                filtered_files = []
                filtered_size = 0
                for item in current_files:
                    size = int(item.get('size') or 0)
                    if min_size_bytes > 0 and size < min_size_bytes:
                        continue
                    ext = str(item.get('ext') or '').lower()
                    if ext_filters and ext not in ext_filters:
                        continue
                    modified_at = float(item.get('modifiedAt') or 0)
                    if older_than_days > 0 and modified_at > 0:
                        age_days = (now_ts - modified_at) / 86400
                        if age_days < older_than_days:
                            continue
                    filtered_files.append(item)
                    filtered_size += size
                current_files, current_size = filtered_files, filtered_size

            files.extend(current_files)
            total_size += current_size
            remaining = max_files - len(files)
        return files, total_size

    def _scan_locations(self, locations: List[Dict], categories=None, include_empty=False):
        selected = self._normalize_categories(categories)
        items = []
        total_size = 0
        state = self._load_c_drive_clean_state()
        whitelist = {str(item).lower() for item in state.get('whitelist', []) if item}

        for location in locations:
            category = location.get('category')
            if selected and category not in selected:
                continue

            files, size = self._scan_location(location)
            if whitelist:
                filtered = [file for file in files if str(file.get('path', '')).lower() not in whitelist]
                if len(filtered) != len(files):
                    files = filtered
                    size = sum(int(file.get('size') or 0) for file in files)

            if not include_empty and not files and size <= 0:
                continue

            item = {
                'category': category,
                'name': location.get('name', category),
                'path': self._location_display_path(location),
                'fileCount': len(files),
                'size': size,
                'sizeText': format_bytes(size),
                'files': files[:300]
            }
            if location.get('description'):
                item['description'] = location.get('description')
            if location.get('risk'):
                item['risk'] = location.get('risk')
            items.append(item)
            total_size += size

        return api_success(
            items=items,
            totalSize=total_size,
            totalSizeText=format_bytes(total_size),
            categoryCount=len(items)
        )

    def _clear_recycle_bin(self, drive_letter=None):
        if platform.system() != 'Windows':
            return False
        command = 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'
        if drive_letter:
            command = f'Clear-RecycleBin -DriveLetter {drive_letter} -Force -ErrorAction SilentlyContinue'
        try:
            result = self._run_subprocess(
                ['powershell', '-NoProfile', '-Command', command],
                timeout=60
            )
            return result.returncode == 0
        except Exception:
            return False

    def _clean_location(self, location: Dict):
        if location.get('special') and str(location.get('category', '')).endswith('recycle_bin'):
            _, before_size = self._get_recycle_bin_size(location.get('driveLetter'))
            ok = self._clear_recycle_bin(location.get('driveLetter'))
            if ok:
                return before_size, 1 if before_size > 0 else 0, []
            return 0, 0, ['回收站清理失败']

        cleared_size = 0
        cleared_count = 0
        errors = []
        patterns = location.get('patterns', ['*'])

        for target in self._resolve_location_paths(location):
            target_path = Path(target)
            if not target_path.exists():
                continue
            try:
                if target_path.is_file():
                    if any(fnmatch.fnmatch(target_path.name, pattern) for pattern in patterns):
                        try:
                            size = target_path.stat().st_size
                            target_path.unlink()
                            cleared_size += size
                            cleared_count += 1
                        except (PermissionError, OSError):
                            pass
                    continue

                for pattern in patterns:
                    for item in target_path.rglob(pattern):
                        try:
                            if item.is_file():
                                size = item.stat().st_size
                                item.unlink()
                                cleared_size += size
                                cleared_count += 1
                            elif item.is_dir():
                                size = self._estimate_path_size(item)
                                shutil.rmtree(item, ignore_errors=True)
                                cleared_size += size
                                cleared_count += 1
                        except (PermissionError, OSError):
                            continue
            except Exception as exc:
                errors.append(f'{location.get("name", "未知类别")} 清理失败: {str(exc)}')
        return cleared_size, cleared_count, errors

    def _clean_locations(self, locations: List[Dict], categories=None):
        selected = self._normalize_categories(categories)
        if not selected:
            return api_error('请选择要清理的类别')
        location_map = {item.get('category'): item for item in locations}
        cleared_size = 0
        cleared_count = 0
        errors = []

        for category in selected:
            location = location_map.get(category)
            if not location:
                continue
            size, count, location_errors = self._clean_location(location)
            cleared_size += size
            cleared_count += count
            errors.extend(location_errors)

        return api_success(
            clearedSize=cleared_size,
            clearedSizeText=format_bytes(cleared_size),
            clearedCount=cleared_count,
            errors=errors if errors else None
        )

    def system_scanJunk(self, options=None):
        '''扫描系统垃圾文件'''
        categories = options.get('categories') if isinstance(options, dict) else None
        return self._scan_locations(self._get_junk_locations(), categories=categories, include_empty=False)

    def system_cleanJunk(self, options=None):
        '''清理系统垃圾文件'''
        categories = options.get('categories') if isinstance(options, dict) else None
        return self._clean_locations(self._get_junk_locations(), categories=categories)

    def system_scanCDriveClean(self, options=None):
        '''扫描 C 盘专清项目'''
        if platform.system() != 'Windows':
            return api_error('C 盘专清仅支持 Windows 系统')
        categories = options.get('categories') if isinstance(options, dict) else None
        locations = self._get_c_drive_clean_locations()

        state = self._load_c_drive_clean_state()
        custom_rules = state.get('customRules', [])
        for index, rule in enumerate(custom_rules):
            if not isinstance(rule, dict):
                continue
            path = rule.get('path')
            if not path:
                continue
            loc = {
                'category': f"custom_{rule.get('id') or index}",
                'name': rule.get('name') or f'自定义规则 {index + 1}',
                'description': rule.get('description') or '用户自定义扫描规则',
                'patterns': rule.get('patterns') or ['*'],
                'risk': 'medium',
                'paths': [path],
                'minSizeBytes': int(rule.get('minSizeBytes') or 0),
                'olderThanDays': int(rule.get('olderThanDays') or 0),
                'extFilters': rule.get('extFilters') if isinstance(rule.get('extFilters'), list) else []
            }
            loc['path'] = self._location_display_path(loc)
            locations.append(loc)

        result = self._scan_locations(locations, categories=categories, include_empty=True)
        result['catalogCount'] = len(locations)
        result['whitelistCount'] = len(state.get('whitelist', []))
        return result

    def system_cleanCDriveClean(self, options=None):
        '''清理 C 盘专清项目'''
        if platform.system() != 'Windows':
            return api_error('C 盘专清仅支持 Windows 系统')
        categories = options.get('categories') if isinstance(options, dict) else None
        mode = (options.get('mode') if isinstance(options, dict) else 'permanent') or 'permanent'
        file_paths = options.get('filePaths') if isinstance(options, dict) else None

        if isinstance(file_paths, list) and file_paths:
            return self.system_cleanCDriveFiles({'filePaths': file_paths, 'mode': mode})

        return self._clean_locations(self._get_c_drive_clean_locations(), categories=categories)

    def system_cleanCDriveFiles(self, payload=None):
        '''按文件粒度清理 C 盘专清文件'''
        if platform.system() != 'Windows':
            return api_error('C 盘专清仅支持 Windows 系统')

        file_paths = payload.get('filePaths') if isinstance(payload, dict) else None
        mode = (payload.get('mode') if isinstance(payload, dict) else 'permanent') or 'permanent'
        if not isinstance(file_paths, list) or not file_paths:
            return api_error('请提供要清理的文件列表')

        use_recycle = mode == 'recycle'
        if use_recycle and send2trash is None:
            return api_error('当前环境未安装 send2trash，无法移动到回收站')

        cleared_size = 0
        cleared_count = 0
        errors = []

        seen = set()
        for raw_path in file_paths:
            path_str = str(raw_path or '').strip()
            if not path_str:
                continue
            key = path_str.lower()
            if key in seen:
                continue
            seen.add(key)

            target = Path(path_str)
            if not target.exists():
                continue

            try:
                size = target.stat().st_size if target.is_file() else self._estimate_path_size(target)
                if use_recycle:
                    send2trash(str(target))
                else:
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                cleared_size += max(0, int(size or 0))
                cleared_count += 1
            except Exception as exc:
                errors.append(f'{path_str}: {str(exc)}')

        return api_success(
            clearedSize=cleared_size,
            clearedSizeText=format_bytes(cleared_size),
            clearedCount=cleared_count,
            mode=mode,
            errors=errors if errors else None
        )

    def system_addCDriveWhitelist(self, payload=None):
        '''将文件路径加入 C 盘专清白名单'''
        paths = payload.get('paths') if isinstance(payload, dict) else None
        if not isinstance(paths, list) or not paths:
            return api_error('请提供路径列表')

        state = self._load_c_drive_clean_state()
        current = {str(item).lower(): str(item) for item in state.get('whitelist', []) if item}
        for raw in paths:
            path_str = str(raw or '').strip()
            if not path_str:
                continue
            current[path_str.lower()] = path_str
        state['whitelist'] = sorted(current.values(), key=lambda x: x.lower())
        self._save_c_drive_clean_state(state)
        return api_success(whitelist=state['whitelist'], count=len(state['whitelist']))

    def system_removeCDriveWhitelist(self, payload=None):
        '''从 C 盘专清白名单移除路径'''
        paths = payload.get('paths') if isinstance(payload, dict) else None
        if not isinstance(paths, list) or not paths:
            return api_error('请提供路径列表')

        remove_set = {str(item).strip().lower() for item in paths if str(item).strip()}
        state = self._load_c_drive_clean_state()
        state['whitelist'] = [
            item for item in state.get('whitelist', [])
            if str(item).lower() not in remove_set
        ]
        self._save_c_drive_clean_state(state)
        return api_success(whitelist=state['whitelist'], count=len(state['whitelist']))

    def system_getCDriveWhitelist(self):
        state = self._load_c_drive_clean_state()
        return api_success(
            whitelist=state.get('whitelist', []),
            count=len(state.get('whitelist', []))
        )

    def system_saveCDriveCustomRule(self, payload=None):
        '''保存 C 盘专清自定义规则'''
        if not isinstance(payload, dict):
            return api_error('参数格式错误')

        path = str(payload.get('path') or '').strip()
        if not path:
            return api_error('请填写扫描路径')

        name = str(payload.get('name') or '').strip() or '自定义规则'
        patterns = payload.get('patterns') if isinstance(payload.get('patterns'), list) else ['*']
        ext_filters = payload.get('extFilters') if isinstance(payload.get('extFilters'), list) else []
        min_size_bytes = int(payload.get('minSizeBytes') or 0)
        older_than_days = int(payload.get('olderThanDays') or 0)

        state = self._load_c_drive_clean_state()
        rules = state.get('customRules', [])
        rule_id = str(payload.get('id') or '').strip()

        normalized = {
            'id': rule_id or uuid.uuid4().hex,
            'name': name,
            'path': path,
            'patterns': [str(item) for item in patterns if str(item).strip()] or ['*'],
            'extFilters': [str(item).lower() for item in ext_filters if str(item).strip()],
            'minSizeBytes': max(0, min_size_bytes),
            'olderThanDays': max(0, older_than_days),
            'description': str(payload.get('description') or '').strip()
        }

        updated = False
        for index, rule in enumerate(rules):
            if str(rule.get('id')) == normalized['id']:
                rules[index] = normalized
                updated = True
                break
        if not updated:
            rules.append(normalized)

        state['customRules'] = rules
        self._save_c_drive_clean_state(state)
        return api_success(rules=rules, rule=normalized)

    def system_removeCDriveCustomRule(self, payload=None):
        rule_id = payload.get('id') if isinstance(payload, dict) else None
        if not rule_id:
            return api_error('请提供规则 ID')
        state = self._load_c_drive_clean_state()
        rules = state.get('customRules', [])
        new_rules = [rule for rule in rules if str(rule.get('id')) != str(rule_id)]
        state['customRules'] = new_rules
        self._save_c_drive_clean_state(state)
        return api_success(rules=new_rules)

    def system_listCDriveCustomRules(self):
        state = self._load_c_drive_clean_state()
        rules = state.get('customRules', [])
        return api_success(rules=rules, count=len(rules))

    # ==================== 注册表清理 ====================

    def _scan_invalid_uninstall_entries(self) -> List[Dict]:
        '''扫描无效的软件卸载信息'''
        items = []
        if platform.system() != 'Windows':
            return items

        uninstall_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
        ]

        for hkey, subkey in uninstall_paths:
            try:
                with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name = winreg.EnumKey(key, i)
                            i += 1
                            try:
                                with winreg.OpenKey(key, name, 0, winreg.KEY_READ) as app_key:
                                    try:
                                        install_location, _ = winreg.QueryValueEx(app_key, 'InstallLocation')
                                        if install_location and not Path(install_location).exists():
                                            display_name = ''
                                            try:
                                                display_name, _ = winreg.QueryValueEx(app_key, 'DisplayName')
                                            except (OSError, FileNotFoundError):
                                                display_name = name
                                            items.append({
                                                'path': f'{subkey}\\{name}',
                                                'name': display_name or name,
                                                'reason': f'安装目录不存在: {install_location}',
                                                'type': 'uninstall',
                                                'hkey': 'HKLM' if hkey == winreg.HKEY_LOCAL_MACHINE else 'HKCU'
                                            })
                                    except (OSError, FileNotFoundError):
                                        pass
                            except (OSError, PermissionError):
                                pass
                        except OSError:
                            break
            except (OSError, PermissionError):
                continue

        return items

    def _scan_invalid_file_extensions(self) -> List[Dict]:
        '''扫描无效的文件类型关联'''
        items = []
        if platform.system() != 'Windows':
            return items

        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, '', 0, winreg.KEY_READ) as root:
                i = 0
                checked = 0
                max_check = 500  # 限制检查数量
                while checked < max_check:
                    try:
                        name = winreg.EnumKey(root, i)
                        i += 1
                        if not name.startswith('.'):
                            continue
                        checked += 1
                        try:
                            with winreg.OpenKey(root, name, 0, winreg.KEY_READ) as ext_key:
                                try:
                                    prog_id, _ = winreg.QueryValueEx(ext_key, '')
                                    if prog_id:
                                        # 检查 ProgID 是否存在
                                        try:
                                            winreg.OpenKey(root, prog_id, 0, winreg.KEY_READ).Close()
                                        except OSError:
                                            items.append({
                                                'path': f'HKCR\\{name}',
                                                'name': name,
                                                'reason': f'关联的程序标识不存在: {prog_id}',
                                                'type': 'file_ext',
                                                'hkey': 'HKCR'
                                            })
                                except (OSError, FileNotFoundError):
                                    pass
                        except (OSError, PermissionError):
                            pass
                    except OSError:
                        break
        except (OSError, PermissionError):
            pass

        return items[:50]  # 最多返回 50 个

    def system_scanRegistry(self):
        '''扫描无效注册表项'''
        if platform.system() != 'Windows':
            return api_error('注册表清理仅支持 Windows 系统')

        items = []

        # 扫描无效卸载信息
        items.extend(self._scan_invalid_uninstall_entries())

        # 扫描无效文件关联
        items.extend(self._scan_invalid_file_extensions())

        return api_success(items=items, count=len(items))

    def system_cleanRegistry(self, payload=None):
        '''清理选中的注册表项'''
        if platform.system() != 'Windows':
            return api_error('注册表清理仅支持 Windows 系统')

        items = []
        if isinstance(payload, dict):
            items = payload.get('items', [])

        if not items:
            return api_error('请选择要清理的注册表项')

        cleared_count = 0
        errors = []

        for item in items:
            try:
                path = item.get('path', '')
                hkey_str = item.get('hkey', '')
                item_type = item.get('type', '')

                # 确定根键
                if hkey_str == 'HKLM':
                    hkey = winreg.HKEY_LOCAL_MACHINE
                elif hkey_str == 'HKCU':
                    hkey = winreg.HKEY_CURRENT_USER
                elif hkey_str == 'HKCR':
                    hkey = winreg.HKEY_CLASSES_ROOT
                else:
                    continue

                # 获取父路径和键名
                if '\\' in path:
                    parent_path, key_name = path.rsplit('\\', 1)
                    # 移除开头的根键标识符
                    if parent_path.startswith('SOFTWARE'):
                        pass
                    elif '\\' in parent_path:
                        parent_path = parent_path.split('\\', 1)[-1]
                else:
                    continue

                # 删除键
                try:
                    winreg.DeleteKey(hkey, path)
                    cleared_count += 1
                except PermissionError:
                    errors.append(f'权限不足: {path}')
                except FileNotFoundError:
                    cleared_count += 1  # 已经不存在，算成功
                except OSError as e:
                    errors.append(f'{path}: {str(e)}')
            except Exception as e:
                errors.append(str(e))

        return api_success(
            clearedCount=cleared_count,
            errors=errors if errors else None
        )
