#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe, persistent workflows, interval schedules and folder watches."""
from __future__ import annotations

import copy
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

from api.utils.error_handler import api_error, api_success
from pyapp.config.config import Config

WORKFLOW_METHODS = {
    'image_format_convert', 'image_batch_compress', 'image_crop', 'image_add_watermark',
    'image_rotate_flip', 'image_concat', 'image_batch_rename', 'image_to_pdf', 'ocr_image',
    'pdf_convert_to_images', 'pdf_convert_to_scan', 'pdf_compress', 'pdf_merge', 'pdf_split',
    'pdf_cut', 'pdf_multi_cut', 'pdf_extract_text', 'ocr_pdf', 'pdf_to_word', 'pdf_extract_images',
    'pdf_page_workbench', 'pdf_secure', 'word_split', 'word_cut', 'word_merge',
    'excel_process', 'excel_merge_tables', 'excel_split_by_column', 'excel_quality_report',
    'text_format_json', 'text_case_transform', 'text_deduplicate_sort', 'text_batch_replace',
    'video_format_convert', 'video_compress', 'video_cut', 'video_extract_audio', 'video_concat',
    'file_search', 'file_auto_classify', 'file_batch_copy', 'file_batch_rename',
    'file_deduplicate', 'file_compress', 'file_decompress', 'seal_generate',
    'ocr_table', 'document_index_build',
}

_BINDING = re.compile(r'\{\{\s*([a-zA-Z_][\w]*(?:\.[\w-]+)*)\s*\}\}')
_MAX_RUNS = 80

BUILTIN_WORKFLOWS = [
    {
        'id': 'builtin-pdf-ocr-word',
        'name': '扫描 PDF → OCR → Word',
        'description': '把扫描件识别为可搜索 PDF，再转换为可编辑 Word。',
        'inputExample': {'filePath': '/path/to/scan.pdf', 'outputDir': '/path/to/output'},
        'steps': [
            {
                'id': 'ocr',
                'name': '扫描件 OCR',
                'method': 'ocr_pdf',
                'args': {
                    'filePath': '{{input.filePath}}',
                    'outputDir': '{{input.outputDir}}',
                    'outputMode': 'searchable_pdf',
                },
                'onError': 'stop',
            },
            {
                'id': 'word',
                'name': '转换为 Word',
                'method': 'pdf_to_word',
                'args': {
                    'filePath': '{{steps.ocr.pdfOutput}}',
                    'outputDir': '{{input.outputDir}}',
                    'textMode': 'auto',
                },
                'onError': 'stop',
            },
        ],
    },
    {
        'id': 'builtin-image-publish',
        'name': '图片水印 → 压缩',
        'description': '批量添加文字水印，再生成适合分享的压缩副本。',
        'inputExample': {
            'files': ['/path/to/image.png'],
            'outputDir': '/path/to/output',
            'watermarkText': '仅供内部使用',
        },
        'steps': [
            {
                'id': 'watermark',
                'name': '添加水印',
                'method': 'image_add_watermark',
                'args': {
                    'files': '{{input.files}}',
                    'outputDir': '{{input.outputDir}}',
                    'watermarkType': 'text',
                    'text': '{{input.watermarkText}}',
                    'position': 'bottom-right',
                    'opacity': 55,
                },
                'onError': 'stop',
            },
            {
                'id': 'compress',
                'name': '压缩分享副本',
                'method': 'image_batch_compress',
                'args': {
                    'files': '{{steps.watermark.files}}',
                    'outputDir': '{{input.outputDir}}',
                    'mode': 'quality',
                    'quality': 82,
                },
                'onError': 'stop',
            },
        ],
    },
]


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _lookup(context: Dict[str, Any], expression: str) -> Any:
    value: Any = context
    for part in expression.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, (list, tuple)) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ValueError(f'找不到工作流变量：{expression}')
    return _copy(value)


