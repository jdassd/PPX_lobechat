"""Bounded, path-level provenance; this does not assert content identity."""
from __future__ import annotations

import ntpath
import os
import re

from api.operations import OPERATIONS

MAX_ORIGINS = 200


def path_identity(value):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(c in value for c in '\x00\n\r'):
        return None
    if re.match(r'^[a-zA-Z]:[\\/]', value) or value.startswith(('\\\\', '//')):
        return ntpath.normcase(ntpath.normpath(value))
    if '://' in value:
        return None
    return os.path.normcase(os.path.abspath(os.path.expanduser(value)))


def primary_paths(method, args):
    descriptor = OPERATIONS.get(method)
    if not descriptor or not args or not isinstance(args[0], dict):
        return set()

    budget = [10000]

    def values(value, parts, depth=0):
        budget[0] -= 1
        if depth > 12 or budget[0] < 0:
            return
        if isinstance(value, list):
            for item in value[:10000]:
                yield from values(item, parts, depth + 1)
        elif parts and isinstance(value, dict):
            yield from values(value.get(parts[0]), parts[1:], depth + 1)
        elif not parts:
            identity = path_identity(value.get('path') if isinstance(value, dict) else value)
            if identity:
                yield identity

    paths = {path for field in descriptor.primaryInputFields for path in values(args[0], field.split('.'))}
    if isinstance(args[0].get('_retryInputs'), list):
        paths &= {path_identity(item) for item in args[0]['_retryInputs']}
    return paths


def validate_origins(raw, method, args, source_lookup):
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], ['来源信息必须为数组，已忽略']
    warnings = []
    if len(raw) > MAX_ORIGINS:
        warnings.append('来源信息超过 200 项，超出部分已忽略')
    paths = primary_paths(method, args)
    accepted, seen = [], set()

    def warn(message):
        if message not in warnings:
            warnings.append(message)

    for item in raw[:MAX_ORIGINS]:
        if not isinstance(item, dict):
            warn('来源信息格式无效，已忽略')
            continue
        input_path, asset_path, source_id = item.get('inputPath'), item.get('sourceAssetPath'), item.get('sourceTaskId')
        identity = path_identity(input_path)
        if not identity or not isinstance(source_id, str) or not source_id or len(source_id) > 128:
            warn('来源信息格式无效，已忽略')
            continue
        if identity not in paths:
            warn('来源文件不在本次主输入中，已忽略')
            continue
        if identity != path_identity(asset_path):
            warn('来源输出路径与输入不一致，已忽略')
            continue
        source = source_lookup(source_id)
        if not source:
            warn('来源任务已清理或不存在，已忽略')
            continue
        if not any(isinstance(asset, dict) and asset.get('kind') == 'file' and
                   path_identity(asset.get('path')) == identity for asset in source.get('outputs', [])):
            warn('来源任务未记录该输出文件，已忽略')
            continue
        key = (identity, source_id)
        if key in seen:
            continue
        seen.add(key)
        accepted.append({'inputPath': input_path, 'sourceTaskId': source_id, 'sourceAssetPath': asset_path,
                         'sourceMethod': source.get('method'), 'sourceCreatedAt': source.get('createdAt'),
                         'validation': 'primary-path-output-v1'})
    return accepted, warnings


def retry_origins(origins, method, args):
    paths = primary_paths(method, args)
    return [dict(item) for item in origins[:MAX_ORIGINS]
            if isinstance(item, dict) and item.get('validation') == 'primary-path-output-v1'
            and path_identity(item.get('inputPath')) in paths]
