#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent local task queue used by the desktop workbench."""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from collections import deque
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from api.utils.error_handler import api_error, api_success
from pyapp.config.config import Config

TRACKED_METHODS = {
    'image_format_convert', 'image_batch_compress', 'image_crop', 'image_add_watermark',
    'image_rotate_flip', 'image_concat', 'image_batch_rename', 'image_to_pdf', 'ocr_image',
    'pdf_convert_to_images', 'pdf_convert_to_scan', 'pdf_compress', 'pdf_merge', 'pdf_split',
    'pdf_cut', 'pdf_multi_cut', 'pdf_extract_text', 'ocr_pdf', 'pdf_to_word', 'pdf_extract_images',
    'pdf_page_workbench', 'pdf_secure', 'word_split', 'word_cut', 'word_merge',
    'excel_process', 'excel_merge_tables', 'excel_column_profile', 'excel_split_by_column',
    'excel_quality_report',
    'text_format_json', 'text_case_transform', 'text_deduplicate_sort', 'text_batch_replace',
    'video_format_convert', 'video_compress', 'video_cut', 'video_extract_audio', 'video_concat',
    'file_search', 'file_auto_classify', 'file_batch_copy', 'file_batch_delete',
    'file_batch_rename', 'file_batch_rename_undo', 'file_deduplicate', 'file_compress',
    'file_decompress', 'file_recycle_restore', 'file_recycle_purge', 'seal_generate',
    'ocr_table', 'document_index_build', 'workflow_run',
    'format_center_convert', 'format_center_images_to_pdf', 'format_center_merge_pdfs',
}
_SENSITIVE_KEY = re.compile(r'(password|passwd|secret|token|cookie|authorization|api[_-]?key)', re.I)
_MAX_TASKS = 200
_MAX_STRING = 200_000
_TASK_STATUSES = ('queued', 'running', 'success', 'failed', 'interrupted', 'canceled')
_TERMINAL_STATUSES = {'success', 'failed', 'interrupted', 'canceled'}
_OUTPUT_KEYS = ('output', 'outputPath', 'outputDir', 'path', 'archive', 'file')
_OUTPUT_LIST_KEYS = ('outputs', 'files', 'created', 'items')


def _task_path_like(value: Any) -> bool:
    if not isinstance(value, (str, os.PathLike)):
        return False
    raw = os.fspath(value).strip()
    if not raw or len(raw) > 4096 or '\n' in raw or '\r' in raw or raw.lower().startswith(('http://', 'https://')):
        return False
    path = Path(raw).expanduser()
    return path.exists() or path.is_absolute() or '/' in raw or '\\' in raw


def _task_output_assets(result: Any) -> List[Dict[str, Any]]:
    """Extract local result files/directories without mistaking text output for a path."""
    raw_paths: List[str] = []

    def add(value: Any) -> None:
        if _task_path_like(value):
            raw_paths.append(os.fspath(value).strip())
            return
        if isinstance(value, dict):
            for key in _OUTPUT_KEYS:
                if key in value:
                    add(value.get(key))
            return
        if isinstance(value, (list, tuple)):
            for item in value[:200]:
                add(item)

    if isinstance(result, dict):
        for key in _OUTPUT_KEYS + _OUTPUT_LIST_KEYS:
            if key in result:
                add(result.get(key))

    assets = []
    seen = set()
    for raw in raw_paths:
        expanded = Path(raw).expanduser()
        identity = os.path.normcase(os.path.abspath(str(expanded)))
        if identity in seen:
            continue
        seen.add(identity)
        exists = expanded.exists()
        is_directory = expanded.is_dir() if exists else raw.endswith(('/', '\\'))
        size = None
        if exists and not is_directory:
            try:
                size = expanded.stat().st_size
            except OSError:
                pass
        assets.append({
            'path': raw,
            'name': expanded.name or raw,
            'kind': 'directory' if is_directory else 'file',
            'exists': exists,
            'size': size,
        })
    return assets


