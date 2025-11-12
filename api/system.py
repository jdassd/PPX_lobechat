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
import json
import os
import subprocess
from datetime import datetime

import webview

try:
    import psutil
except ImportError:
    psutil = None


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
        '''获取进程列表，可按名称和端口过滤'''
        if psutil is None:
            return self._psutil_missing_response()

        keyword = ''
        port = None
        limit = 200

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
        elif filters:
            keyword = str(filters).strip().lower()

        matched = list()
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
                    ports = self._collect_process_ports(proc)
                    if port is not None and port not in ports:
                        continue
                    matched.append({
                        'pid': info.get('pid'),
                        'name': name,
                        'status': info.get('status') or '',
                        'username': info.get('username') or '',
                        'createTime': info.get('create_time') or 0,
                        'createLabel': self._format_create_time(info.get('create_time')),
                        'memoryPercent': round(float(info.get('memory_percent') or 0), 2),
                        'cmdline': cmdline.strip(),
                        'ports': ports
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        matched.sort(key=lambda item: (item.get('memoryPercent', 0), item.get('pid', 0)), reverse=True)
        total = len(matched)
        limited = matched[:limit]
        return {
            'success': True,
            'items': limited,
            'total': total,
            'limit': limit,
            'hasMore': total > len(limited),
            'keyword': keyword,
            'port': port
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
