#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe, persistent workflows, interval schedules and folder watches."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

from api.core.context import TaskCancelled, TaskContext, checkpoint, current_context, report_progress, task_context
from api.core.store import StateStore
from api.core.worker import ISOLATED_PREFIXES, run_in_worker
from api.core.workflow_bindings import BINDING
from api.core.workflow_bindings import resolve as _resolve
from api.utils.error_handler import api_error, api_success
from pyapp.config.config import Config

WORKFLOW_METHODS = {
    'format_center_convert', 'format_center_images_to_pdf', 'format_center_merge_pdfs',
    'image_format_convert', 'image_batch_compress', 'image_crop', 'image_add_watermark',
    'image_rotate_flip', 'image_concat', 'image_batch_rename', 'image_to_pdf', 'ocr_image',
    'pdf_convert_to_images', 'pdf_convert_to_scan', 'pdf_compress', 'pdf_merge', 'pdf_split',
    'pdf_cut', 'pdf_multi_cut', 'pdf_extract_text', 'ocr_pdf', 'pdf_to_word', 'pdf_extract_images',
    'pdf_page_workbench', 'pdf_secure', 'word_split', 'word_cut', 'word_merge',
    'excel_process', 'excel_merge_tables', 'excel_column_profile', 'excel_split_by_column',
    'excel_quality_report',
    'text_format_json', 'text_case_transform', 'text_deduplicate_sort', 'text_batch_replace',
    'video_format_convert', 'video_compress', 'video_cut', 'video_extract_audio', 'video_concat',
    'file_search', 'file_auto_classify', 'file_batch_copy', 'file_batch_rename',
    'file_deduplicate', 'file_deduplicate_report', 'file_compress', 'file_decompress', 'seal_generate',
    'ocr_table', 'document_index_build',
}

