#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2022-03-23 15:41:46
LastEditTime: 2024-09-08 20:29:41
Description: 生成客户端主程序
usage: 运行前，请确保本机已经搭建Python3开发环境，且已经安装 pywebview 模块。
'''

import argparse
import mimetypes
import os
import sys
import keyboard
import platform
import webview
import threading
import time

from api.api import API
from pyapp.config.config import Config
from pyapp.db.db import DB

cfg = Config()    # 配置
db = DB()    # 数据库类
api = API()    # 本地接口

cfg.init()

# 全局变量存储窗口实例和状态
global_window = None
window_shown = True  # 用于跟踪窗口状态

def reset_top_after_delay():
    """延迟取消窗口置顶"""
    time.sleep(0.1)  # 等待100毫秒
    if global_window:
        global_window.on_top = False

def toggle_window_visibility():
    """切换窗口显示/隐藏状态"""
    global window_shown
    if global_window:
        if window_shown:
            global_window.hide()
            window_shown = False
        else:
            # 显示窗口并临时置顶
            global_window.show()
            global_window.on_top = True
            # 创建新线程来延迟取消置顶
            threading.Thread(target=reset_top_after_delay, daemon=True).start()
            window_shown = True

def setup_global_hotkey():
    """设置全局快捷键"""
    system = platform.system()
    if system == 'Darwin':  # macOS
        # macOS 上使用 Option(Alt) + Shift + Q
        keyboard.add_hotkey('alt+shift+q', toggle_window_visibility)
    else:  # Windows 和 Linux
        # Windows 和 Linux 上使用 Alt + Shift + Q
        keyboard.add_hotkey('alt+shift+q', toggle_window_visibility)

def on_shown():
    # print('程序启动')
    db.init()    # 初始化数据库
    setup_global_hotkey()  # 设置全局快捷键
    # 启动时临时置顶
    if global_window:
        global_window.on_top = True
        # 创建新线程来延迟取消置顶
        threading.Thread(target=reset_top_after_delay, daemon=True).start()

def on_loaded():
    # print('DOM加载完毕')
    pass

def on_closing():
    # print('程序关闭')
    pass

def WebViewApp(ifCef=False):
    global global_window

    # 是否为开发环境
    Config.devEnv = sys.flags.dev_mode

    # 视图层页面URL
    if Config.devEnv:
        # 开发环境
        MAIN_DIR = f'http://localhost:{Config.devPort}/'
        template = os.path.join(MAIN_DIR, "")    # 设置页面，指向远程
    else:
        # 生产环境
        MAIN_DIR = os.path.join(".", "web")
        template = os.path.join(MAIN_DIR, "index.html")    # 设置页面，指向本地

        # 修复某些情况下，打包后软件打开白屏的问题
        mimetypes.add_type('application/javascript', '.js')

    # 系统分辨率
    screens = webview.screens
    screens = screens[0]
    width = screens.width
    height = screens.height
    # 程序窗口大小
    initWidth = int(width * 2 / 3)
    initHeight = int(height * 4 / 5)
    minWidth = int(initWidth / 2)
    minHeight = int(initHeight / 2)

    # 创建窗口，禁用隐私模式以保留缓存数据
    window = webview.create_window(
        title=Config.appName, 
        url=template, 
        js_api=api, 
        width=initWidth, 
        height=initHeight, 
        min_size=(minWidth, minHeight),
        on_top=False  # 默认不置顶，只在需要时通过 move_to_front() 置顶
    )
    
    # 存储窗口实例到全局变量
    global_window = window

    # 获取窗口实例
    api.setWindow(window)

    # 绑定事件
    window.events.shown += on_shown
    window.events.loaded += on_loaded
    window.events.closing += on_closing

    # CEF模式
    guiCEF = 'cef' if ifCef else None

    # 启动窗口，禁用隐私模式以保留缓存数据
    webview.start(debug=Config.devEnv, http_server=True, gui=guiCEF, private_mode=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cef", action="store_true", dest="if_cef", help="if_cef")
    args = parser.parse_args()

    ifCef = args.if_cef    # 是否开启cef模式

    WebViewApp(ifCef)