def _task_diagnosis(task: Dict[str, Any]) -> Dict[str, str] | None:
    status = str(task.get('status') or '')
    if status not in {'failed', 'interrupted', 'canceled'}:
        return None
    message = str(task.get('message') or '')
    lowered = message.lower()
    if status == 'interrupted':
        return {
            'category': 'interrupted',
            'title': '任务被应用退出中断',
            'suggestion': '确认输入文件仍在原位置后直接重试；任务会以新记录重新进入队列。',
        }
    if status == 'canceled':
        return {
            'category': 'canceled',
            'title': '任务已取消',
            'suggestion': '取消可能留下部分输出，请先检查结果目录，再决定是否重试。',
        }
    rules = (
        (
            'dependency',
            '缺少处理组件',
            ('ffmpeg', 'ffprobe', 'libreoffice', 'rapidocr', 'playwright', 'chromium', '组件未安装', 'not installed'),
            '前往模块中心重新检测依赖，按提示安装或修复后再重试。',
        ),
        (
            'storage',
            '磁盘空间不足',
            ('no space left', 'disk full', '磁盘空间', '空间不足'),
            '释放输出磁盘空间，或在工具页面改用其他输出目录后重新提交。',
        ),
        (
            'permission',
            '没有文件访问权限',
            ('permission denied', 'access denied', '拒绝访问', '没有权限', '权限不足'),
            '检查源文件和输出目录权限，关闭可能占用文件的程序后重试。',
        ),
        (
            'missing-input',
            '源文件或目录已不存在',
            ('no such file', 'not found', '文件不存在', '目录不存在', '找不到文件'),
            '返回原工具重新选择仍然存在的输入文件或目录。',
        ),
        (
            'timeout',
            '处理超时',
            ('timeout', 'timed out', '超时'),
            '减少单次文件数量或文件体积，确认依赖组件可用后再重试。',
        ),
        (
            'input',
            '输入参数或文件格式不符合要求',
            ('invalid', 'json', '参数', '格式错误', '不支持的文件格式', '密码错误'),
            '打开原工具检查文件格式与参数，再重新提交任务。',
        ),
    )
    for category, title, patterns, suggestion in rules:
        if any(pattern in lowered for pattern in patterns):
            return {'category': category, 'title': title, 'suggestion': suggestion}
    return {
        'category': 'unknown',
        'title': '处理未完成',
        'suggestion': '展开错误信息核对输入；如果问题持续，可在维护中心导出隐私安全的诊断报告。',
    }


def _json_safe(value: Any, key: str = '', depth: int = 0) -> Tuple[Any, bool]:
    """Return a JSON-safe value plus whether it can be safely retried."""
    if key and _SENSITIVE_KEY.search(key):
        return '[REDACTED]', False
    if depth > 12:
        return '[DEPTH_LIMIT]', False
    if value is None or isinstance(value, (bool, int, float)):
        return value, True
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            return value[:_MAX_STRING] + '\n[TRUNCATED]', False
        return value, True
    if isinstance(value, Path):
        return str(value), True
    if isinstance(value, (list, tuple)):
        output: List[Any] = []
        retryable = True
        for item in value:
            safe, item_retryable = _json_safe(item, depth=depth + 1)
            output.append(safe)
            retryable = retryable and item_retryable
        return output, retryable
    if isinstance(value, dict):
        output: Dict[str, Any] = {}
        retryable = True
        for raw_key, item in value.items():
            item_key = str(raw_key)
            safe, item_retryable = _json_safe(item, item_key, depth + 1)
            output[item_key] = safe
            retryable = retryable and item_retryable
        return output, retryable
    return str(value), False


