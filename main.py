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
import json
import mimetypes
import os
import socket
import time
from contextlib import closing

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


def _probe_port(host: str, port: int) -> bool:
    '''简单探测某个端口是否可连接'''
    try:
        with closing(socket.create_connection((host, port), timeout=0.6)):
            return True
    except OSError:
        return False


def _dev_port_file():
    return os.path.join(Config.codeDir, '.ppx-dev-port')


def _read_dev_port_hint():
    path = _dev_port_file()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handler:
            data = json.load(handler)
        port = int(data.get('port'))
        timestamp = float(data.get('time', 0)) / 1000.0
        if port <= 0:
            return None
        if time.time() - timestamp > 120:
            return None
        return port
    except Exception:
        return None


def _wait_dev_port_hint(timeout: float = 12.0):
    deadline = time.time() + max(0.5, timeout)
    while time.time() < deadline:
        hint = _read_dev_port_hint()
        if hint:
            return hint
        time.sleep(0.3)
    return None


def _resolve_dev_server(base_port: int, timeout: float = 25.0, span: int = 16):
    '''探测实际启动的 Vite 端口（支持端口被占用后自动递增）'''
    hosts = ['127.0.0.1', 'localhost']
    hint_port = _wait_dev_port_hint(min(timeout * 0.4, 10))
    if hint_port:
        for host in hosts:
            if _probe_port(host, hint_port):
                Config.devPort = str(hint_port)
                resolved = f'http://{host}:{hint_port}/'
                print(f'[DevServer] 根据端口文件命中 {resolved}')
                return resolved
    if hint_port:
        print(f'[DevServer] 端口文件 {hint_port} 无法连接，尝试扫描')
    ports = [base_port + offset for offset in range(max(1, span))]
    deadline = time.time() + max(1.0, timeout)
    while time.time() < deadline:
        for port in ports:
            for host in hosts:
                if _probe_port(host, port):
                    Config.devPort = str(port)
                    resolved = f'http://{host}:{port}/'
                    print(f'[DevServer] 已检测到 Vite 端口 {port}，将使用 {resolved}')
                    return resolved
        time.sleep(0.5)
    print(f'[DevServer] 未检测到动态端口，回落至 http://localhost:{base_port}/')
    return f'http://localhost:{base_port}/'


def WebViewApp(ifDev=False, ifCef=False):

    # 是否为开发环境
    Config.devEnv = ifDev

    # 视图层页面URL
    if Config.devEnv:
        # 开发环境
        try:
            base_port = int(Config.devPort)
        except (TypeError, ValueError):
            base_port = 5173
        MAIN_DIR = _resolve_dev_server(base_port)
        template = MAIN_DIR    # 设置页面，指向远程
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

    # 创建窗口
    window = webview.create_window(
        title=Config.appName,
        url=template,
        js_api=api,
        width=initWidth,
        height=initHeight,
        min_size=(minWidth, minHeight),
        frameless=True,  # 禁用系统默认窗口装饰，使用自定义顶栏
        resizable=True,
        easy_drag=False
    )

    # 获取窗口实例
    api.setWindow(window)

    # 绑定事件
    window.events.shown += on_shown
    window.events.loaded += on_loaded
    window.events.closing += on_closing

    # CEF模式
    guiCEF = 'cef' if ifCef else None

    # 启动窗口
    webview.start(debug=Config.devEnv, http_server=True, gui=guiCEF)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dev", action="store_true", dest="if_dev", help="if_dev")
    parser.add_argument("-c", "--cef", action="store_true", dest="if_cef", help="if_cef")
    args = parser.parse_args()

    ifDev = args.if_dev    # 是否开启开发环境
    ifCef = args.if_cef    # 是否开启cef模式

    WebViewApp(ifDev, ifCef)
