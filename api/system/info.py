#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 系统信息与基础交互 Mixin（应用信息、文件对话框、系统状态、磁盘分析）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

import getpass
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

import webview

try:
    import psutil
except ImportError:
    psutil = None

from api.utils import format_bytes
from api.utils.error_handler import api_success, api_error
from pyapp.config.config import Config
from pyapp.update.update import AppUpdate


class SystemInfoMixin():
    '''系统信息与基础交互 Mixin：应用信息、文件对话框、系统状态、磁盘分析'''

    def system_py2js(self, func, info):
        '''调用js中挂载到window的函数'''
        infoJson = json.dumps(info)
        self._window.evaluate_js(f"{func}({infoJson})")

    def system_getAppInfo(self):
        '''程序基础配置信息'''
        return {
            'appName': Config.appName,  # 应用名称
            'appVersion': Config.appVersion  # 应用版本号
        }

    def system_checkNewVersion(self, payload=None):
        '''检查更新'''
        appUpdate = AppUpdate()    # 程序更新类
        res = appUpdate.check(payload)
        return res

    def system_downloadNewVersion(self, payload=None):
        '''下载新版本'''
        appUpdate = AppUpdate()    # 程序更新类
        res = appUpdate.run(payload)
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
        result = self._window.create_file_dialog(dialog_type=webview.OPEN_DIALOG, directory=directory, allow_multiple=True, file_types=fileTypes)
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
        result = self._window.create_file_dialog(dialog_type=webview.FOLDER_DIALOG, directory=directory)
        if result is not None and len(result) > 0:
            if isinstance(result, tuple) or isinstance(result, list):
                return result[0]
            else:
                return result
        else:
            return ''

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
            # creationflags 携带 Windows 下的 CREATE_NO_WINDOW，避免弹出命令行窗口
            output = subprocess.check_output(
                command,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=self._subprocess_creationflags()
            )
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

        return api_success(
            updatedAt=now_label,
            uptime=uptime,
            load=load_data,
            cpu={
                'percent': round(cpu_percent or 0, 2),
                'cores': cpu_count,
                'freq': cpu_freq_label,
                'tempLabel': cpu_temp_label
            },
            memory={
                'percent': round(memory.percent or 0, 2),
                'total': memory.total,
                'used': memory.used,
                'totalText': format_bytes(memory.total),
                'usedText': format_bytes(memory.used),
                'text': f"{format_bytes(memory.used)} / {format_bytes(memory.total)}"
            },
            swap={
                'percent': round(swap.percent or 0, 2),
                'total': swap.total,
                'used': swap.used,
                'text': f"{format_bytes(swap.used)} / {format_bytes(swap.total)}"
            },
            disks=disks,
            gpus=gpus,
            sensors={
                'temperatures': temperatures,
                'fans': fans,
                'voltages': voltages
            }
        )

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
            return api_error('请指定要分析的目录')

        target = Path(target_path)
        if not target.exists():
            return api_error('目录不存在')
        if not target.is_dir():
            return api_error('请指定一个目录')

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

        return api_success(tree=tree)