class TaskMixin:
    """A single-worker, persistent queue with pause, cancel and retry APIs."""

    _task_boot_lock = threading.Lock()

    def _tasks_ensure(self) -> None:
        if getattr(self, '_task_ready', False):
            return
        with self._task_boot_lock:
            if getattr(self, '_task_ready', False):
                return
            task_dir = Path(Config.appDataDir) / 'tasks'
            task_dir.mkdir(parents=True, exist_ok=True)
            self._task_store_path = task_dir / 'history.json'
            self._task_lock = threading.RLock()
            self._task_condition = threading.Condition(self._task_lock)
            self._task_items: Dict[str, Dict[str, Any]] = {}
            self._task_order: List[str] = []
            self._task_queue = deque()
            self._task_runtime_args: Dict[str, List[Any]] = {}
            self._task_paused = False
            self._task_stopping = False
            self._task_load_locked()
            self._task_worker_thread = threading.Thread(target=self._task_worker, name='ppx-task-worker', daemon=True)
            self._task_ready = True
            self._task_worker_thread.start()

    def _task_load_locked(self) -> None:
        items = []
        for candidate in (self._task_store_path, self._task_store_path.with_suffix('.bak')):
            try:
                payload = json.loads(candidate.read_text(encoding='utf-8'))
                items = payload.get('tasks', []) if isinstance(payload, dict) else []
                if isinstance(items, list):
                    break
            except (OSError, ValueError, TypeError):
                continue
        if not isinstance(items, list):
            items = []
        changed = False
        for item in items[:_MAX_TASKS]:
            if not isinstance(item, dict) or not item.get('id'):
                continue
            task = dict(item)
            if task.get('status') in {'queued', 'running'}:
                task['status'] = 'interrupted'
                task['message'] = '应用在任务完成前退出，可从任务中心重试'
                task['endedAt'] = time.time()
                changed = True
            task_id = str(task['id'])
            self._task_items[task_id] = task
            self._task_order.append(task_id)
        if changed:
            self._task_persist_locked()

    def _task_persist_locked(self) -> None:
        tasks = [self._task_items[task_id] for task_id in self._task_order[:_MAX_TASKS] if task_id in self._task_items]
        payload = {'schemaVersion': 2, 'paused': self._task_paused, 'tasks': tasks}
        temp_path = self._task_store_path.with_suffix('.tmp')
        with temp_path.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        if self._task_store_path.is_file():
            backup_temp = self._task_store_path.with_suffix('.bak.tmp')
            shutil.copy2(self._task_store_path, backup_temp)
            os.replace(backup_temp, self._task_store_path.with_suffix('.bak'))
        os.replace(temp_path, self._task_store_path)

    @staticmethod
    def _task_snapshot(task: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = dict(task)
        snapshot['outputs'] = _task_output_assets(snapshot.get('result'))
        diagnosis = _task_diagnosis(snapshot)
        if diagnosis:
            snapshot['diagnosis'] = diagnosis
        else:
            snapshot.pop('diagnosis', None)
        return snapshot

    @staticmethod
    def _task_stats(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        status_counts = {status: 0 for status in _TASK_STATUSES}
        method_metrics: Dict[str, Dict[str, Any]] = {}
        durations = []
        first_day = date.today() - timedelta(days=6)
        daily = {
            first_day + timedelta(days=offset): {'total': 0, 'success': 0, 'attention': 0}
            for offset in range(7)
        }
        for task in tasks:
            status = str(task.get('status') or '')
            if status in status_counts:
                status_counts[status] += 1
            method = str(task.get('method') or '')
            metric = method_metrics.setdefault(
                method,
                {'method': method, 'total': 0, 'success': 0, 'attention': 0, 'durationTotal': 0.0, 'durationCount': 0},
            )
            metric['total'] += 1
            if status == 'success':
                metric['success'] += 1
            if status in {'failed', 'interrupted', 'canceled'}:
                metric['attention'] += 1
            started_at = task.get('startedAt')
            ended_at = task.get('endedAt')
            if isinstance(started_at, (int, float)) and isinstance(ended_at, (int, float)):
                duration = max(0.0, ended_at - started_at)
                durations.append(duration)
                metric['durationTotal'] += duration
                metric['durationCount'] += 1
            created_at = task.get('createdAt')
            if isinstance(created_at, (int, float)):
                task_day = date.fromtimestamp(created_at)
                if task_day in daily:
                    daily[task_day]['total'] += 1
                    if status == 'success':
                        daily[task_day]['success'] += 1
                    if status in {'failed', 'interrupted', 'canceled'}:
                        daily[task_day]['attention'] += 1

        method_stats = []
        for metric in method_metrics.values():
            decisive = metric['success'] + metric['attention']
            method_stats.append({
                'method': metric['method'],
                'total': metric['total'],
                'success': metric['success'],
                'attention': metric['attention'],
                'successRate': round(metric['success'] * 100 / decisive, 1) if decisive else 0,
                'averageDurationSeconds': round(metric['durationTotal'] / metric['durationCount'], 2) if metric['durationCount'] else 0,
            })
        method_stats.sort(key=lambda item: (-item['attention'], -item['total'], -item['averageDurationSeconds'], item['method']))
        decisive = status_counts['success'] + status_counts['failed']
        return {
            'total': len(tasks),
            'active': status_counts['queued'] + status_counts['running'],
            'attention': status_counts['failed'] + status_counts['interrupted'] + status_counts['canceled'],
            'finished': len(tasks) - status_counts['queued'] - status_counts['running'],
            'successRate': round(status_counts['success'] * 100 / decisive, 1) if decisive else 0,
            'averageDurationSeconds': round(sum(durations) / len(durations), 2) if durations else 0,
            'statusCounts': status_counts,
            'methodCounts': {item['method']: item['total'] for item in method_stats},
            'daily': [
                {'date': day.isoformat(), **values}
                for day, values in daily.items()
            ],
            'methodStats': method_stats,
        }

    @staticmethod
    def _task_ok(result: Any) -> bool:
        return isinstance(result, dict) and (result.get('code') == 0 or result.get('success') is True)

    @staticmethod
    def _task_message(result: Any, ok: bool) -> str:
        if isinstance(result, dict):
            message = result.get('msg') if result.get('msg') is not None else result.get('message')
            if message:
                return str(message)
        return '处理完成' if ok else '处理失败'

    def _task_worker(self) -> None:
        while True:
            with self._task_condition:
                while not self._task_stopping and (self._task_paused or not self._task_queue):
                    self._task_condition.wait(timeout=0.5)
                if self._task_stopping:
                    return
                task_id = self._task_queue.popleft()
                task = self._task_items.get(task_id)
                if not task or task.get('status') != 'queued':
                    continue
                task['status'] = 'running'
                task['startedAt'] = time.time()
                task['progress'] = 5
                task['message'] = '正在处理'
                self._task_persist_locked()
                method = task['method']
                args = self._task_runtime_args.get(task_id, task.get('args', []))
            try:
                handler = getattr(self, method, None)
                if not callable(handler) or method not in TRACKED_METHODS:
                    raise ValueError(f'不支持的任务方法：{method}')
                result = handler(*args)
                ok = self._task_ok(result)
                safe_result, _ = _json_safe(result)
                with self._task_condition:
                    task = self._task_items.get(task_id)
                    if not task:
                        continue
                    task['result'] = safe_result
                    task['progress'] = 100
                    task['endedAt'] = time.time()
                    if task.get('cancelRequested'):
                        task['status'] = 'canceled'
                        task['message'] = '已响应取消请求；任务可能已产生部分输出'
                    else:
                        task['status'] = 'success' if ok else 'failed'
                        task['message'] = self._task_message(result, ok)
                    self._task_runtime_args.pop(task_id, None)
                    self._task_persist_locked()
                    self._task_condition.notify_all()
            except Exception as exc:
                with self._task_condition:
                    task = self._task_items.get(task_id)
                    if task:
                        task['status'] = 'failed'
                        task['progress'] = 100
                        task['endedAt'] = time.time()
                        task['message'] = str(exc)
                        task['result'] = {'code': -1, 'msg': str(exc)}
                        self._task_runtime_args.pop(task_id, None)
                        self._task_persist_locked()
                        self._task_condition.notify_all()

    def task_methods(self):
        return api_success(methods=sorted(TRACKED_METHODS))

    def task_submit(self, options: Dict | None = None):
        try:
            self._tasks_ensure()
            options = options or {}
            method = str(options.get('method') or '')
            args = options.get('args') or []
            if method not in TRACKED_METHODS:
                return api_error(f'方法不能进入任务队列：{method}')
            if not isinstance(args, list):
                return api_error('任务参数必须是数组')
            safe_args, retryable = _json_safe(args)
            task_id = uuid.uuid4().hex
            created_at = time.time()
            task = {
                'id': task_id,
                'schemaVersion': 2,
                'method': method,
                'args': safe_args,
                'retryable': retryable,
                'retryOf': str(options.get('retryOf') or ''),
                'status': 'queued',
                'progress': 0,
                'message': '等待执行',
                'createdAt': created_at,
                'startedAt': None,
                'endedAt': None,
                'cancelRequested': False,
                'result': None,
            }
            with self._task_condition:
                self._task_items[task_id] = task
                self._task_order.insert(0, task_id)
                self._task_runtime_args[task_id] = args
                if int(options.get('priority') or 0) > 0:
                    self._task_queue.appendleft(task_id)
                else:
                    self._task_queue.append(task_id)
                self._task_order = self._task_order[:_MAX_TASKS]
                self._task_persist_locked()
                self._task_condition.notify_all()
            return api_success('任务已加入队列', taskId=task_id, task=self._task_snapshot(task))
        except Exception as exc:
            return api_error(f'创建任务失败：{exc}')

    def task_get(self, options: Dict | str | None = None):
        try:
            self._tasks_ensure()
            task_id = str(options.get('id') if isinstance(options, dict) else options or '')
            with self._task_lock:
                task = self._task_items.get(task_id)
                if not task:
                    return api_error('任务不存在')
                return api_success(task=self._task_snapshot(task), paused=self._task_paused)
        except Exception as exc:
            return api_error(f'读取任务失败：{exc}')

    def task_list(self, options: Dict | None = None):
        try:
            self._tasks_ensure()
            options = options or {}
            page_size = max(1, min(_MAX_TASKS, int(options.get('pageSize') or options.get('limit') or 100)))
            page = max(1, int(options.get('page') or 1))
            raw_statuses = options.get('statuses') if options.get('statuses') is not None else options.get('status')
            if isinstance(raw_statuses, str):
                raw_statuses = [item.strip() for item in raw_statuses.split(',') if item.strip()]
            statuses = {str(item) for item in (raw_statuses or []) if str(item) in _TASK_STATUSES}
            method = str(options.get('method') or '').strip()
            query = str(options.get('query') or options.get('search') or '').strip().lower()
            with self._task_lock:
                all_tasks = [
                    self._task_snapshot(self._task_items[task_id])
                    for task_id in self._task_order
                    if task_id in self._task_items
                ]
                tasks = []
                for task in all_tasks:
                    if statuses and task.get('status') not in statuses:
                        continue
                    if method and task.get('method') != method:
                        continue
                    if query:
                        output_paths = ' '.join(str(item.get('path') or '') for item in task.get('outputs') or [])
                        diagnosis = task.get('diagnosis') or {}
                        haystack = ' '.join([
                            *(str(task.get(key) or '') for key in ('id', 'method', 'message', 'retryOf')),
                            output_paths,
                            str(diagnosis.get('title') or ''),
                            str(diagnosis.get('suggestion') or ''),
                        ]).lower()
                        if query not in haystack:
                            continue
                    tasks.append(task)

                total = len(tasks)
                offset = (page - 1) * page_size
                page_tasks = tasks[offset:offset + page_size]
                return api_success(
                    tasks=page_tasks,
                    paused=self._task_paused,
                    stats=self._task_stats(all_tasks),
                    total=total,
                    page=page,
                    pageSize=page_size,
                    hasMore=offset + len(page_tasks) < total,
                )
        except Exception as exc:
            return api_error(f'读取任务列表失败：{exc}')

    def task_cancel(self, options: Dict | str | None = None):
        try:
            self._tasks_ensure()
            task_id = str(options.get('id') if isinstance(options, dict) else options or '')
            with self._task_condition:
                task = self._task_items.get(task_id)
                if not task:
                    return api_error('任务不存在')
                if task.get('status') == 'queued':
                    try:
                        self._task_queue.remove(task_id)
                    except ValueError:
                        pass
                    task['status'] = 'canceled'
                    task['message'] = '任务已取消'
                    task['endedAt'] = time.time()
                    task['progress'] = 100
                elif task.get('status') == 'running':
                    task['cancelRequested'] = True
                    task['message'] = '已请求取消，将在当前处理步骤结束后停止'
                else:
                    return api_error('该任务已经结束')
                self._task_persist_locked()
                self._task_condition.notify_all()
                return api_success(task=self._task_snapshot(task))
        except Exception as exc:
            return api_error(f'取消任务失败：{exc}')

    def task_retry(self, options: Dict | str | None = None):
        self._tasks_ensure()
        task_id = str(options.get('id') if isinstance(options, dict) else options or '')
        with self._task_lock:
            task = self._task_items.get(task_id)
            if not task:
                return api_error('任务不存在')
            if task.get('status') not in {'failed', 'interrupted', 'canceled'}:
                return api_error('只有失败、中断或取消的任务可以重试')
            if not task.get('retryable', False):
                return api_error('任务包含敏感或过大的参数，请返回工具页面重新提交')
            method = task['method']
            args = task.get('args') or []
        return self.task_submit({'method': method, 'args': args, 'retryOf': task_id, 'priority': 1})

    @staticmethod
    def _task_batch_ids(options: Dict | None = None) -> List[str]:
        if not isinstance(options, dict):
            return []
        raw_ids = options.get('ids') or []
        if isinstance(raw_ids, str):
            raw_ids = [raw_ids]
        if not isinstance(raw_ids, list):
            return []
        output = []
        seen = set()
        for raw_id in raw_ids[:_MAX_TASKS]:
            task_id = str(raw_id or '').strip()
            if task_id and task_id not in seen:
                output.append(task_id)
                seen.add(task_id)
        return output

    def _task_batch_action(self, options: Dict | None, action: str):
        task_ids = self._task_batch_ids(options)
        if not task_ids:
            return api_error('请选择至少一个任务')
        handler = self.task_cancel if action == 'cancel' else self.task_retry
        results = []
        for task_id in task_ids:
            outcome = handler({'id': task_id})
            ok = self._task_ok(outcome)
            result = {
                'id': task_id,
                'ok': ok,
                'message': self._task_message(outcome, ok),
            }
            if isinstance(outcome, dict) and outcome.get('taskId'):
                result['taskId'] = outcome['taskId']
            results.append(result)
        succeeded = sum(1 for item in results if item['ok'])
        failed = len(results) - succeeded
        label = '取消' if action == 'cancel' else '重试'
        payload = {'results': results, 'succeeded': succeeded, 'failed': failed}
        if not succeeded:
            return api_error(f'批量{label}失败', **payload)
        return api_success(f'已{label} {succeeded} 个任务，失败 {failed} 个', **payload)

    def task_batch_cancel(self, options: Dict | None = None):
        return self._task_batch_action(options, 'cancel')

    def task_batch_retry(self, options: Dict | None = None):
        return self._task_batch_action(options, 'retry')

    def task_queue_pause(self):
        self._tasks_ensure()
        with self._task_condition:
            self._task_paused = True
            self._task_persist_locked()
        return api_success('任务队列已暂停；正在运行的任务不会被强制中止', paused=True)

    def task_queue_resume(self):
        self._tasks_ensure()
        with self._task_condition:
            self._task_paused = False
            self._task_persist_locked()
            self._task_condition.notify_all()
        return api_success('任务队列已继续', paused=False)

    def task_clear(self, options: Dict | None = None):
        """Preview or remove a bounded subset of terminal task history."""
        try:
            self._tasks_ensure()
            options = options or {}
            raw_statuses = options.get('statuses') if options.get('statuses') is not None else options.get('status')
            statuses_supplied = raw_statuses is not None
            if isinstance(raw_statuses, str):
                raw_statuses = [item.strip() for item in raw_statuses.split(',') if item.strip()]
            statuses = {str(item) for item in (raw_statuses if statuses_supplied else _TERMINAL_STATUSES)} & _TERMINAL_STATUSES
            if not statuses:
                return api_error('请选择至少一种可清理的结束状态')
            ids_supplied = options.get('ids') is not None
            ids = set(self._task_batch_ids(options)) if ids_supplied else set()
            method = str(options.get('method') or '').strip()
            try:
                before = float(options.get('before') or 0)
            except (TypeError, ValueError):
                return api_error('清理时间无效')
            dry_run = bool(options.get('dryRun'))
            with self._task_condition:
                removable = []
                for task_id in self._task_order:
                    task = self._task_items.get(task_id, {})
                    if task.get('status') not in statuses:
                        continue
                    if ids_supplied and task_id not in ids:
                        continue
                    if method and task.get('method') != method:
                        continue
                    ended_at = task.get('endedAt') or task.get('createdAt') or 0
                    if before and (not isinstance(ended_at, (int, float)) or ended_at >= before):
                        continue
                    removable.append(task_id)
                if dry_run:
                    return api_success(
                        '清理预览已生成',
                        removableCount=len(removable),
                        removableIds=removable,
                        statuses=sorted(statuses),
                    )
                removable_set = set(removable)
                self._task_order = [task_id for task_id in self._task_order if task_id not in removable_set]
                for task_id in removable:
                    self._task_items.pop(task_id, None)
                    self._task_runtime_args.pop(task_id, None)
                self._task_persist_locked()
            return api_success(
                f'已清除 {len(removable)} 条任务记录',
                removedCount=len(removable),
                removedIds=removable,
            )
        except Exception as exc:
            return api_error(f'清理任务记录失败：{exc}')

    def task_shutdown(self):
        if not getattr(self, '_task_ready', False):
            return
        with self._task_condition:
            self._task_stopping = True
            for task_id in list(self._task_queue):
                task = self._task_items.get(task_id)
                if task and task.get('status') == 'queued':
                    task['status'] = 'interrupted'
                    task['message'] = '应用关闭，任务尚未开始'
                    task['endedAt'] = time.time()
            self._task_queue.clear()
            self._task_persist_locked()
            self._task_condition.notify_all()
        self._task_worker_thread.join(timeout=1.5)
