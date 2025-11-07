#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Codex
Date: 2025-02-14 10:00:00
LastEditTime: 2025-02-14 10:00:00
Description: 跨端工具箱 API
'''

import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import httpx
import psutil

from api.db.orm import ORM
from pyapp.config.config import Config


class Toolkit:
    '''工具箱 API 集合'''

    orm = ORM()
    _RATE_CACHE_PREFIX = 'toolkit_exchange_rates'
    _RATE_TTL_HOURS = 12
    _UNIT_CATALOG = {
        'length': {
            'label': '长度',
            'base': 'm',
            'units': {
                'mm': {'label': '毫米', 'factor': 0.001},
                'cm': {'label': '厘米', 'factor': 0.01},
                'm': {'label': '米', 'factor': 1},
                'km': {'label': '千米', 'factor': 1000},
                'in': {'label': '英寸', 'factor': 0.0254},
                'ft': {'label': '英尺', 'factor': 0.3048},
                'yd': {'label': '码', 'factor': 0.9144},
                'mi': {'label': '英里', 'factor': 1609.34}
            }
        },
        'weight': {
            'label': '重量',
            'base': 'g',
            'units': {
                'mg': {'label': '毫克', 'factor': 0.001},
                'g': {'label': '克', 'factor': 1},
                'kg': {'label': '千克', 'factor': 1000},
                't': {'label': '吨', 'factor': 1_000_000},
                'oz': {'label': '盎司', 'factor': 28.3495},
                'lb': {'label': '磅', 'factor': 453.592},
                'st': {'label': '英石', 'factor': 6350.29}
            }
        },
        'temperature': {
            'label': '温度',
            'base': 'c',
            'units': {
                'c': {'label': '℃'},
                'f': {'label': '℉'},
                'k': {'label': 'K'}
            }
        },
        'storage': {
            'label': '存储容量',
            'base': 'b',
            'units': {
                'b': {'label': 'Bytes', 'factor': 1},
                'kb': {'label': 'KB', 'factor': 1024},
                'mb': {'label': 'MB', 'factor': 1024 ** 2},
                'gb': {'label': 'GB', 'factor': 1024 ** 3},
                'tb': {'label': 'TB', 'factor': 1024 ** 4}
            }
        }
    }

    _THRESHOLDS = {
        'cpu': 85,
        'memory': 85,
        'disk': 90
    }

    def toolkit_get_unit_catalog(self):
        '''获取单位定义'''
        return Toolkit._UNIT_CATALOG

    def toolkit_convert_units(self, category, from_unit, to_unit, value):
        '''单位换算'''
        category = (category or '').lower()
        from_unit = (from_unit or '').lower()
        to_unit = (to_unit or '').lower()
        value = float(value)
        if category == 'temperature':
            return self._convert_temperature(from_unit, to_unit, value)
        if category not in Toolkit._UNIT_CATALOG:
            raise ValueError('不支持的单位类别')
        table = Toolkit._UNIT_CATALOG[category]['units']
        if from_unit not in table or to_unit not in table:
            raise ValueError('未知单位')
        base_value = value * table[from_unit]['factor']
        result = base_value / table[to_unit]['factor']
        return {
            'value': result,
            'display': self._trim_float(result)
        }

    def toolkit_get_exchange_rates(self, base='USD', force_refresh=False):
        '''获取汇率'''
        base = (base or 'USD').upper()
        cache_key = f'{Toolkit._RATE_CACHE_PREFIX}_{base}'
        cached = self._load_cache(cache_key)
        if cached and not force_refresh:
            fetched_at = cached.get('fetched_at')
            if fetched_at and not self._is_cache_expired(fetched_at):
                return cached
        fresh = self._pull_rates_from_remote(base)
        if fresh:
            self._save_cache(cache_key, fresh)
            return fresh
        if cached:
            cached['stale'] = True
            return cached
        raise RuntimeError('无法获取汇率数据')

    def toolkit_convert_currency(self, amount, source, target, base='USD', force_refresh=False):
        '''货币换算'''
        amount = float(amount)
        source = (source or '').upper()
        target = (target or '').upper()
        payload = self.toolkit_get_exchange_rates(base=base, force_refresh=force_refresh)
        rates = payload.get('rates', {})
        if source not in rates or target not in rates:
            raise ValueError('不支持的货币代码')
        base_rate = rates[source]
        target_rate = rates[target]
        base_code = payload['base']
        # 所有汇率都相对于 base
        base_value = amount / base_rate if source != base_code else amount
        result = base_value * target_rate if target != base_code else base_value
        return {
            'value': result,
            'display': self._trim_float(result),
            'meta': payload
        }

    def toolkit_get_system_metrics(self):
        '''系统资源监控数据'''
        timestamp = datetime.now(timezone.utc).isoformat()

        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_percent = sum(cpu_per_core) / len(cpu_per_core or [1])
        cpu_freq = psutil.cpu_freq()
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk_path = Config.appDataDir or os.path.expanduser('~')
        disk = psutil.disk_usage(disk_path)
        net = psutil.net_io_counters()

        gpu = self._get_gpu_snapshot()

        overview = {
            'cpu': round(cpu_percent, 2),
            'memory': round(mem.percent, 2),
            'disk': round(disk.percent, 2)
        }
        alerts = self._build_alerts(overview)

        return {
            'timestamp': timestamp,
            'overview': overview,
            'alerts': alerts,
            'cpu': {
                'percent': round(cpu_percent, 2),
                'perCore': cpu_per_core,
                'cores': psutil.cpu_count(logical=True),
                'frequency': cpu_freq._asdict() if cpu_freq else {},
                'loadAverage': list(load_avg)
            },
            'memory': {
                'percent': round(mem.percent, 2),
                'used': mem.used,
                'available': mem.available,
                'total': mem.total,
                'swap': {
                    'percent': round(swap.percent, 2) if swap.total else 0,
                    'used': swap.used,
                    'total': swap.total
                }
            },
            'disk': {
                'percent': round(disk.percent, 2),
                'used': disk.used,
                'free': disk.free,
                'total': disk.total,
                'path': disk_path
            },
            'network': {
                'bytesSent': net.bytes_sent,
                'bytesRecv': net.bytes_recv,
                'packetsSent': net.packets_sent,
                'packetsRecv': net.packets_recv
            },
            'gpu': gpu,
            'process': {
                'count': len(psutil.pids())
            },
            'thresholds': Toolkit._THRESHOLDS
        }

    # -------------------------
    # helpers
    # -------------------------

    def _convert_temperature(self, from_unit, to_unit, value):
        if from_unit == to_unit:
            return {'value': value, 'display': self._trim_float(value)}
        if from_unit == 'c':
            base_c = value
        elif from_unit == 'f':
            base_c = (value - 32) * 5 / 9
        elif from_unit == 'k':
            base_c = value - 273.15
        else:
            raise ValueError('未知温度单位')

        if to_unit == 'c':
            result = base_c
        elif to_unit == 'f':
            result = (base_c * 9 / 5) + 32
        elif to_unit == 'k':
            result = base_c + 273.15
        else:
            raise ValueError('未知温度单位')

        return {'value': result, 'display': self._trim_float(result)}

    def _pull_rates_from_remote(self, base):
        url = f'https://open.er-api.com/v6/latest/{base}'
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url)
                res.raise_for_status()
                data = res.json()
        except Exception as exc:
            print(f'[Toolkit] 获取汇率失败 => {exc}')
            return None
        if 'rates' not in data:
            return None
        payload = {
            'base': data.get('base_code', base),
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'provider': data.get('provider', 'open.er-api.com'),
            'rates': data['rates']
        }
        return payload

    def _is_cache_expired(self, fetched_at):
        try:
            fetch_time = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
        except ValueError:
            return True
        return datetime.now(timezone.utc) - fetch_time > timedelta(hours=Toolkit._RATE_TTL_HOURS)

    def _load_cache(self, key):
        raw = self.orm.getStorageVar(key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _save_cache(self, key, data):
        self.orm.setStorageVar(key, json.dumps(data))

    def _trim_float(self, value):
        if abs(value) >= 1:
            return round(value, 4)
        return float(f'{value:.8f}')

    def _get_gpu_snapshot(self):
        if not shutil.which('nvidia-smi'):
            return None
        cmd = [
            'nvidia-smi',
            '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu',
            '--format=csv,noheader,nounits'
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2, check=True)
            gpus = []
            for idx, line in enumerate(proc.stdout.strip().splitlines()):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) != 4:
                    continue
                util, mem_used, mem_total, temp = map(float, parts)
                gpus.append({
                    'name': f'GPU {idx}',
                    'util': util,
                    'memory': {
                        'used': mem_used,
                        'total': mem_total,
                        'percent': round((mem_used / mem_total) * 100, 2) if mem_total else 0
                    },
                    'temperature': temp
                })
            return gpus or None
        except Exception as exc:
            print(f'[Toolkit] GPU采集失败 => {exc}')
            return None

    def _build_alerts(self, overview):
        alerts = []
        for metric, percent in overview.items():
            limit = Toolkit._THRESHOLDS.get(metric)
            if limit and percent >= limit:
                alerts.append({
                    'type': metric,
                    'level': 'warning' if percent < 95 else 'danger',
                    'message': f'{metric.upper()} 已达到 {percent}%'
                })
        return alerts
