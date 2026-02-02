#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2022-03-21 17:01:39
LastEditTime: 2024-09-08 20:28:48
Description: 业务层API，供前端JS调用
usage: 在Javascript中调用window.pywebview.api.<methodname>(<parameters>)
'''

from api.storage import Storage
from api.system import System
from api.pdf import PDF
from api.excel import Excel
from api.seal import Seal
from api.image import ImageTool
from api.text import TextTool
from api.video import VideoTool
from api.file import FileTool
from api.finance import FinanceTool
from api.automation import AutomationTool


class API(System, Storage, PDF, Excel, Seal, ImageTool, TextTool, VideoTool, FileTool, FinanceTool, AutomationTool):
    '''业务层API，供前端JS调用'''

    def setWindow(self, window):
        '''获取窗口实例'''
        System._window = window
