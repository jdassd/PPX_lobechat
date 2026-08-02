#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类 - 只读进程诊断 Mixin（进程列表、性能指标）
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None

from api.utils import format_bytes
from api.utils.error_handler import api_success


class ProcessMixin():
    '''只读进程诊断 Mixin：进程列表与性能指标。'''

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
