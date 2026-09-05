#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: 潘高
LastEditors: 潘高
Date: 2022-03-21 17:01:39
LastEditTime: 2024-09-08 20:28:48
Description: 业务层API，供前端JS调用
usage: 在Javascript中调用window.pywebview.api.<methodname>(<parameters>)
"""

import inspect
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from api.capabilities import CapabilitiesMixin
from api.document_index import DocumentIndexMixin
from api.excel import Excel
from api.file import FileTool
from api.format_center import FormatCenterMixin
from api.image import ImageTool
from api.maintenance import MaintenanceMixin
from api.ocr import OcrMixin
from api.operations import OperationService, enrich_result
from api.pdf import PDF
from api.seal import Seal
from api.storage import Storage
from api.system import System
from api.tasks import TaskMixin
from api.text import TextTool
from api.video import VideoTool
from api.webauto import WebAutoTool
from api.word import WordTool
from api.workflow import WorkflowMixin

SERVICE_TYPES = (
    OperationService,
    CapabilitiesMixin, FormatCenterMixin, TaskMixin, WorkflowMixin,
    DocumentIndexMixin, MaintenanceMixin, OcrMixin, System, Storage,
    PDF, WordTool, Excel, Seal, ImageTool, TextTool, VideoTool, FileTool, WebAutoTool,
)


def _bridge_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _bridge_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_bridge_value(item) for item in value]
    return value


class _HostAccess:
    """Only explicit public calls can cross service boundaries, never helpers."""

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self._host, name)


class API:
    """Desktop bridge. Each domain owns its helpers and mutable state."""

    def __init__(self):
        self._services = {}
        for service_type in SERVICE_TYPES:
            bound_type = type(f'Hosted{service_type.__name__}', (_HostAccess, service_type), {})
            service = bound_type()
            service._host = self
            self._services[service_type] = service
        self._services[CapabilitiesMixin]._wa_chromium_installed = self._services[WebAutoTool]._wa_chromium_installed

    def setWindow(self, window):
        """获取窗口实例"""
        System._window = window


def _delegate(service_type, name, method):
    @wraps(method)
    def call(self, *args, **kwargs):
        return _bridge_value(enrich_result(name, getattr(self._services[service_type], name)(*args, **kwargs)))
    # pywebview reads getfullargspec to generate JavaScript function declarations.
    call.__signature__ = inspect.signature(method)
    return call


for _service_type in SERVICE_TYPES:
    for _name, _method in inspect.getmembers(_service_type, inspect.isfunction):
        if _name.startswith('_'):
            continue
        if hasattr(API, _name):
            raise RuntimeError(f'Duplicate desktop operation: {_name}')
        setattr(API, _name, _delegate(_service_type, _name, _method))
