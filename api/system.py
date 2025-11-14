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
import hashlib
import json
import os
import platform
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import webview

try:
    import psutil
except ImportError:
    psutil = None


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
        System._window.evaluate_js(f"{func}('{infoJson}')")

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
        '''用电脑默认软件打开本地文件'''
        # 判断以下当前系统类型
        if Config.appIsMacOS:
            path = path.replace("\\", "/")
            subprocess.call(["open", path])
        else:
            path = path.replace("/", "\\")
            os.startfile(path)

    def system_pyCreateFileDialog(self, fileTypes=['全部文件 (*.*)'], directory=''):
        '''打开文件对话框'''
        # 可选文件类型
        # fileTypes = ['Excel表格 (*.xlsx;*.xls)']
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
        timestamp = datetime.utcnow().isoformat()
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
        '''列出自动启动规则'''
        try:
            return {
                'success': True,
                'rules': self._load_startup_rules()
            }
        except Exception as exc:
            return {'success': False, 'message': str(exc)}

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
            now = datetime.utcnow().isoformat()
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
            target['lastRun'] = datetime.utcnow().isoformat()
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

        def run_command(command: str):
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or 'netsh 执行失败，需管理员权限')

        try:
            sanitized = exe_path.replace('"', '')
            for direction in directions:
                rule_name = f'PPX_{rule_hash}_{direction.upper()}'
                if block:
                    cleanup = (
                        f'netsh advfirewall firewall delete rule name="{rule_name}" '
                        f'program="{sanitized}"'
                    )
                    subprocess.run(cleanup, capture_output=True, text=True, shell=True)
                    cmd = (
                        f'netsh advfirewall firewall add rule name="{rule_name}" '
                        f'dir={direction} action=block program="{sanitized}" enable=yes'
                    )
                else:
                    cmd = (
                        f'netsh advfirewall firewall delete rule name="{rule_name}" '
                        f'program="{sanitized}"'
                    )
                run_command(cmd)
            return {
                'success': True,
                'pid': proc.pid,
                'program': exe_path,
                'blocked': block
            }
        except Exception as exc:
            return {'success': False, 'message': str(exc)}