def _resolve(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [_resolve(item, context) for item in value]
    if isinstance(value, dict):
        return {str(key): _resolve(item, context) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    full = _BINDING.fullmatch(value)
    if full:
        return _lookup(context, full.group(1))

    def replace(match: re.Match) -> str:
        resolved = _lookup(context, match.group(1))
        if isinstance(resolved, (dict, list)):
            return json.dumps(resolved, ensure_ascii=False)
        return '' if resolved is None else str(resolved)

    return _BINDING.sub(replace, value)


def _clean_id(value: Any, prefix: str) -> str:
    raw = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(value or '')).strip('-')
    return raw[:80] or f'{prefix}-{uuid.uuid4().hex[:10]}'


class WorkflowMixin:
    """API mixin for v2.3 no-code automation."""

    _workflow_boot_lock = threading.Lock()

    def _workflow_ensure(self) -> None:
        if getattr(self, '_workflow_ready', False):
            return
        with self._workflow_boot_lock:
            if getattr(self, '_workflow_ready', False):
                return
            store_dir = Path(Config.appDataDir) / 'workflows'
            store_dir.mkdir(parents=True, exist_ok=True)
            self._workflow_store_path = store_dir / 'workflows.json'
            self._workflow_lock = threading.RLock()
            self._workflow_stop_event = threading.Event()
            self._workflow_thread = None
            self._workflow_watch_state: Dict[str, Dict[str, Any]] = {}
            self._workflow_data = self._workflow_load()
            self._workflow_ready = True

    def _workflow_load(self) -> Dict[str, Any]:
        empty = {'schemaVersion': 1, 'workflows': [], 'schedules': [], 'watches': [], 'runs': []}
        try:
            payload = json.loads(self._workflow_store_path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            return empty
        if not isinstance(payload, dict):
            return empty
        for key in ('workflows', 'schedules', 'watches', 'runs'):
            if not isinstance(payload.get(key), list):
                payload[key] = []
        payload['schemaVersion'] = 1
        payload['runs'] = payload['runs'][:_MAX_RUNS]
        return payload

    def _workflow_persist_locked(self) -> None:
        temp = self._workflow_store_path.with_suffix('.tmp')
        temp.write_text(json.dumps(self._workflow_data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, self._workflow_store_path)

    @staticmethod
    def _workflow_validate_steps(steps: Any) -> List[Dict[str, Any]]:
        if not isinstance(steps, list) or not steps:
            raise ValueError('工作流至少需要一个步骤')
        clean: List[Dict[str, Any]] = []
        seen = set()
        for index, raw in enumerate(steps, 1):
            if not isinstance(raw, dict):
                raise ValueError(f'第 {index} 个步骤格式不正确')
            method = str(raw.get('method') or '').strip()
            if method not in WORKFLOW_METHODS:
                raise ValueError(f'第 {index} 个步骤方法不在安全白名单：{method}')
            step_id = _clean_id(raw.get('id') or f'step-{index}', 'step')
            if step_id in seen:
                raise ValueError(f'步骤 ID 重复：{step_id}')
            seen.add(step_id)
            args = raw.get('args') or {}
            if not isinstance(args, dict):
                raise ValueError(f'步骤 {step_id} 的参数必须是对象')
            clean.append({
                'id': step_id,
                'name': str(raw.get('name') or method)[:120],
                'method': method,
                'args': _copy(args),
                'onError': 'continue' if raw.get('onError') == 'continue' else 'stop',
            })
        return clean

    @staticmethod
    def _workflow_find(items: Iterable[Dict[str, Any]], item_id: str) -> Dict[str, Any] | None:
        return next((item for item in items if str(item.get('id')) == item_id), None)

    def workflow_methods(self):
        return api_success(methods=sorted(WORKFLOW_METHODS))

    def workflow_templates(self):
        return api_success(templates=_copy(BUILTIN_WORKFLOWS))

    def workflow_list(self):
        try:
            self._workflow_ensure()
            with self._workflow_lock:
                return api_success(
                    workflows=_copy(self._workflow_data['workflows']),
                    schedules=_copy(self._workflow_data['schedules']),
                    watches=_copy(self._workflow_data['watches']),
                    runs=_copy(self._workflow_data['runs']),
                    running=bool(self._workflow_thread and self._workflow_thread.is_alive()),
                )
        except Exception as exc:
            return api_error(f'读取工作流失败：{exc}')

    def workflow_save(self, options: Dict | None = None):
        try:
            self._workflow_ensure()
            options = options or {}
            workflow_id = _clean_id(options.get('id'), 'workflow')
            if workflow_id.startswith('builtin-'):
                workflow_id = f'workflow-{uuid.uuid4().hex[:10]}'
            workflow = {
                'id': workflow_id,
                'name': str(options.get('name') or '未命名工作流').strip()[:120],
                'description': str(options.get('description') or '').strip()[:500],
                'enabled': bool(options.get('enabled', True)),
                'steps': self._workflow_validate_steps(options.get('steps')),
                'inputExample': _copy(options.get('inputExample') or {}),
                'updatedAt': time.time(),
            }
            with self._workflow_lock:
                current = self._workflow_find(self._workflow_data['workflows'], workflow_id)
                if current:
                    workflow['createdAt'] = current.get('createdAt') or workflow['updatedAt']
                    current.clear()
                    current.update(workflow)
                else:
                    workflow['createdAt'] = workflow['updatedAt']
                    self._workflow_data['workflows'].insert(0, workflow)
                self._workflow_persist_locked()
            return api_success('工作流已保存', workflow=_copy(workflow))
        except Exception as exc:
            return api_error(f'保存工作流失败：{exc}')

    def workflow_create_from_template(self, options: Dict | None = None):
        options = options or {}
        template_id = str(options.get('templateId') or '')
        template = self._workflow_find(BUILTIN_WORKFLOWS, template_id)
        if not template:
            return api_error('模板不存在')
        payload = _copy(template)
        payload.pop('id', None)
        payload['name'] = str(options.get('name') or template['name'])
        return self.workflow_save(payload)

    def workflow_delete(self, options: Dict | str | None = None):
        try:
            self._workflow_ensure()
            workflow_id = str(options.get('id') if isinstance(options, dict) else options or '')
            with self._workflow_lock:
                before = len(self._workflow_data['workflows'])
                self._workflow_data['workflows'] = [item for item in self._workflow_data['workflows'] if item.get('id') != workflow_id]
                if len(self._workflow_data['workflows']) == before:
                    return api_error('工作流不存在')
                self._workflow_data['schedules'] = [item for item in self._workflow_data['schedules'] if item.get('workflowId') != workflow_id]
                self._workflow_data['watches'] = [item for item in self._workflow_data['watches'] if item.get('workflowId') != workflow_id]
                self._workflow_persist_locked()
            return api_success('工作流及其触发器已删除')
        except Exception as exc:
            return api_error(f'删除工作流失败：{exc}')

    def workflow_run(self, options: Dict | None = None):
        self._workflow_ensure()
        options = options or {}
        workflow_id = str(options.get('id') or options.get('workflowId') or '')
        with self._workflow_lock:
            workflow = self._workflow_find(self._workflow_data['workflows'], workflow_id)
            if not workflow:
                return api_error('工作流不存在，请先从模板创建或保存')
            workflow = _copy(workflow)
        if not workflow.get('enabled', True):
            return api_error('工作流已停用')

        input_data = options.get('input') or {}
        watch_data = options.get('watch') or {}
        if not isinstance(input_data, dict) or not isinstance(watch_data, dict):
            return api_error('工作流输入必须是对象')
        run_id = uuid.uuid4().hex
        started_at = time.time()
        run = {
            'id': run_id,
            'workflowId': workflow_id,
            'workflowName': workflow.get('name'),
            'trigger': str(options.get('trigger') or 'manual'),
            'status': 'running',
            'startedAt': started_at,
            'endedAt': None,
            'steps': [],
        }
        with self._workflow_lock:
            self._workflow_data['runs'].insert(0, run)
            self._workflow_data['runs'] = self._workflow_data['runs'][:_MAX_RUNS]
            self._workflow_persist_locked()

        context = {'input': _copy(input_data), 'watch': _copy(watch_data), 'steps': {}}
        failed = False
        try:
            for step in workflow['steps']:
                step_started = time.time()
                try:
                    args = _resolve(step['args'], context)
                    handler = getattr(self, step['method'], None)
                    if step['method'] not in WORKFLOW_METHODS or not callable(handler):
                        raise ValueError(f'步骤方法不可用：{step["method"]}')
                    result = handler(args)
                    ok = isinstance(result, dict) and (result.get('code') == 0 or result.get('success') is True)
                    context['steps'][step['id']] = _copy(result)
                    step_run = {
                        'id': step['id'], 'name': step['name'], 'method': step['method'],
                        'status': 'success' if ok else 'failed',
                        'message': str(result.get('msg') or result.get('message') or '') if isinstance(result, dict) else '',
                        'startedAt': step_started, 'endedAt': time.time(), 'result': _copy(result),
                    }
                    run['steps'].append(step_run)
                    if not ok:
                        failed = True
                        if step['onError'] != 'continue':
                            break
                except Exception as exc:
                    failed = True
                    context['steps'][step['id']] = {'code': -1, 'msg': str(exc)}
                    run['steps'].append({
                        'id': step['id'], 'name': step['name'], 'method': step['method'],
                        'status': 'failed', 'message': str(exc),
                        'startedAt': step_started, 'endedAt': time.time(),
                    })
                    if step['onError'] != 'continue':
                        break
        finally:
            run['status'] = 'failed' if failed else 'success'
            run['endedAt'] = time.time()
            with self._workflow_lock:
                stored = self._workflow_find(self._workflow_data['runs'], run_id)
                if stored:
                    stored.clear()
                    stored.update(_copy(run))
                self._workflow_persist_locked()

        if failed:
            return api_error('工作流执行失败，请查看步骤记录', run=_copy(run), context=context)
        return api_success('工作流执行完成', run=_copy(run), context=context)

    def workflow_schedule_save(self, options: Dict | None = None):
        try:
            self._workflow_ensure()
            options = options or {}
            workflow_id = str(options.get('workflowId') or '')
            with self._workflow_lock:
                if not self._workflow_find(self._workflow_data['workflows'], workflow_id):
                    return api_error('工作流不存在')
                schedule_id = _clean_id(options.get('id'), 'schedule')
                minutes = max(1, min(int(options.get('intervalMinutes') or 60), 525_600))
                now = time.time()
                schedule = {
                    'id': schedule_id,
                    'workflowId': workflow_id,
                    'name': str(options.get('name') or '周期任务')[:120],
                    'enabled': bool(options.get('enabled', True)),
                    'intervalMinutes': minutes,
                    'input': _copy(options.get('input') or {}),
                    'lastRunAt': options.get('lastRunAt'),
                    'nextRunAt': float(options.get('nextRunAt') or now + minutes * 60),
                    'updatedAt': now,
                }
                current = self._workflow_find(self._workflow_data['schedules'], schedule_id)
                if current:
                    current.clear()
                    current.update(schedule)
                else:
                    self._workflow_data['schedules'].insert(0, schedule)
                self._workflow_persist_locked()
            return api_success('定时任务已保存', schedule=_copy(schedule))
        except Exception as exc:
            return api_error(f'保存定时任务失败：{exc}')

    def workflow_schedule_delete(self, options: Dict | str | None = None):
        return self._workflow_trigger_delete('schedules', options, '定时任务')

    def workflow_watch_save(self, options: Dict | None = None):
        try:
            self._workflow_ensure()
            options = options or {}
            workflow_id = str(options.get('workflowId') or '')
            directory = Path(str(options.get('path') or '')).expanduser().resolve()
            if not directory.is_dir():
                return api_error('监听目录不存在')
            extensions = options.get('extensions') or []
            if isinstance(extensions, str):
                extensions = [part.strip() for part in extensions.split(',') if part.strip()]
            extensions = sorted({str(item).lower().lstrip('.') for item in extensions if str(item).strip()})
            with self._workflow_lock:
                if not self._workflow_find(self._workflow_data['workflows'], workflow_id):
                    return api_error('工作流不存在')
                watch_id = _clean_id(options.get('id'), 'watch')
                watch = {
                    'id': watch_id,
                    'workflowId': workflow_id,
                    'name': str(options.get('name') or directory.name or '目录监听')[:120],
                    'path': str(directory),
                    'enabled': bool(options.get('enabled', True)),
                    'recursive': bool(options.get('recursive', False)),
                    'extensions': extensions,
                    'debounceSeconds': max(1, min(int(options.get('debounceSeconds') or 3), 3600)),
                    'input': _copy(options.get('input') or {}),
                    'lastEventAt': options.get('lastEventAt'),
                    'updatedAt': time.time(),
                }
                current = self._workflow_find(self._workflow_data['watches'], watch_id)
                if current:
                    current.clear()
                    current.update(watch)
                else:
                    self._workflow_data['watches'].insert(0, watch)
                self._workflow_watch_state.pop(watch_id, None)
                self._workflow_persist_locked()
            return api_success('目录监听已保存', watch=_copy(watch))
        except Exception as exc:
            return api_error(f'保存目录监听失败：{exc}')

    def workflow_watch_delete(self, options: Dict | str | None = None):
        return self._workflow_trigger_delete('watches', options, '目录监听')

    def _workflow_trigger_delete(self, key: str, options: Dict | str | None, label: str):
        try:
            self._workflow_ensure()
            item_id = str(options.get('id') if isinstance(options, dict) else options or '')
            with self._workflow_lock:
                before = len(self._workflow_data[key])
                self._workflow_data[key] = [item for item in self._workflow_data[key] if item.get('id') != item_id]
                if len(self._workflow_data[key]) == before:
                    return api_error(f'{label}不存在')
                self._workflow_watch_state.pop(item_id, None)
                self._workflow_persist_locked()
            return api_success(f'{label}已删除')
        except Exception as exc:
            return api_error(f'删除{label}失败：{exc}')

    def _workflow_submit(self, workflow_id: str, input_data: Dict[str, Any], trigger: str, watch=None) -> None:
        payload = {'id': workflow_id, 'input': input_data, 'trigger': trigger, 'watch': watch or {}}
        submit = getattr(self, 'task_submit', None)
        if callable(submit):
            submit({'method': 'workflow_run', 'args': [payload]})
        else:
            self.workflow_run(payload)

    @staticmethod
    def _workflow_scan(watch: Dict[str, Any]) -> Dict[str, tuple]:
        directory = Path(watch['path'])
        pattern = '**/*' if watch.get('recursive') else '*'
        extensions = set(watch.get('extensions') or [])
        output: Dict[str, tuple] = {}
        try:
            paths = directory.glob(pattern)
            for path in paths:
                if not path.is_file():
                    continue
                if extensions and path.suffix.lower().lstrip('.') not in extensions:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                output[str(path.resolve())] = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return {}
        return output

    def _workflow_tick_schedules(self, now: float) -> None:
        due = []
        with self._workflow_lock:
            for schedule in self._workflow_data['schedules']:
                if schedule.get('enabled') and float(schedule.get('nextRunAt') or 0) <= now:
                    due.append(_copy(schedule))
                    schedule['lastRunAt'] = now
                    schedule['nextRunAt'] = now + int(schedule.get('intervalMinutes') or 60) * 60
            if due:
                self._workflow_persist_locked()
        for schedule in due:
            self._workflow_submit(schedule['workflowId'], schedule.get('input') or {}, f'schedule:{schedule["id"]}')

    def _workflow_tick_watches(self, now: float) -> None:
        with self._workflow_lock:
            watches = _copy(self._workflow_data['watches'])
        for watch in watches:
            if not watch.get('enabled'):
                continue
            current = self._workflow_scan(watch)
            state = self._workflow_watch_state.get(watch['id'])
            if state is None:
                self._workflow_watch_state[watch['id']] = {'snapshot': current, 'pending': {}}
                continue
            previous = state['snapshot']
            pending = state['pending']
            for path, signature in current.items():
                if previous.get(path) != signature:
                    pending[path] = {'signature': signature, 'seenAt': now}
            for path in list(pending):
                candidate = pending[path]
                if path not in current:
                    pending.pop(path, None)
                    continue
                if current[path] != candidate['signature']:
                    pending[path] = {'signature': current[path], 'seenAt': now}
                    continue
                if now - candidate['seenAt'] < int(watch.get('debounceSeconds') or 3):
                    continue
                input_data = _copy(watch.get('input') or {})
                input_data.setdefault('filePath', path)
                input_data.setdefault('files', [path])
                watch_data = {'path': path, 'directory': watch['path'], 'watchId': watch['id']}
                self._workflow_submit(watch['workflowId'], input_data, f'watch:{watch["id"]}', watch_data)
                pending.pop(path, None)
                with self._workflow_lock:
                    stored = self._workflow_find(self._workflow_data['watches'], watch['id'])
                    if stored:
                        stored['lastEventAt'] = now
                        self._workflow_persist_locked()
            state['snapshot'] = current

    def _workflow_loop(self) -> None:
        while not self._workflow_stop_event.wait(1.0):
            try:
                now = time.time()
                self._workflow_tick_schedules(now)
                self._workflow_tick_watches(now)
            except Exception:
                # A malformed or temporarily unavailable watch must not stop all automation.
                continue

    def workflow_start(self):
        try:
            self._workflow_ensure()
            with self._workflow_lock:
                if self._workflow_thread and self._workflow_thread.is_alive():
                    return api_success('自动化服务已在运行', running=True)
                self._workflow_stop_event.clear()
                self._workflow_thread = threading.Thread(target=self._workflow_loop, name='ppx-workflows', daemon=True)
                self._workflow_thread.start()
            return api_success('自动化服务已启动', running=True)
        except Exception as exc:
            return api_error(f'启动自动化服务失败：{exc}')

    def workflow_stop(self):
        if not getattr(self, '_workflow_ready', False):
            return api_success('自动化服务未启动', running=False)
        self._workflow_stop_event.set()
        thread = self._workflow_thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        return api_success('自动化服务已停止', running=False)
