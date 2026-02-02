#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2022-03-23 15:41:46
LastEditTime: 2025-06-24 08:56:56
Description: 生成客户端主程序
usage: 运行前，请确保本机已经搭建Python3开发环境，且已经安装 pywebview 模块。
'''

import argparse
import mimetypes
import os

import webview

from api.api import API
from pyapp.config.config import Config

from pyapp.db.db import DB

cfg = Config()    # 配置
db = DB()    # 数据库类
api = API()    # 本地接口

cfg.init()


def on_shown():
    # print('程序启动')
    db.init()    # 初始化数据库


def on_loaded():
    # print('DOM加载完毕')
    pass


def on_closing():
    # print('程序关闭')
    pass


def WebViewApp(ifDev=False, ifCef=False):

    # 是否为开发环境
    Config.devEnv = ifDev

    # 视图层页面URL
    if Config.devEnv:
        # 开发环境
        template = f'http://localhost:{Config.devPort}/'
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
    
    # 启动器窗口大小（固定尺寸）
    initWidth = Config.launcherWidth
    initHeight = Config.launcherHeight
    
    # 计算居中位置
    x = int((width - initWidth) / 2)
    y = int((height - initHeight) / 2)

    # 创建窗口（启动器模式：无边框、固定大小、初始隐藏）
    window = webview.create_window(
        title=Config.appName, 
        url=template, 
        js_api=api, 
        width=initWidth, 
        height=initHeight,
        x=x,
        y=y,
        resizable=False,  # 启动器窗口固定大小
        frameless=True,  # 无边框窗口
        easy_drag=True,  # 支持拖动
        on_top=True,  # 窗口置顶
        hidden=False  # 默认显示窗口
    )

    # 获取窗口实例
    api.setWindow(window)

    # 绑定事件
    window.events.shown += on_shown
    window.events.loaded += on_loaded
    window.events.closing += on_closing

    # CEF模式
    guiCEF = 'cef' if ifCef else None

    # 启动全局快捷键监听
    def start_hotkey_listener():
        api.start_listener()
    
    # 在开发模式下不需要http_server，因为使用Vite服务器
    use_http_server = not Config.devEnv
    
    # 启动窗口
    webview.start(func=start_hotkey_listener, debug=Config.devEnv, http_server=use_http_server, gui=guiCEF)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dev", action="store_true", dest="if_dev", help="if_dev")
    parser.add_argument("-c", "--cef", action="store_true", dest="if_cef", help="if_cef")
    args = parser.parse_args()

    ifDev = args.if_dev    # 是否开启开发环境
    ifCef = args.if_cef    # 是否开启cef模式

    WebViewApp(ifDev, ifCef)