_MAX_STEP_RETRIES = 5
_MAX_RETRY_DELAY_SECONDS = 300
_MAX_BUNDLE_BYTES = 2 * 1024 * 1024
_MAX_BUNDLE_WORKFLOWS = 100
_WORKFLOW_BUNDLE_TYPE = 'ppx-workflow-bundle'

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
    {
        'id': 'builtin-image-archive',
        'name': '图片压缩 → 归档',
        'description': '手动运行后保留源图片，生成压缩副本并打包为 ZIP；可在运行前修改输入和输出目录。',
        'inputExample': {'files': [], 'outputDir': '', 'archiveName': '图片分享包'},
        'steps': [
            {
                'id': 'compress', 'name': '压缩分享副本', 'method': 'image_batch_compress',
                'args': {'files': '{{input.files}}', 'outputDir': '{{input.outputDir}}', 'mode': 'quality', 'quality': 82},
                'onError': 'stop', 'onPartial': 'stop',
            },
            {
                'id': 'archive', 'name': '打包压缩副本', 'method': 'file_compress',
                'args': {'items': '{{steps.compress.outputPaths}}', 'outputDir': '{{input.outputDir}}',
                         'archiveName': '{{input.archiveName}}', 'format': 'zip'},
                'onError': 'stop', 'onPartial': 'stop',
            },
        ],
    },
    {
        'id': 'builtin-excel-quality',
        'name': 'Excel 清洗 → 质检报告',
        'description': '手动运行后保留源工作簿，生成去空格、可按列去重的清洗副本，并检查该副本。',
        'inputExample': {'filePath': '', 'outputDir': '', 'headerRow': 1, 'trimText': True, 'deduplicateColumns': []},
        'steps': [
            {
                'id': 'clean', 'name': '生成清洗副本', 'method': 'excel_process',
                'args': {'filePath': '{{input.filePath}}', 'outputDir': '{{input.outputDir}}',
                         'headerRow': '{{input.headerRow}}', 'trimText': '{{input.trimText}}',
                         'deduplicateColumns': '{{input.deduplicateColumns}}', 'exportCombined': True,
                         'exportGroups': False, 'exportJson': False},
                'onError': 'stop', 'onPartial': 'stop',
            },
            {
                'id': 'report', 'name': '检查清洗副本', 'method': 'excel_quality_report',
                'args': {'filePath': '{{steps.clean.combinedPath}}', 'outputDir': '{{input.outputDir}}',
                         'headerRow': 1, 'blankRatioThreshold': 0.5},
                'onError': 'stop', 'onPartial': 'stop',
            },
        ],
    },
    {
        'id': 'builtin-text-clean-format',
        'name': '文本去重 → 统一格式',
        'description': '逐行清除首尾空格和重复内容，再统一大小写或命名格式；结果可在运行记录中查看和复制。',
        'inputExample': {'content': '', 'mode': 'upper'},
        'steps': [
            {'id': 'clean', 'name': '逐行清理文本', 'method': 'text_deduplicate_sort',
             'args': {'content': '{{input.content}}', 'operation': 'deduplicate', 'trimWhitespace': True,
                      'keepEmpty': False, 'caseSensitive': True}, 'onError': 'stop', 'onPartial': 'stop'},
            {'id': 'format', 'name': '统一文本格式', 'method': 'text_case_transform',
             'args': {'content': '{{steps.clean.result}}', 'mode': '{{input.mode}}'},
             'onError': 'stop', 'onPartial': 'stop'},
        ],
    },
    {
        'id': 'builtin-search-archive',
        'name': '搜索文档 → 保留目录归档',
        'description': '按名称和扩展名搜索文档，再按来源相对路径打包；搜索不完整时停止，自动排除所选输出目录。',
        'inputExample': {'directory': '', 'outputDir': '', 'keyword': '',
                         'extensions': ['pdf', 'docx', 'xlsx', 'txt'], 'recursive': True,
                         'limit': 500, 'archiveName': '文档归档'},
        'steps': [
            {'id': 'search', 'name': '搜索要归档的文档', 'method': 'file_search',
             'args': {'directory': '{{input.directory}}', 'keyword': '{{input.keyword}}',
                      'extensions': '{{input.extensions}}', 'recursive': '{{input.recursive}}',
                      'limit': '{{input.limit}}', 'excludeDirectory': '{{input.outputDir}}'},
             'onError': 'stop', 'onPartial': 'stop'},
            {'id': 'archive', 'name': '按相对路径归档', 'method': 'file_compress',
             'args': {'items': '{{steps.search.outputPaths}}', 'format': 'zip',
                      'baseDir': '{{input.directory}}', 'outputDir': '{{input.outputDir}}',
                      'archiveName': '{{input.archiveName}}'}, 'onError': 'stop', 'onPartial': 'stop'},
        ],
    },
    {
        'id': 'builtin-duplicate-report',
        'name': '重复文件扫描 → 核对报告',
        'description': '按内容比较候选，完整扫描后导出 Excel 核对报告；排除报告目录，不删除来源文件。',
        'inputExample': {'directory': '', 'outputDir': '', 'extensions': [], 'recursive': True, 'limit': 5000},
        'steps': [
            {'id': 'scan', 'name': '比较重复内容', 'method': 'file_deduplicate',
             'args': {'directory': '{{input.directory}}', 'mode': 'content', 'extensions': '{{input.extensions}}',
                      'recursive': '{{input.recursive}}', 'limit': '{{input.limit}}',
                      'excludeDirectory': '{{input.outputDir}}'}, 'onError': 'stop', 'onPartial': 'stop'},
            {'id': 'report', 'name': '导出核对报告', 'method': 'file_deduplicate_report',
             'args': {'groups': '{{steps.scan.groups}}', 'summary': '{{steps.scan.summary}}',
                      'outputDir': '{{input.outputDir}}'}, 'onError': 'stop', 'onPartial': 'stop'},
        ],
    },
]


def _copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _clean_id(value: Any, prefix: str) -> str:
    raw = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(value or '')).strip('-')
    return raw[:80] or f'{prefix}-{uuid.uuid4().hex[:10]}'


def _recorded_input_count(result):
    """Empty legacy records mean unknown; they do not prove zero work occurred."""
    inputs = [item.get('input') for item in result.get('itemResults', []) if item.get('input')]
    if not inputs and (result.get('code') == 0 or result.get('success') is True):
        inputs = result.get('inputItems')
    if not isinstance(inputs, list) or not inputs:
        return None
    paths = {str(item.get('path') if isinstance(item, dict) else item) for item in inputs}
    return len(paths)


def _depends_on_rerun(value, rerun_ids):
    if isinstance(value, dict):
        return any(_depends_on_rerun(item, rerun_ids) for item in value.values())
    if isinstance(value, list):
        return any(_depends_on_rerun(item, rerun_ids) for item in value)
    if isinstance(value, str):
        for match in BINDING.finditer(value):
            parts = match.group(1).split('.')
            if parts[0] == 'steps' and (len(parts) == 1 or parts[1] in rerun_ids):
                return bool(rerun_ids)
    return False


