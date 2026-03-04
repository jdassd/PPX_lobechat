#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import getpass
import fnmatch
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import webview
from webview.window import FixPoint

if platform.system() == 'Windows':
    import winreg

try:
    import psutil
except ImportError:
    psutil = None

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None


from api.utils import format_bytes
from pyapp.config.config import Config
from pyapp.update.update import AppUpdate


class System():
    '''系统类'''

    _window = None

    @staticmethod
    def _psutil_missing_response():
        return {
            'success': False,
            'message': 'psutil 模块未安装，请先运行 pnpm run init 安装依赖后重试'
        }

    @staticmethod
    def _format_create_time(timestamp):
        if not timestamp:
            return ''
        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError, OSError):
            return ''

    @staticmethod
    def _collect_process_ports(proc, max_ports=16):
        ports = set()
        if psutil is None:
            return []
        try:
            for conn in proc.connections(kind='inet'):
                laddr = getattr(conn, 'laddr', None)
                raddr = getattr(conn, 'raddr', None)
                if laddr and getattr(laddr, 'port', None):
                    ports.add(laddr.port)
                elif isinstance(laddr, tuple) and len(laddr) > 1:
                    ports.add(laddr[1])
                if raddr and getattr(raddr, 'port', None):
                    ports.add(raddr.port)
                elif isinstance(raddr, tuple) and len(raddr) > 1:
                    ports.add(raddr[1])
                if len(ports) >= max_ports:
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
        return sorted(ports)

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

    def system_py2js(self, func, info):
        '''调用js中挂载到window的函数'''
        infoJson = json.dumps(info)
        System._window.evaluate_js(f"{func}({infoJson})")

    def system_getAppInfo(self):
        '''程序基础配置信息'''
        return {
            'appName': Config.appName,  # 应用名称
            'appVersion': Config.appVersion  # 应用版本号
        }

    def system_checkNewVersion(self):
        '''检查更新'''
        appUpdate = AppUpdate()    # 程序更新类
        res = appUpdate.check()
        return res

    def system_downloadNewVersion(self):
        '''下载新版本'''
        appUpdate = AppUpdate()    # 程序更新类
        res = appUpdate.run()
        return res

    def system_cancelDownloadNewVersion(self):
        '''取消下载新版本'''
        appUpdate = AppUpdate()    # 程序更新类
        appUpdate.cancel()

    def system_getOwner(self):
        # 获取本机用户名
        return getpass.getuser()

    def system_pyOpenFile(self, path):
        '''用电脑默认软件打开本地文件或URL'''
        # 判断是否为URL
        if path.startswith('http://') or path.startswith('https://'):
            # 打开URL
            import webbrowser
            webbrowser.open(path)
        else:
            # 使用 pathlib 进行跨平台路径处理
            file_path = Path(path).resolve()
            if Config.appIsMacOS:
                subprocess.call(["open", str(file_path)])
            else:
                os.startfile(str(file_path))

    def system_pyCreateFileDialog(self, fileTypes=None, directory=''):
        '''打开文件对话框'''
        # 可选文件类型
        # fileTypes = ['Excel表格 (*.xlsx;*.xls)']
        if fileTypes is None:
            fileTypes = ['全部文件 (*.*)']
        fileTypes = tuple(fileTypes)    # 要求必须是元组
        result = System._window.create_file_dialog(dialog_type=webview.OPEN_DIALOG, directory=directory, allow_multiple=True, file_types=fileTypes)
        resList = list()
        if result is not None:
            for res in result:
                filePathList = os.path.split(res)
                dir = filePathList[0]
                filename = filePathList[1]
                ext = os.path.splitext(res)[-1]
                resList.append({
                    'filename': filename,
                    'ext': ext,
                    'dir': dir,
                    'path': res
                })
        return resList

    def system_pySelectDirDialog(self, directory=''):
        '''选择文件夹对话框'''
        result = System._window.create_file_dialog(dialog_type=webview.FOLDER_DIALOG, directory=directory)
        if result is not None and len(result) > 0:
            if isinstance(result, tuple) or isinstance(result, list):
                return result[0]
            else:
                return result
        else:
            return ''

    def system_listProcesses(self, filters=None):
        '''获取进程列表，可按名称和端口过滤

        说明：为提升查询速度，默认仅在指定端口过滤时才收集端口信息，
        普通名称搜索不会遍历每个进程的网络连接。
        '''
        if psutil is None:
            return self._psutil_missing_response()

        keyword = ''
        port = None
        limit = 200
        sort_by = 'memory'
        sort_order = 'desc'

        if isinstance(filters, dict):
            keyword = str(filters.get('keyword', '') or '').strip().lower()
            raw_port = filters.get('port', None)
            try:
                port = int(str(raw_port).strip()) if str(raw_port).strip() else None
            except (TypeError, ValueError):
                port = None
            try:
                requested_limit = int(filters.get('limit', limit))
                if requested_limit > 0:
                    limit = min(requested_limit, 500)
            except (TypeError, ValueError):
                pass
            sort_by = str(filters.get('sortBy', sort_by)).lower()
            sort_order = str(filters.get('sortOrder', sort_order)).lower()
        elif filters:
            # 向后兼容字符串参数：按关键字过滤
            keyword = str(filters).strip().lower()

        matched = []
        attrs = ['pid', 'name', 'username', 'status', 'cmdline', 'create_time', 'memory_percent']
        try:
            processes = psutil.process_iter(attrs=attrs)
        except Exception:
            processes = psutil.process_iter()

        for proc in processes:
            try:
                with proc.oneshot():
                    info = proc.as_dict(attrs=attrs, ad_value='')
                    name = info.get('name') or ''
                    cmdline_list = info.get('cmdline') or []
                    cmdline = ' '.join(cmdline_list) if isinstance(cmdline_list, list) else str(cmdline_list)
                    if keyword:
                        merged = f"{name} {cmdline}".lower()
                        if keyword not in merged:
                            continue
                    # 仅在需要按端口过滤时才收集端口信息，避免遍历大量连接影响性能
                    ports = []
                    if port is not None:
                        ports = self._collect_process_ports(proc)
                        if port not in ports:
                            continue
                    cpu_percent = proc.cpu_percent(interval=None)
                    try:
                        mem_info = proc.memory_info()
                        memory_bytes = getattr(mem_info, 'rss', 0)
                    except (psutil.AccessDenied, psutil.ZombieProcess):
                        memory_bytes = 0
                    memory_percent = round(float(info.get('memory_percent') or 0), 2)
                    matched.append({
                        'pid': info.get('pid'),
                        'name': name,
                        'status': info.get('status') or '',
                        'username': info.get('username') or '',
                        'createTime': info.get('create_time') or 0,
                        'createLabel': self._format_create_time(info.get('create_time')),
                        'memoryPercent': memory_percent,
                        'memoryBytes': memory_bytes,
                        'memoryText': format_bytes(memory_bytes),
                        'cpuPercent': round(cpu_percent or 0.0, 2),
                        'threads': proc.num_threads(),
                        'cmdline': cmdline.strip(),
                        'ports': ports
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        reverse = sort_order != 'asc'
        if sort_by == 'cpu':
            matched.sort(key=lambda item: item.get('cpuPercent', 0.0), reverse=reverse)
        elif sort_by in {'start', 'create', 'time'}:
            matched.sort(key=lambda item: item.get('createTime', 0), reverse=reverse)
        elif sort_by == 'name':
            matched.sort(key=lambda item: item.get('name', '').lower(), reverse=reverse)
        else:
            matched.sort(key=lambda item: item.get('memoryPercent', 0.0), reverse=reverse)
        total = len(matched)
        limited = matched[:limit]
        return {
            'success': True,
            'items': limited,
            'total': total,
            'limit': limit,
            'hasMore': total > len(limited),
            'keyword': keyword,
            'port': port,
            'sortBy': sort_by,
            'sortOrder': sort_order
        }

    def system_processMetrics(self, payload=None):
        '''获取指定 PID 的实时性能指标'''
        if psutil is None:
            return self._psutil_missing_response()
        pids = []
        if isinstance(payload, dict):
            raw = payload.get('pids') or payload.get('pid')
        else:
            raw = payload
        if isinstance(raw, (list, tuple, set)):
            pids = list(raw)
        elif raw:
            pids = [raw]
        metrics = []
        timestamp = datetime.now(timezone.utc).isoformat()
        for pid in pids:
            try:
                proc = psutil.Process(int(pid))
                with proc.oneshot():
                    cpu_percent = proc.cpu_percent(interval=None)
                    mem_info = proc.memory_info()
                    metrics.append({
                        'pid': proc.pid,
                        'name': proc.name(),
                        'cpuPercent': round(cpu_percent or 0.0, 2),
                        'memoryBytes': getattr(mem_info, 'rss', 0),
                        'memoryText': format_bytes(getattr(mem_info, 'rss', 0)),
                        'threads': proc.num_threads(),
                        'timestamp': timestamp
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                metrics.append({
                    'pid': pid,
                    'error': 'process_not_available',
                    'timestamp': timestamp
                })
        return {
            'success': True,
            'metrics': metrics,
            'timestamp': timestamp
        }

    def system_killProcess(self, pid):
        '''强制结束指定进程'''
        if psutil is None:
            return self._psutil_missing_response()

        try:
            target_pid = int(pid)
        except (TypeError, ValueError):
            return {
                'success': False,
                'message': '请输入正确的 PID'
            }

        if target_pid <= 0:
            return {
                'success': False,
                'message': 'PID 需要为正整数'
            }

        try:
            proc = psutil.Process(target_pid)
            name = proc.name()
            proc.kill()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                pass
            return {
                'success': True,
                'pid': target_pid,
                'name': name
            }
        except psutil.NoSuchProcess:
            return {
                'success': True,
                'pid': target_pid,
                'message': '进程已不存在'
            }
        except psutil.AccessDenied:
            return {
                'success': False,
                'pid': target_pid,
                'message': '权限不足，建议以管理员方式运行 PPX 后重试'
            }
        except Exception as err:
            return {
                'success': False,
                'pid': target_pid,
                'message': f'结束进程失败：{err}'
            }

    def system_killProcesses(self, payload=None):
        '''批量结束进程'''
        if psutil is None:
            return self._psutil_missing_response()
        if isinstance(payload, dict):
            raw = payload.get('pids') or payload.get('pid')
        else:
            raw = payload
        if isinstance(raw, (list, tuple, set)):
            pids = raw
        elif raw:
            pids = [raw]
        else:
            return {'success': False, 'message': '请提供 PID 列表'}
        results = []
        overall_success = True
        for pid in pids:
            result = self.system_killProcess(pid)
            results.append(result)
            if not result.get('success'):
                overall_success = False
        return {
            'success': overall_success,
            'results': results
        }

    def system_listStartupRules(self):
        '''列出自动启动规则（包括系统启动项）'''
        try:
            # 自定义规则
            custom_rules = self._load_startup_rules()
            # 系统启动项
            system_rules = self._load_system_startup_items()
            # 合并：系统项在前，自定义在后
            all_rules = system_rules + custom_rules
            return {
                'success': True,
                'rules': all_rules
            }
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

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

    def _query_nvidia_gpus(self):
        if not shutil.which('nvidia-smi'):
            return []
        query_fields = [
            'name',
            'temperature.gpu',
            'utilization.gpu',
            'utilization.memory',
            'memory.total',
            'memory.used',
            'fan.speed',
            'power.draw'
        ]
        command = [
            'nvidia-smi',
            f'--query-gpu={",".join(query_fields)}',
            '--format=csv,noheader,nounits'
        ]
        try:
            output = subprocess.check_output(command, text=True, encoding='utf-8', errors='ignore')
        except Exception:
            return []
        gpus = []
        for line in output.splitlines():
            if not line.strip():
                continue
            parts = [item.strip() for item in line.split(',')]
            if len(parts) < len(query_fields):
                continue
            name = parts[0]
            temperature = self._safe_float(parts[1])
            utilization = self._safe_float(parts[2])
            memory_util = self._safe_float(parts[3])
            memory_total = self._safe_float(parts[4])
            memory_used = self._safe_float(parts[5])
            fan_speed = self._safe_float(parts[6])
            power_draw = self._safe_float(parts[7])
            memory_percent = None
            if memory_total:
                memory_percent = round((memory_used or 0) / memory_total * 100, 2)
            gpus.append({
                'name': name,
                'temperature': temperature,
                'temperatureLabel': f'{temperature:.1f}°C' if temperature is not None else '',
                'utilization': round(utilization or 0, 2) if utilization is not None else 0,
                'memoryUtilization': round(memory_util or 0, 2) if memory_util is not None else 0,
                'memoryTotal': memory_total or 0,
                'memoryUsed': memory_used or 0,
                'memoryPercent': memory_percent or 0,
                'memoryTotalText': format_bytes((memory_total or 0) * 1024 * 1024),
                'memoryUsedText': format_bytes((memory_used or 0) * 1024 * 1024),
                'fanSpeed': fan_speed,
                'fanSpeedLabel': f'{fan_speed:.0f}%' if fan_speed is not None else '',
                'powerDraw': power_draw
            })
        return gpus

    def system_getSystemStatus(self):
        '''获取系统概览与传感器信息'''
        if psutil is None:
            return self._psutil_missing_response()

        cpu_percent = psutil.cpu_percent(interval=0.2)
        cpu_count = psutil.cpu_count(logical=True) or 0
        cpu_freq = psutil.cpu_freq()
        cpu_freq_label = f'{cpu_freq.current:.0f} MHz' if cpu_freq else ''

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disks = []
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            partitions = []
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except Exception:
                continue
            label = part.device or part.mountpoint
            disks.append({
                'device': part.device,
                'mount': part.mountpoint,
                'fstype': part.fstype,
                'label': label,
                'total': usage.total,
                'used': usage.used,
                'percent': round(usage.percent or 0, 2),
                'totalText': format_bytes(usage.total),
                'usedText': format_bytes(usage.used)
            })

        temperatures = []
        fans = []
        voltages = []
        try:
            temps_raw = psutil.sensors_temperatures(fahrenheit=False) or {}
            for name, entries in temps_raw.items():
                for entry in entries:
                    temperatures.append({
                        'name': name,
                        'label': entry.label or name,
                        'value': entry.current,
                        'high': entry.high,
                        'critical': entry.critical
                    })
        except Exception:
            pass

        try:
            fans_raw = psutil.sensors_fans() or {}
            for name, entries in fans_raw.items():
                for entry in entries:
                    fans.append({
                        'name': name,
                        'label': entry.label or name,
                        'value': entry.current
                    })
        except Exception:
            pass

        gpus = self._query_nvidia_gpus()

        cpu_temp_label = ''
        for temp in temperatures:
            label = f"{temp.get('name', '')} {temp.get('label', '')}".lower()
            if 'cpu' in label or 'core' in label or 'package' in label:
                if temp.get('value') is not None:
                    cpu_temp_label = f"{temp.get('value')}°C"
                break

        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time if boot_time else 0
        uptime = {
            'seconds': round(uptime_seconds, 2),
            'text': self._format_duration(uptime_seconds)
        }

        load_label = ''
        load_data = {}
        try:
            load_avg = psutil.getloadavg()
            load_data = {
                'avg1': round(load_avg[0], 2),
                'avg5': round(load_avg[1], 2),
                'avg15': round(load_avg[2], 2)
            }
            load_label = f"{load_data['avg1']}/{load_data['avg5']}/{load_data['avg15']}"
        except Exception:
            load_label = f'CPU {cpu_percent:.1f}%'
        load_data['label'] = load_label

        now_label = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return {
            'success': True,
            'updatedAt': now_label,
            'uptime': uptime,
            'load': load_data,
            'cpu': {
                'percent': round(cpu_percent or 0, 2),
                'cores': cpu_count,
                'freq': cpu_freq_label,
                'tempLabel': cpu_temp_label
            },
            'memory': {
                'percent': round(memory.percent or 0, 2),
                'total': memory.total,
                'used': memory.used,
                'totalText': format_bytes(memory.total),
                'usedText': format_bytes(memory.used),
                'text': f"{format_bytes(memory.used)} / {format_bytes(memory.total)}"
            },
            'swap': {
                'percent': round(swap.percent or 0, 2),
                'total': swap.total,
                'used': swap.used,
                'text': f"{format_bytes(swap.used)} / {format_bytes(swap.total)}"
            },
            'disks': disks,
            'gpus': gpus,
            'sensors': {
                'temperatures': temperatures,
                'fans': fans,
                'voltages': voltages
            }
        }

    def system_saveStartupRule(self, rule):
        '''新增或更新自动启动规则'''
        try:
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
            return {'success': True, 'id': rule_id, 'rules': rules}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

    def system_removeStartupRule(self, payload=None):
        '''删除自动启动规则'''
        try:
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
            return {'success': True, 'rules': new_rules}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

    def system_runStartupRule(self, payload=None):
        '''运行自动启动规则'''
        try:
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
            return {'success': True, 'pid': process.pid, 'rule': target}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

    def system_toggleProcessNetwork(self, payload=None):
        '''禁用或恢复进程网络访问（仅 Windows）'''
        if psutil is None:
            return self._psutil_missing_response()
        block = True
        pid = None
        if isinstance(payload, dict):
            pid = payload.get('pid')
            block = bool(payload.get('block', True))
        else:
            pid = payload
        if not pid:
            return {'success': False, 'message': '请提供 PID'}
        if Config.appSystem != 'Windows':
            return {'success': False, 'message': '当前仅支持 Windows 平台'}
        if not shutil.which('netsh'):
            return {'success': False, 'message': '未检测到 netsh，无法修改防火墙规则'}
        try:
            proc = psutil.Process(int(pid))
            exe_path = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {'success': False, 'message': '无法访问指定进程'}
        if not exe_path:
            return {'success': False, 'message': '无法获取进程可执行文件路径'}
        rule_hash = hashlib.md5(exe_path.encode('utf-8', errors='ignore')).hexdigest()[:8]
        directions = ('out', 'in')

        def run_command(command):
            result = subprocess.run(command, capture_output=True, text=True, shell=False)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or 'netsh 执行失败，需管理员权限')

        try:
            sanitized = exe_path.replace('"', '')
            for direction in directions:
                rule_name = f'PPX_{rule_hash}_{direction.upper()}'
                if block:
                    cleanup = [
                        'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                        f'name="{rule_name}"', f'program="{sanitized}"'
                    ]
                    subprocess.run(cleanup, capture_output=True, text=True, shell=False)
                    cmd = [
                        'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                        f'name="{rule_name}"', f'dir={direction}', 'action=block',
                        f'program="{sanitized}"', 'enable=yes'
                    ]
                else:
                    cmd = [
                        'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                        f'name="{rule_name}"', f'program="{sanitized}"'
                    ]
                run_command(cmd)
            return {
                'success': True,
                'pid': proc.pid,
                'program': exe_path,
                'blocked': block
            }
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

    def system_runSystemStartup(self, payload=None):
        '''运行系统启动项'''
        try:
            command = None
            file_path = None
            if isinstance(payload, dict):
                command = payload.get('command')
                file_path = payload.get('filePath')
            if not command and not file_path:
                return {'success': False, 'message': '请提供启动命令'}

            # 如果是启动文件夹中的文件，使用 os.startfile 打开
            if file_path and Path(file_path).exists():
                if Config.appIsMacOS:
                    subprocess.Popen(['open', file_path])
                else:
                    os.startfile(file_path)
                return {'success': True}

            # 否则执行命令
            creationflags = 0
            if platform.system() == 'Windows' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creationflags = subprocess.CREATE_NO_WINDOW
            subprocess.Popen(command, shell=True, creationflags=creationflags)
            return {'success': True}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

    def system_openStartupLocation(self, payload=None):
        '''打开启动项所在位置'''
        try:
            source = None
            reg_key = None
            file_path = None
            if isinstance(payload, dict):
                source = payload.get('source')
                reg_key = payload.get('regKey')
                file_path = payload.get('filePath')

            if platform.system() != 'Windows':
                return {'success': False, 'message': '仅支持 Windows 平台'}

            # 如果是启动文件夹中的项目，打开文件夹并选中文件
            if source == 'StartupFolder' and file_path:
                file_obj = Path(file_path)
                if file_obj.exists():
                    subprocess.Popen(['explorer', '/select,', str(file_obj)])
                    return {'success': True}
                else:
                    return {'success': False, 'message': '文件不存在'}

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
                return {'success': True}

            return {'success': False, 'message': '无法确定启动项位置'}
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

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

            result = subprocess.run(
                ['powershell', '-Command', command],
                capture_output=True,
                text=True,
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

        return {
            'success': True,
            'items': items,
            'totalSize': total_size,
            'totalSizeText': format_bytes(total_size),
            'categoryCount': len(items)
        }

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

    def _clear_recycle_bin(self, drive_letter=None):
        if platform.system() != 'Windows':
            return False
        command = 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'
        if drive_letter:
            command = f'Clear-RecycleBin -DriveLetter {drive_letter} -Force -ErrorAction SilentlyContinue'
        try:
            result = subprocess.run(
                ['powershell', '-Command', command],
                capture_output=True,
                text=True,
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
            return {'success': False, 'message': '请选择要清理的类别'}

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

        return {
            'success': True,
            'clearedSize': cleared_size,
            'clearedSizeText': format_bytes(cleared_size),
            'clearedCount': cleared_count,
            'errors': errors if errors else None
        }

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
            return {
                'success': False,
                'message': 'C 盘专清仅支持 Windows 系统'
            }
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
            return {
                'success': False,
                'message': 'C 盘专清仅支持 Windows 系统'
            }
        categories = options.get('categories') if isinstance(options, dict) else None
        mode = (options.get('mode') if isinstance(options, dict) else 'permanent') or 'permanent'
        file_paths = options.get('filePaths') if isinstance(options, dict) else None

        if isinstance(file_paths, list) and file_paths:
            return self.system_cleanCDriveFiles({'filePaths': file_paths, 'mode': mode})

        return self._clean_locations(self._get_c_drive_clean_locations(), categories=categories)

    def system_cleanCDriveFiles(self, payload=None):
        '''按文件粒度清理 C 盘专清文件'''
        if platform.system() != 'Windows':
            return {
                'success': False,
                'message': 'C 盘专清仅支持 Windows 系统'
            }

        file_paths = payload.get('filePaths') if isinstance(payload, dict) else None
        mode = (payload.get('mode') if isinstance(payload, dict) else 'permanent') or 'permanent'
        if not isinstance(file_paths, list) or not file_paths:
            return {'success': False, 'message': '请提供要清理的文件列表'}

        use_recycle = mode == 'recycle'
        if use_recycle and send2trash is None:
            return {'success': False, 'message': '当前环境未安装 send2trash，无法移动到回收站'}

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

        return {
            'success': True,
            'clearedSize': cleared_size,
            'clearedSizeText': format_bytes(cleared_size),
            'clearedCount': cleared_count,
            'mode': mode,
            'errors': errors if errors else None
        }

    def system_addCDriveWhitelist(self, payload=None):
        '''将文件路径加入 C 盘专清白名单'''
        paths = payload.get('paths') if isinstance(payload, dict) else None
        if not isinstance(paths, list) or not paths:
            return {'success': False, 'message': '请提供路径列表'}

        state = self._load_c_drive_clean_state()
        current = {str(item).lower(): str(item) for item in state.get('whitelist', []) if item}
        for raw in paths:
            path_str = str(raw or '').strip()
            if not path_str:
                continue
            current[path_str.lower()] = path_str
        state['whitelist'] = sorted(current.values(), key=lambda x: x.lower())
        self._save_c_drive_clean_state(state)
        return {'success': True, 'whitelist': state['whitelist'], 'count': len(state['whitelist'])}

    def system_removeCDriveWhitelist(self, payload=None):
        '''从 C 盘专清白名单移除路径'''
        paths = payload.get('paths') if isinstance(payload, dict) else None
        if not isinstance(paths, list) or not paths:
            return {'success': False, 'message': '请提供路径列表'}

        remove_set = {str(item).strip().lower() for item in paths if str(item).strip()}
        state = self._load_c_drive_clean_state()
        state['whitelist'] = [
            item for item in state.get('whitelist', [])
            if str(item).lower() not in remove_set
        ]
        self._save_c_drive_clean_state(state)
        return {'success': True, 'whitelist': state['whitelist'], 'count': len(state['whitelist'])}

    def system_getCDriveWhitelist(self):
        state = self._load_c_drive_clean_state()
        return {
            'success': True,
            'whitelist': state.get('whitelist', []),
            'count': len(state.get('whitelist', []))
        }

    def system_saveCDriveCustomRule(self, payload=None):
        '''保存 C 盘专清自定义规则'''
        if not isinstance(payload, dict):
            return {'success': False, 'message': '参数格式错误'}

        path = str(payload.get('path') or '').strip()
        if not path:
            return {'success': False, 'message': '请填写扫描路径'}

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
        return {'success': True, 'rules': rules, 'rule': normalized}

    def system_removeCDriveCustomRule(self, payload=None):
        rule_id = payload.get('id') if isinstance(payload, dict) else None
        if not rule_id:
            return {'success': False, 'message': '请提供规则 ID'}
        state = self._load_c_drive_clean_state()
        rules = state.get('customRules', [])
        new_rules = [rule for rule in rules if str(rule.get('id')) != str(rule_id)]
        state['customRules'] = new_rules
        self._save_c_drive_clean_state(state)
        return {'success': True, 'rules': new_rules}

    def system_listCDriveCustomRules(self):
        state = self._load_c_drive_clean_state()
        rules = state.get('customRules', [])
        return {'success': True, 'rules': rules, 'count': len(rules)}

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
            return {
                'success': False,
                'message': '注册表清理仅支持 Windows 系统'
            }
        
        items = []
        
        # 扫描无效卸载信息
        items.extend(self._scan_invalid_uninstall_entries())
        
        # 扫描无效文件关联
        items.extend(self._scan_invalid_file_extensions())
        
        return {
            'success': True,
            'items': items,
            'count': len(items)
        }

    def system_cleanRegistry(self, payload=None):
        '''清理选中的注册表项'''
        if platform.system() != 'Windows':
            return {
                'success': False,
                'message': '注册表清理仅支持 Windows 系统'
            }
        
        items = []
        if isinstance(payload, dict):
            items = payload.get('items', [])
        
        if not items:
            return {'success': False, 'message': '请选择要清理的注册表项'}
        
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
        
        return {
            'success': True,
            'clearedCount': cleared_count,
            'errors': errors if errors else None
        }

    # ==================== 磁盘空间分析 ====================

    def minimize_window(self):
        '''最小化窗口'''
        try:
            if System._window:
                if hasattr(System._window, 'minimize'):
                    System._window.minimize()
                elif hasattr(System._window, 'hide'):
                    System._window.hide()
                else:
                    return {'success': False, 'message': '当前窗口不支持最小化'}
                return {'success': True}
            return {'success': False, 'message': '窗口对象未初始化'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def resize_window(self, payload=None):
        '''调整窗口大小（用于无边框拖拽缩放）'''
        try:
            if not System._window:
                return {'success': False, 'message': '窗口对象未初始化'}

            if not isinstance(payload, dict):
                return {'success': False, 'message': '参数无效'}

            width = payload.get('width')
            height = payload.get('height')
            fix_point_raw = payload.get('fixPoint')

            try:
                width = int(width)
                height = int(height)
            except (TypeError, ValueError):
                return {'success': False, 'message': '宽高无效'}

            fix_point = FixPoint.NORTH | FixPoint.WEST
            if isinstance(fix_point_raw, str) and fix_point_raw:
                flags = []
                token = fix_point_raw.upper()
                if 'N' in token:
                    flags.append(FixPoint.NORTH)
                if 'S' in token:
                    flags.append(FixPoint.SOUTH)
                if 'E' in token:
                    flags.append(FixPoint.EAST)
                if 'W' in token:
                    flags.append(FixPoint.WEST)
                if flags:
                    fix_point = FixPoint(0)
                    for flag in flags:
                        fix_point |= flag

            System._window.resize(width, height, fix_point)
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def close_window(self):
        '''关闭窗口'''
        try:
            if System._window:
                if hasattr(System._window, 'destroy'):
                    System._window.destroy()
                elif hasattr(System._window, 'close'):
                    System._window.close()
                else:
                    return {'success': False, 'message': '当前窗口不支持关闭'}
                return {'success': True}
            return {'success': False, 'message': '窗口对象未初始化'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def system_analyzeDisk(self, payload=None):
        '''分析指定目录的磁盘占用'''
        target_path = None
        max_depth = 3
        max_items = 100
        
        if isinstance(payload, dict):
            target_path = payload.get('path')
            max_depth = min(payload.get('maxDepth', 3), 5)
            max_items = min(payload.get('maxItems', 100), 500)
        elif isinstance(payload, str):
            target_path = payload
        
        if not target_path:
            return {'success': False, 'message': '请指定要分析的目录'}
        
        target = Path(target_path)
        if not target.exists():
            return {'success': False, 'message': '目录不存在'}
        if not target.is_dir():
            return {'success': False, 'message': '请指定一个目录'}
        
        def analyze_dir(dir_path: Path, current_depth: int) -> Dict:
            result = {
                'name': dir_path.name or str(dir_path),
                'path': str(dir_path),
                'size': 0,
                'fileCount': 0,
                'dirCount': 0,
                'children': []
            }
            
            try:
                entries = list(dir_path.iterdir())
            except (PermissionError, OSError):
                return result
            
            child_items = []
            
            for entry in entries:
                try:
                    if entry.is_file():
                        size = entry.stat().st_size
                        result['size'] += size
                        result['fileCount'] += 1
                        if current_depth < max_depth:
                            child_items.append({
                                'name': entry.name,
                                'path': str(entry),
                                'size': size,
                                'sizeText': format_bytes(size),
                                'isFile': True
                            })
                    elif entry.is_dir():
                        result['dirCount'] += 1
                        if current_depth < max_depth:
                            child_result = analyze_dir(entry, current_depth + 1)
                            result['size'] += child_result['size']
                            result['fileCount'] += child_result['fileCount']
                            result['dirCount'] += child_result['dirCount']
                            child_items.append({
                                'name': child_result['name'],
                                'path': child_result['path'],
                                'size': child_result['size'],
                                'sizeText': format_bytes(child_result['size']),
                                'isFile': False,
                                'fileCount': child_result['fileCount'],
                                'dirCount': child_result['dirCount'],
                                'children': child_result['children']
                            })
                        else:
                            # 只计算大小，不递归子目录详情
                            dir_size = 0
                            try:
                                for f in entry.rglob('*'):
                                    if f.is_file():
                                        try:
                                            dir_size += f.stat().st_size
                                        except (PermissionError, OSError):
                                            pass
                            except (PermissionError, OSError):
                                pass
                            result['size'] += dir_size
                            child_items.append({
                                'name': entry.name,
                                'path': str(entry),
                                'size': dir_size,
                                'sizeText': format_bytes(dir_size),
                                'isFile': False
                            })
                except (PermissionError, OSError):
                    continue
            
            # 按大小排序，取前 N 个
            child_items.sort(key=lambda x: x['size'], reverse=True)
            result['children'] = child_items[:max_items]
            result['sizeText'] = format_bytes(result['size'])
            
            return result
        
        tree = analyze_dir(target, 0)
        
        return {
            'success': True,
            'tree': tree
        }
