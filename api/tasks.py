#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent local task queue used by the desktop workbench."""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from collections import deque
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
}
_SENSITIVE_KEY = re.compile(r'(password|passwd|secret|token|cookie|authorization|api[_-]?key)', re.I)
_MAX_TASKS = 200
_MAX_STRING = 200_000
_TASK_STATUSES = ('queued', 'running', 'success', 'failed', 'interrupted', 'canceled')


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
        try:
            payload = json.loads(self._task_store_path.read_text(encoding='utf-8'))
            items = payload.get('tasks', []) if isinstance(payload, dict) else []
        except (OSError, ValueError, TypeError):
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
        payload = {'schemaVersion': 1, 'paused': self._task_paused, 'tasks': tasks}
        temp_path = self._task_store_path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp_path, self._task_store_path)

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
                'schemaVersion': 1,
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
            return api_success('任务已加入队列', taskId=task_id, task=task)
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
                return api_success(task=dict(task), paused=self._task_paused)
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
                    dict(self._task_items[task_id])
                    for task_id in self._task_order
                    if task_id in self._task_items
                ]
                status_counts = {status: 0 for status in _TASK_STATUSES}
                method_counts: Dict[str, int] = {}
                durations = []
                for task in all_tasks:
                    status = str(task.get('status') or '')
                    if status in status_counts:
                        status_counts[status] += 1
                    task_method = str(task.get('method') or '')
                    method_counts[task_method] = method_counts.get(task_method, 0) + 1
                    started_at = task.get('startedAt')
                    ended_at = task.get('endedAt')
                    if isinstance(started_at, (int, float)) and isinstance(ended_at, (int, float)):
                        durations.append(max(0.0, ended_at - started_at))

                tasks = []
                for task in all_tasks:
                    if statuses and task.get('status') not in statuses:
                        continue
                    if method and task.get('method') != method:
                        continue
                    if query:
                        haystack = ' '.join(
                            str(task.get(key) or '')
                            for key in ('id', 'method', 'message', 'retryOf')
                        ).lower()
                        if query not in haystack:
                            continue
                    tasks.append(task)

                total = len(tasks)
                offset = (page - 1) * page_size
                page_tasks = tasks[offset:offset + page_size]
                decisive = status_counts['success'] + status_counts['failed']
                stats = {
                    'total': len(all_tasks),
                    'active': status_counts['queued'] + status_counts['running'],
                    'attention': status_counts['failed'] + status_counts['interrupted'] + status_counts['canceled'],
                    'finished': len(all_tasks) - status_counts['queued'] - status_counts['running'],
                    'successRate': round(status_counts['success'] * 100 / decisive, 1) if decisive else 0,
                    'averageDurationSeconds': round(sum(durations) / len(durations), 2) if durations else 0,
                    'statusCounts': status_counts,
                    'methodCounts': method_counts,
                }
                return api_success(
                    tasks=page_tasks,
                    paused=self._task_paused,
                    stats=stats,
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
                return api_success(task=dict(task))
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

    def task_clear(self):
        self._tasks_ensure()
        with self._task_condition:
            active = {'queued', 'running'}
            keep = [task_id for task_id in self._task_order if self._task_items.get(task_id, {}).get('status') in active]
            self._task_items = {task_id: self._task_items[task_id] for task_id in keep}
            self._task_order = keep
            self._task_persist_locked()
        return api_success('已清除结束任务')

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