class WorkflowMixin:
    """API mixin for persistent no-code automation."""

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
            self._workflow_store = StateStore(Config.appDataDir)
            self._workflow_lock = threading.RLock()
            self._workflow_stop_event = threading.Event()
            self._workflow_thread = None
            self._workflow_watch_state: Dict[str, Dict[str, Any]] = {}
            self._workflow_data = self._workflow_load()
            self._workflow_generated_paths = set(self._workflow_data.get('generatedPaths', []))
            self._workflow_ready = True

    def _workflow_load(self) -> Dict[str, Any]:
        empty = {'schemaVersion': 1, 'workflows': [], 'schedules': [], 'watches': [], 'runs': []}
        payload = self._workflow_store.load('workflows', self._workflow_store_path, empty)
        if not isinstance(payload, dict):
            return empty
        for key in ('workflows', 'schedules', 'watches', 'runs'):
            if not isinstance(payload.get(key), list):
                payload[key] = []
        payload['schemaVersion'] = 1
        interrupted = False
        for run in payload['runs']:
            if run.get('status') == 'running':
                run.update(status='interrupted', endedAt=time.time())
                interrupted = True
        # Older versions registered query source files as newly generated files.
        # Repair identities supported by retained history without touching files
        # or dropping paths also known to have been written by real operations.
        if not payload.get('querySourceExclusionFixed'):
            import os

            from api.operations import QUERY_METHODS
            queried, generated = set(), set()
            for run in payload['runs']:
                for step in run.get('steps', []):
                    identities = queried if step.get('method') in QUERY_METHODS else generated
                    identities.update(os.path.normcase(os.path.abspath(asset['path']))
                                      for asset in (step.get('result') or {}).get('outputAssets', []) if asset.get('path'))
            sources = queried - generated
            payload['generatedPaths'] = [path for path in payload.get('generatedPaths', [])
                                         if os.path.normcase(os.path.abspath(path)) not in sources]
            payload['querySourceExclusionFixed'] = True
            interrupted = True
        if interrupted:
            self._workflow_store.save('workflows', payload)
        return payload

    def _workflow_persist_locked(self) -> None:
        self._workflow_data['generatedPaths'] = sorted(getattr(self, '_workflow_generated_paths', set()))[-10000:]
        self._workflow_store.save('workflows', self._workflow_data)

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
            try:
                retry_count = max(0, min(int(raw.get('retryCount') or raw.get('retries') or 0), _MAX_STEP_RETRIES))
                retry_delay_value = float(raw.get('retryDelaySeconds') or 0)
                if not math.isfinite(retry_delay_value):
                    raise ValueError('重试延迟必须是有限数值')
                retry_delay = max(
                    0.0,
                    min(retry_delay_value, _MAX_RETRY_DELAY_SECONDS),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f'步骤 {step_id} 的重试配置无效') from exc
            clean.append({
                'id': step_id,
                'name': str(raw.get('name') or method)[:120],
                'method': method,
                'args': _copy(args),
                'onError': 'continue' if raw.get('onError') == 'continue' else 'stop',
                'onPartial': 'stop' if raw.get('onPartial') == 'stop' else 'continue',
                'retryCount': retry_count,
                'retryDelaySeconds': retry_delay,
            })
        return clean

    @staticmethod
    def _workflow_find(items: Iterable[Dict[str, Any]], item_id: str) -> Dict[str, Any] | None:
        return next((item for item in items if str(item.get('id')) == item_id), None)

    def workflow_methods(self):
        return api_success(methods=sorted(WORKFLOW_METHODS))

    def workflow_templates(self):
        return api_success(templates=_copy(BUILTIN_WORKFLOWS))

    def workflow_preflight(self, options: Dict | None = None):
        """Validate a prospective manual run without touching workflow state or files."""
        try:
            from api.core.workflow_preflight import preflight
            report = preflight({} if options is None else options, self._workflow_validate_steps)
            return api_success('预检完成' if report['valid'] else '预检发现问题', **report)
        except Exception:
            return api_error('检查配置失败，请核对参数的数据结构', errorCode='PREFLIGHT_ERROR')

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

    def workflow_runs_clear(self, options: Dict | None = None):
        """Preview or clear selected completed workflow run records."""
        try:
            self._workflow_ensure()
            options = options or {}
            raw_statuses = options.get('statuses') if options.get('statuses') is not None else options.get('status')
            statuses_supplied = raw_statuses is not None
            if isinstance(raw_statuses, str):
                raw_statuses = [item.strip() for item in raw_statuses.split(',') if item.strip()]
            statuses = {str(item) for item in (raw_statuses if statuses_supplied else ('success', 'failed'))} & {'success', 'failed'}
            if not statuses:
                return api_error('请选择成功或失败的运行状态')
            ids_supplied = options.get('ids') is not None
            raw_ids = options.get('ids') or []
            if isinstance(raw_ids, str):
                raw_ids = [raw_ids]
            ids = {str(item) for item in raw_ids if str(item).strip()}
            workflow_id = str(options.get('workflowId') or '')
            trigger = str(options.get('trigger') or '')
            try:
                before = float(options.get('before') or 0)
            except (TypeError, ValueError):
                return api_error('清理时间无效')
            with self._workflow_lock:
                removable = []
                for run in self._workflow_data['runs']:
                    run_id = str(run.get('id') or '')
                    if run.get('status') not in statuses:
                        continue
                    if ids_supplied and run_id not in ids:
                        continue
                    if workflow_id and str(run.get('workflowId') or '') != workflow_id:
                        continue
                    if trigger and trigger not in str(run.get('trigger') or ''):
                        continue
                    ended_at = run.get('endedAt') or run.get('startedAt') or 0
                    if before and (not isinstance(ended_at, (int, float)) or ended_at >= before):
                        continue
                    removable.append(run_id)
                if options.get('dryRun'):
                    return api_success('运行记录清理预览已生成', removableCount=len(removable), removableIds=removable)
                removable_set = set(removable)
                self._workflow_data['runs'] = [
                    run for run in self._workflow_data['runs'] if str(run.get('id') or '') not in removable_set
                ]
                self._workflow_persist_locked()
            return api_success(
                f'已清除 {len(removable)} 条工作流运行记录',
                removedCount=len(removable),
                removedIds=removable,
            )
        except Exception as exc:
            return api_error(f'清理工作流运行记录失败：{exc}')

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

    def workflow_bundle_export(self, options: Dict | None = None):
        """Export reusable workflow definitions without schedules, watches or run history."""
        try:
            self._workflow_ensure()
            options = options or {}
            ids_supplied = options.get('ids') is not None
            raw_ids = options.get('ids') or []
            if isinstance(raw_ids, str):
                raw_ids = [raw_ids]
            selected_ids = {str(item) for item in raw_ids if str(item).strip()}
            if ids_supplied and not selected_ids:
                return api_error('请选择至少一个要导出的工作流')
            with self._workflow_lock:
                selected = [
                    _copy(item)
                    for item in self._workflow_data['workflows']
                    if not ids_supplied or str(item.get('id')) in selected_ids
                ]
            if not selected:
                return api_error('没有可导出的工作流')
            output_raw = str(options.get('outputDir') or Config.downloadDir or (Path(Config.appDataDir) / 'exports'))
            output_dir = Path(output_raw).expanduser().resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            target = output_dir / f'PPX_workflows_{timestamp}.json'
            index = 2
            while target.exists() or target.is_symlink():
                target = output_dir / f'PPX_workflows_{timestamp}_{index}.json'
                index += 1
            workflows = []
            for item in selected:
                workflows.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'description': item.get('description'),
                    'enabled': item.get('enabled', True),
                    'steps': item.get('steps') or [],
                    'inputExample': item.get('inputExample') or {},
                })
            bundle = {
                'type': _WORKFLOW_BUNDLE_TYPE,
                'schemaVersion': 1,
                'appVersion': Config.appVersion,
                'exportedAt': time.time(),
                'workflows': workflows,
            }
            temp = target.with_name(f'.{target.name}.{uuid.uuid4().hex}.tmp')
            with temp.open('w', encoding='utf-8') as handle:
                json.dump(bundle, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, target)
            return api_success('工作流模板包已导出', output=str(target), workflowCount=len(workflows))
        except Exception as exc:
            if 'temp' in locals():
                temp.unlink(missing_ok=True)
            return api_error(f'导出工作流模板包失败：{exc}')

    def workflow_bundle_import(self, options: Dict | None = None):
        """Validate and import a versioned local workflow bundle."""
        try:
            self._workflow_ensure()
            options = options or {}
            source = Path(str(options.get('filePath') or '')).expanduser().resolve()
            if not source.is_file() or source.suffix.lower() != '.json':
                return api_error('请选择 PPX 工作流 JSON 模板包')
            if source.stat().st_size > _MAX_BUNDLE_BYTES:
                return api_error('工作流模板包超过 2 MB 安全上限')
            bundle = json.loads(source.read_text(encoding='utf-8'))
            if not isinstance(bundle, dict) or bundle.get('type') != _WORKFLOW_BUNDLE_TYPE:
                return api_error('不是有效的 PPX 工作流模板包')
            if int(bundle.get('schemaVersion') or 0) != 1:
                return api_error('工作流模板包版本不受支持')
            raw_workflows = bundle.get('workflows')
            if not isinstance(raw_workflows, list) or not raw_workflows:
                return api_error('模板包不包含工作流')
            if len(raw_workflows) > _MAX_BUNDLE_WORKFLOWS:
                return api_error(f'单次最多导入 {_MAX_BUNDLE_WORKFLOWS} 个工作流')

            with self._workflow_lock:
                used_ids = {str(item.get('id')) for item in self._workflow_data['workflows']}
                imported = []
                renamed = 0
                now = time.time()
                for index, raw in enumerate(raw_workflows, 1):
                    if not isinstance(raw, dict):
                        raise ValueError(f'第 {index} 个工作流格式不正确')
                    workflow_id = _clean_id(raw.get('id'), 'workflow')
                    if workflow_id.startswith('builtin-') or workflow_id in used_ids:
                        workflow_id = f'workflow-{uuid.uuid4().hex[:10]}'
                        renamed += 1
                    used_ids.add(workflow_id)
                    input_example = raw.get('inputExample') or {}
                    if not isinstance(input_example, dict):
                        raise ValueError(f'第 {index} 个工作流的输入示例必须是对象')
                    imported.append({
                        'id': workflow_id,
                        'name': str(raw.get('name') or f'导入工作流 {index}').strip()[:120],
                        'description': str(raw.get('description') or '').strip()[:500],
                        'enabled': bool(raw.get('enabled', True)),
                        'steps': self._workflow_validate_steps(raw.get('steps')),
                        'inputExample': _copy(input_example),
                        'createdAt': now,
                        'updatedAt': now,
                    })
                previous_workflows = self._workflow_data['workflows']
                self._workflow_data['workflows'] = imported + previous_workflows
                try:
                    self._workflow_persist_locked()
                except Exception:
                    self._workflow_data['workflows'] = previous_workflows
                    raise
            return api_success(
                f'已导入 {len(imported)} 个工作流',
                workflows=_copy(imported),
                importedCount=len(imported),
                renamedCount=renamed,
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return api_error(f'导入工作流模板包失败：{exc}')
        except Exception as exc:
            return api_error(f'导入工作流模板包失败：{exc}')

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

    @staticmethod
    def _workflow_result_ok(result: Any) -> bool:
        return isinstance(result, dict) and (result.get('code') == 0 or result.get('success') is True)

    def _workflow_execute_step(self, step: Dict[str, Any], context: Dict[str, Any], previous=None):
        from api.operations import QUERY_METHODS
        generates_files = step['method'] not in QUERY_METHODS
        step_started = time.time()
        attempts = []
        result: Any = None
        ok = False
        canceled = False
        resume_info = {'processedInputCount': None, 'retainedInputCount': None,
                       'retainedOutputCount': None} if previous else None
        try:
            args = _resolve(step['args'], context)
            if previous and isinstance(args, dict):
                from api.operations import OPERATIONS
                descriptor = OPERATIONS.get(step['method'])
                batch_key = descriptor.batchKey if descriptor else None
                if step['method'] == 'format_center_convert':
                    batch_key = 'files'
                completed = {item.get('input') for item in previous.get('itemResults', []) if item.get('status') in {'success', 'skipped'}}
                if batch_key and isinstance(args.get(batch_key), list):
                    original_batch = args[batch_key]
                    args[batch_key] = [item for item in args[batch_key] if (item.get('path') if isinstance(item, dict) else item) not in completed]
                    resume_info['retainedInputCount'] = len({str(item.get('path') if isinstance(item, dict) else item) for item in original_batch
                                                             if (item.get('path') if isinstance(item, dict) else item) in completed})
                elif step['method'] in {'file_batch_copy', 'file_batch_delete', 'file_batch_rename', 'file_auto_classify'} and previous.get('inputItems'):
                    args['_retryInputs'] = [path for path in previous['inputItems'] if path not in completed]
                    args['_inputOrder'] = {path: index for index, path in enumerate(previous['inputItems'])}
                    resume_info['retainedInputCount'] = len(set(previous['inputItems']) & completed)
            handler = getattr(self, step['method'], None)
            if step['method'] not in WORKFLOW_METHODS or not callable(handler):
                raise ValueError(f'步骤方法不可用：{step["method"]}')
            retry_count = int(step.get('retryCount') or 0)
            retry_delay = float(step.get('retryDelaySeconds') or 0)
            for attempt_index in range(retry_count + 1):
                checkpoint()
                attempt_started = time.time()
                try:
                    parent_context = current_context() or TaskContext()

                    def report_step(payload):
                        asset = payload.get('outputAsset')
                        if asset:
                            if not any(item['path'] == asset['path'] for item in parent_context.outputs):
                                parent_context.outputs.append(asset)
                            if generates_files:
                                with self._workflow_lock:
                                    self._workflow_generated_paths.add(str(Path(asset['path']).resolve()))
                                    self._workflow_persist_locked()
                        parent_context.emit(**payload)

                    child_context = TaskContext(cancel=parent_context.cancel, callback=report_step)
                    if getattr(self, '_host', None) and step['method'].startswith(ISOLATED_PREFIXES):
                        result = run_in_worker(step['method'], [args], child_context)
                    else:
                        with task_context(child_context):
                            result = handler(args)
                    if isinstance(result, dict):
                        result.setdefault('itemResults', child_context.item_results)
                        result.setdefault('inputItems', child_context.input_items)
                    checkpoint()
                    if generates_files and isinstance(result, dict):
                        with self._workflow_lock:
                            self._workflow_generated_paths.update(str(Path(asset['path']).resolve()) for asset in result.get('outputAssets', []))
                    ok = self._workflow_result_ok(result)
                    message = (
                        str(result.get('msg') or result.get('message') or '')
                        if isinstance(result, dict)
                        else ''
                    )
                except TaskCancelled:
                    raise
                except Exception as exc:
                    result = {'code': -1, 'msg': str(exc)}
                    ok = False
                    message = str(exc)
                attempts.append({
                    'attempt': attempt_index + 1,
                    'status': 'success' if ok else 'failed',
                    'message': message,
                    'startedAt': attempt_started,
                    'endedAt': time.time(),
                })
                if ok:
                    break
                if attempt_index < retry_count and retry_delay:
                    active_context = current_context()
                    if active_context:
                        active_context.cancel.wait(retry_delay)
                        checkpoint()
                    else:
                        time.sleep(retry_delay)
        except TaskCancelled as exc:
            canceled = True
            result = {'code': -1, 'msg': str(exc), 'errorCode': 'CANCELED'}
            attempts.append({'attempt': len(attempts) + 1, 'status': 'canceled', 'message': str(exc),
                             'startedAt': step_started, 'endedAt': time.time()})
        except Exception as exc:
            result = {'code': -1, 'msg': str(exc)}
            attempts.append({
                'attempt': 1,
                'status': 'failed',
                'message': str(exc),
                'startedAt': step_started,
                'endedAt': time.time(),
            })

        message = (
            str(result.get('msg') or result.get('message') or '')
            if isinstance(result, dict)
            else ''
        )
        if previous and isinstance(result, dict) and generates_files:
            from api.operations import enrich_result
            resume_info['processedInputCount'] = _recorded_input_count(result)
            retained = [asset for asset in previous.get('outputAssets', []) if Path(asset['path']).exists()]
            newly_generated = {asset['path'] for asset in result.get('outputAssets', [])}
            result['outputAssets'] = list({asset['path']: asset for asset in [*retained, *result.get('outputAssets', [])]}.values())
            result['itemResults'] = list({item['input']: item for item in [*previous.get('itemResults', []), *result.get('itemResults', [])] if item.get('input')}.values())
            result = enrich_result(step['method'], result)
            retained_paths = {asset.get('path') for asset in retained if asset.get('path')} - newly_generated
            resume_info['retainedOutputCount'] = len(retained_paths & {asset.get('path') for asset in result.get('outputAssets', [])})
        elif previous and isinstance(result, dict):
            # Queries describe this scan, not a cumulative set of past matches.
            resume_info.update(processedInputCount=_recorded_input_count(result), retainedInputCount=0, retainedOutputCount=0)
        step_run = {
            'id': step['id'],
            'name': step['name'],
            'method': step['method'],
            'status': 'canceled' if canceled else 'partial' if ok and result.get('partial') else 'success' if ok else 'failed',
            'message': message,
            'startedAt': step_started,
            'endedAt': time.time(),
            'result': _copy(result),
            'attemptCount': len(attempts),
            'attempts': attempts,
        }
        if resume_info is not None:
            step_run['resumeInfo'] = resume_info
        return step_run, result, ok

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
        signature = hashlib.sha256(json.dumps(workflow['steps'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        resume_steps = {}
        if options.get('_resumeRunId'):
            with self._workflow_lock:
                previous_run = self._workflow_find(self._workflow_data['runs'], options['_resumeRunId'])
                previous_run = _copy(previous_run) if previous_run else None
            if not previous_run or previous_run.get('workflowId') != workflow_id:
                return api_error('找不到可重试的工作流记录')
            if previous_run.get('stepsSignature') != signature:
                return api_error('工作流步骤已修改，请使用当前版本重新运行')
            resume_steps = {step['id']: step for step in previous_run.get('steps', [])}
            if any(not Path(asset['path']).exists() for step in resume_steps.values()
                   for asset in step.get('result', {}).get('outputAssets', [])):
                return api_error('先前的结果文件已移动或删除，请重新运行工作流')

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
            'stepsSignature': signature,
        }
        if options.get('_resumeRunId'):
            run['resumeOfRunId'] = str(options['_resumeRunId'])
        with self._workflow_lock:
            self._workflow_data['runs'].insert(0, _copy(run))
            self._workflow_persist_locked()

        context = {'input': _copy(input_data), 'watch': _copy(watch_data), 'steps': {}}
        if current_context():
            current_context().emit(workflowRunId=run_id)
        failed = False
        partial = False
        rerun_ids = set()
        try:
            for step_index, step in enumerate(workflow['steps']):
                report_progress(step_index, len(workflow['steps']), f'执行步骤：{step["name"]}')
                previous = resume_steps.get(step['id'])
                dependency_rerun = bool(previous and _depends_on_rerun(step['args'], rerun_ids))
                if previous and previous['status'] == 'success' and not dependency_rerun:
                    step_run, result, ok = {**previous, 'reused': True, 'resumeInfo': {
                        'processedInputCount': 0, 'retainedInputCount': _recorded_input_count(previous['result']),
                        'retainedOutputCount': len({asset['path'] for asset in previous['result']['outputAssets']}) if 'outputAssets' in previous['result'] else None,
                    }}, _copy(previous['result']), True
                else:
                    step_run, result, ok = self._workflow_execute_step(step, context, previous.get('result') if previous and not dependency_rerun else None)
                    rerun_ids.add(step['id'])
                if previous:
                    info = step_run.setdefault('resumeInfo', {'processedInputCount': None, 'retainedInputCount': None, 'retainedOutputCount': None})
                    info.update(sourceRunId=run['resumeOfRunId'], reusedStep=bool(step_run.get('reused')))
                    if dependency_rerun:
                        info.update(processedInputCount=_recorded_input_count(result), retainedInputCount=0,
                                    retainedOutputCount=0, reason='前序依赖已重新执行，本步骤使用当前结果重新生成')
                context['steps'][step['id']] = _copy(result)
                run['steps'].append(step_run)
                with self._workflow_lock:
                    stored = self._workflow_find(self._workflow_data['runs'], run_id)
                    if stored:
                        stored.update(_copy(run))
                    self._workflow_persist_locked()
                checkpoint()
                partial = partial or step_run['status'] == 'partial'
                if step_run['status'] == 'partial' and step.get('onPartial') == 'stop':
                    break
                if not ok:
                    failed = True
                    if step['onError'] != 'continue':
                        break
        except TaskCancelled:
            failed = True
            run['status'] = 'canceled'
        except Exception:
            failed = True
            raise
        finally:
            partial = partial or (failed and any(step['status'] in {'success', 'partial'} for step in run['steps']))
            run['status'] = 'canceled' if run['status'] == 'canceled' else 'partial' if partial else 'failed' if failed else 'success'
            run['endedAt'] = time.time()
            with self._workflow_lock:
                stored = self._workflow_find(self._workflow_data['runs'], run_id)
                if stored:
                    stored.clear()
                    stored.update(_copy(run))
                self._workflow_persist_locked()

        assets = list({asset['path']: asset for step in run['steps'] for asset in step.get('result', {}).get('outputAssets', [])}.values())
        if run['status'] == 'canceled':
            return api_error('工作流已取消，已完成的结果已保留', run=_copy(run), context=context, outputAssets=assets, errorCode='CANCELED')
        if partial:
            return api_success('工作流部分成功，请查看步骤记录', run=_copy(run), context=context, outputAssets=assets, partial=True)
        if failed:
            return api_error('工作流执行失败，请查看步骤记录', run=_copy(run), context=context, outputAssets=assets)
        return api_success('工作流执行完成', run=_copy(run), context=context, outputAssets=assets)

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

    @staticmethod
    def _workflow_trigger_key(kind: str) -> str:
        key = {'schedule': 'schedules', 'watch': 'watches'}.get(kind)
        if not key:
            raise ValueError('触发器类型必须是 schedule 或 watch')
        return key

    def workflow_trigger_set_enabled(self, options: Dict | None = None):
        try:
            self._workflow_ensure()
            options = options or {}
            kind = str(options.get('kind') or '')
            key = self._workflow_trigger_key(kind)
            item_id = str(options.get('id') or '')
            with self._workflow_lock:
                trigger = self._workflow_find(self._workflow_data[key], item_id)
                if not trigger:
                    return api_error('触发器不存在')
                trigger['enabled'] = bool(options.get('enabled', True))
                trigger['updatedAt'] = time.time()
                if kind == 'watch':
                    self._workflow_watch_state.pop(item_id, None)
                self._workflow_persist_locked()
                snapshot = _copy(trigger)
            return api_success('触发器已启用' if snapshot['enabled'] else '触发器已停用', trigger=snapshot)
        except Exception as exc:
            return api_error(f'更新触发器失败：{exc}')

    def workflow_trigger_run_now(self, options: Dict | None = None):
        try:
            self._workflow_ensure()
            options = options or {}
            kind = str(options.get('kind') or '')
            key = self._workflow_trigger_key(kind)
            item_id = str(options.get('id') or '')
            now = time.time()
            with self._workflow_lock:
                trigger = self._workflow_find(self._workflow_data[key], item_id)
                if not trigger:
                    return api_error('触发器不存在')
                snapshot = _copy(trigger)
            watch_data = {}
            if kind == 'watch':
                watch_data = {'directory': snapshot.get('path'), 'watchId': snapshot['id']}
            submission = self._workflow_submit(
                snapshot['workflowId'],
                snapshot.get('input') or {},
                f'manual:{kind}:{snapshot["id"]}',
                watch_data,
            )
            accepted = self._workflow_result_ok(submission)
            with self._workflow_lock:
                stored = self._workflow_find(self._workflow_data[key], item_id)
                if stored:
                    stored['lastRunAt' if kind == 'schedule' else 'lastEventAt'] = now
                    stored['lastError'] = '' if accepted else str((submission or {}).get('msg') or '提交失败')
                    self._workflow_persist_locked()
            if not accepted:
                return api_error(
                    str((submission or {}).get('msg') or '立即运行失败'),
                    submission=_copy(submission),
                )
            return api_success('触发器已提交运行', submission=_copy(submission))
        except Exception as exc:
            return api_error(f'立即运行触发器失败：{exc}')

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

    def _workflow_submit(self, workflow_id: str, input_data: Dict[str, Any], trigger: str, watch=None):
        payload = {'id': workflow_id, 'input': input_data, 'trigger': trigger, 'watch': watch or {}}
        submit = getattr(self, 'task_submit', None)
        if callable(submit):
            return submit({'method': 'workflow_run', 'args': [payload]})
        return self.workflow_run(payload)

    @staticmethod
    def _workflow_scan(watch: Dict[str, Any]) -> Dict[str, tuple]:
        directory = Path(watch['path'])
        pattern = '**/*' if watch.get('recursive') else '*'
        extensions = set(watch.get('extensions') or [])
        output: Dict[str, tuple] = {}
        try:
            paths = directory.glob(pattern)
            for path in paths:
                if any(part.startswith('.') or part in {'node_modules', '__pycache__'} for part in path.relative_to(directory).parts):
                    continue
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
            current = {path: signature for path, signature in current.items() if path not in self._workflow_generated_paths}
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
