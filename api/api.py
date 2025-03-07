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


class API(System, Storage):
    '''业务层API，供前端JS调用'''

    def setWindow(self, window):
        '''获取窗口实例'''
        System._window = window
    #     # 注入JavaScript以监听快捷键
    #     js = """
    #             document.addEventListener('keydown', function(event) {
    #                 if (event.ctrlKey && event.shiftKey && event.key === 'H') {
    #                     window.pywebview.api.trigger_hotkey();
    #                 }
    #             });
    #             """
    #     window.evaluate_js(js)
    #
    # def trigger_hotkey(self):
    #     self.on_hotkey_pressed()
    #
    # def on_hotkey_pressed(self):
    #     print("快捷键被触发!")