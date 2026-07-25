#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 进程管理 Mixin（进程列表、性能指标、结束进程）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None

from api.utils import format_bytes
from api.utils.error_handler import api_error, api_success


class ProcessMixin():
    '''进程管理 Mixin：进程列表、性能指标、结束进程、网络访问控制'''

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
        return api_success(
            items=limited,
            total=total,
            limit=limit,
            hasMore=total > len(limited),
            keyword=keyword,
            port=port,
            sortBy=sort_by,
            sortOrder=sort_order
        )

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
        return api_success(metrics=metrics, timestamp=timestamp)

    def system_killProcess(self, pid):
        '''强制结束指定进程'''
        if psutil is None:
            return self._psutil_missing_response()

        try:
            target_pid = int(pid)
        except (TypeError, ValueError):
            return api_error('请输入正确的 PID')

        if target_pid <= 0:
            return api_error('PID 需要为正整数')

        try:
            proc = psutil.Process(target_pid)
            name = proc.name()
            proc.kill()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                pass
            return api_success(pid=target_pid, name=name)
        except psutil.NoSuchProcess:
            return api_success('进程已不存在', pid=target_pid)
        except psutil.AccessDenied:
            return api_error('权限不足，建议以管理员方式运行 PPX 后重试', pid=target_pid)
        except Exception as err:
            return api_error(f'结束进程失败：{err}', pid=target_pid)

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
            return api_error('请提供 PID 列表')
        results = []
        overall_success = True
        for pid in pids:
            result = self.system_killProcess(pid)
            results.append(result)
            # 子结果采用统一返回格式，code==0 视为成功
            if result.get('code') != 0:
                overall_success = False
        if overall_success:
            return api_success(results=results)
        return api_error('部分进程结束失败', results=results)
