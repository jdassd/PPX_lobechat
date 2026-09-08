"""Bounded duplicate review and an explicit scan-time workbook snapshot."""
from __future__ import annotations

import hashlib
import os
import stat
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from api.core.context import checkpoint, report_progress
from api.core.file_search import search_files
from api.core.outputs import write_output
from api.utils import format_bytes


class _HashBudget(Exception):
    pass


def _signature(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _stable_hash(path, expected_size, check):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or getattr(before, 'st_file_attributes', 0) & 0x400:
        raise ValueError('文件已变为链接或不再是普通文件')
    if before.st_size != expected_size:
        raise ValueError('文件大小在扫描后发生变化，请重新扫描')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        if _signature(before) != _signature(os.fstat(source.fileno())):
            raise ValueError('打开文件时来源已变化')
        while True:
            check()
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        if _signature(before) != _signature(os.fstat(source.fileno())):
            raise ValueError('文件在内容比较期间发生变化，请重新扫描')
    if _signature(before) != _signature(path.lstat()):
        raise ValueError('文件在内容比较期间被替换，请重新扫描')
    return digest.hexdigest(), before


def scan_duplicates(directory, filters, limit, mode='content', *, max_hash_seconds=60):
    if mode not in {'content', 'name'}:
        raise ValueError('比较方式必须是 content 或 name')
    report_progress(message='正在收集文件；完成后仅比较同大小候选')
    search = search_files(directory, filters, limit)
    items = search.pop('items')
    result = {**search, 'groups': [], 'scanned': len(items), 'mode': mode,
              'hashedFiles': 0, 'candidateFiles': 0, 'hardLinkAliases': 0}

    def issue(path, code, message):
        result['complete'] = False
        result['errorCount'] += 1
        if len(result['errors']) < 20:
            result['errors'].append({'path': str(path), 'code': code, 'message': message})

    buckets = defaultdict(list)
    for item in items:
        checkpoint()
        buckets[item['name'].casefold() if mode == 'name' else item['size']].append(item)
    candidates = [bucket for bucket in buckets.values() if len(bucket) > 1]
    result['candidateFiles'] = sum(map(len, candidates))
    started = time.monotonic()
    groups = defaultdict(list)
    identities = {}

    def check():
        checkpoint()
        if time.monotonic() - started >= max_hash_seconds:
            raise _HashBudget

    try:
        for bucket in candidates:
            for item in bucket:
                checkpoint()
                if mode == 'name':
                    groups[item['name'].casefold()].append(item)
                    continue
                path = Path(item['path'])
                try:
                    digest, metadata = _stable_hash(path, item['size'], check)
                    result['hashedFiles'] += 1
                    # Distinct directory entries for the same inode are aliases,
                    # not independently reclaimable copies. Unknown inode = path.
                    identity = (metadata.st_dev, metadata.st_ino) if metadata.st_ino else str(path)
                    identities[item['path']] = identity
                    groups[(item['size'], digest)].append(item)
                except (OSError, ValueError) as exc:
                    issue(path, 'DUPLICATE_CHANGED_OR_UNREADABLE', str(exc))
                report_progress(result['hashedFiles'], result['candidateFiles'], '正在比较同大小文件内容')
    except _HashBudget:
        issue(directory, 'DUPLICATE_HASH_TIME_LIMIT', f'内容比较达到 {max_hash_seconds} 秒预算，请缩小范围后重试')
    duplicate_bytes = 0
    for key, members in groups.items():
        if len(members) < 2:
            continue
        copies = len({identities[item['path']] for item in members}) if mode == 'content' else None
        redundant = members[0]['size'] * max(0, copies - 1) if copies is not None else None
        if copies is not None:
            result['hardLinkAliases'] += len(members) - copies
            duplicate_bytes += redundant
        result['groups'].append({'count': len(members), 'files': [item['path'] for item in members],
                                 'sizes': [item['size'] for item in members],
                                 'sizeEach': format_bytes(members[0]['size']) if mode == 'content' else '大小可能不同',
                                 'digest': key[1] if mode == 'content' else None,
                                 'independentCopies': copies, 'duplicateBytes': redundant})
    result['groups'].sort(key=lambda group: group['files'][0].casefold())
    result.update(totalGroups=len(result['groups']), partial=not result['complete'],
                  duplicateBytes=duplicate_bytes if mode == 'content' else None,
                  spaceSaved=format_bytes(duplicate_bytes) if mode == 'content' else None)
    result['summary'] = {name: result[name] for name in (
        'mode', 'scanned', 'complete', 'truncated', 'partial', 'totalGroups', 'limit',
        'scannedEntries', 'skippedLinks', 'errorCount', 'errors', 'hashedFiles',
        'candidateFiles', 'hardLinkAliases', 'duplicateBytes')}
    result['summary'].update(scanId=uuid.uuid4().hex, scannedAt=datetime.now(timezone.utc).isoformat(),
                             directory=str(Path(directory).resolve()),
                             scope={'extensions': filters.get('extensions', []), 'keyword': filters.get('keyword', ''),
                                    'recursive': filters.get('recursive', True),
                                    'excludeDirectory': str(filters.get('exclude_directory') or '')})
    return result


def export_duplicate_report(groups, summary, output_dir):
    """Export supplied snapshot only; never reread or modify its source files."""
    from openpyxl import Workbook
    from openpyxl.cell import Cell
    if not isinstance(groups, list) or not isinstance(summary, dict):
        raise ValueError('报告需要扫描分组列表和摘要对象')
    if summary.get('mode') not in {'content', 'name'} or not isinstance(summary.get('complete'), bool):
        raise ValueError('扫描摘要缺少比较方式或完整性状态')
    if not summary.get('scanId') or not summary.get('scannedAt') or not summary.get('directory'):
        raise ValueError('扫描摘要缺少编号、时间或来源目录')
    if len(groups) > 10000 or sum(len(group.get('files', [])) for group in groups if isinstance(group, dict)) > 20000:
        raise ValueError('报告最多包含 20000 份文件，请缩小范围')
    if summary.get('totalGroups') != len(groups):
        raise ValueError('分组数量与扫描摘要不一致')
    rows = []
    for index, group in enumerate(groups, 1):
        checkpoint()
        if not isinstance(group, dict) or not isinstance(group.get('files'), list) or not isinstance(group.get('sizes'), list):
            raise ValueError('扫描分组格式错误')
        files, sizes = group['files'], group['sizes']
        if len(files) < 2 or len(files) != len(sizes) or group.get('count') != len(files):
            raise ValueError('扫描分组数量不一致')
        for path, size in zip(files, sizes, strict=True):
            if not isinstance(path, str) or not path or len(path) > 32767 or not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise ValueError('文件路径或字节数格式错误')
            rows.append([index, path, size, group.get('digest') or '未比较内容', group.get('independentCopies'), group.get('duplicateBytes')])
    # The bounded report uses a normal workbook so canceled row construction
    # cannot leave open write-only worksheet temporary files.
    book = Workbook()
    info = book.active
    info.title = '扫描说明'
    sheet = book.create_sheet('逐文件核对')
    sheet.freeze_panes = 'A2'
    sheet.column_dimensions['B'].width = 75
    sheet.column_dimensions['D'].width = 68
    info.column_dimensions['A'].width = 24
    info.column_dimensions['B'].width = 100

    def append(target, values):
        cells = []
        for value in values:
            if isinstance(value, (dict, list)):
                import json
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str):
                if len(value) > 32767:
                    raise ValueError('报告单元格超出 Excel 的 32767 字符上限')
                cell = Cell(target, value=value)
                cell.data_type = 's'
                cells.append(cell)
            else:
                cells.append(value)
        target.append(cells)

    try:
        append(info, ['报告性质', '扫描时快照；导出不重新核验文件。请核对后手动决定，不自动删除。'])
        append(info, ['完整性', '完整' if summary['complete'] else '不完整，仅列出已确认候选'])
        append(info, ['比较方式', 'SHA-256 内容比较' if summary['mode'] == 'content' else '同名候选，未比较内容'])
        append(info, ['体积说明', '内容模式按独立文件身份估算多余逻辑字节；硬链接别名不重复计数，不代表磁盘实际可释放空间。'])
        for key, value in summary.items():
            append(info, [key, value])
        append(sheet, ['分组', '文件路径', '扫描时字节数', 'SHA-256 / 比较说明', '组内独立文件数', '组内重复逻辑字节（勿按行累加）'])
        for row in rows:
            checkpoint()
            append(sheet, row)
        return write_output(Path(output_dir) / '重复文件核对报告.xlsx', book.save)
    finally:
        book.close()
