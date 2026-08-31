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

from api.capabilities import CapabilitiesMixin
from api.document_index import DocumentIndexMixin
from api.excel import Excel
from api.file import FileTool
from api.format_center import FormatCenterMixin
from api.image import ImageTool
from api.maintenance import MaintenanceMixin
from api.mindmap.tool import MindMapTool
from api.ocr import OcrMixin
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


class API(
    CapabilitiesMixin,
    FormatCenterMixin,
    TaskMixin,
    WorkflowMixin,
    DocumentIndexMixin,
    MaintenanceMixin,
    OcrMixin,
    System,
    Storage,
    PDF,
    WordTool,
    Excel,
    Seal,
    ImageTool,
    TextTool,
    VideoTool,
    FileTool,
    WebAutoTool,
    MindMapTool,
):
    """业务层API，供前端JS调用"""

    def setWindow(self, window):
        """获取窗口实例"""
        System._window = window
