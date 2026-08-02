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
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import webview

from api.api import API
from pyapp.config.config import Config
from pyapp.db.db import DB

cfg = Config()    # 配置
db = DB()    # 数据库类
api = API()    # 本地接口

cfg.init()

# 创建窗口前不能读取 webview.screens：pywebview 会据此初始化默认 GUI，
# 使 --cef 之后的 gui='cef' 失效。先使用稳定的初始尺寸，窗口显示后再适配屏幕。
INITIAL_WINDOW_WIDTH = 1280
INITIAL_WINDOW_HEIGHT = 800
MIN_WINDOW_WIDTH = 640
MIN_WINDOW_HEIGHT = 400
DEV_SHUTDOWN_GRACE_SECONDS = 3.0
_dev_shutdown_watchdog = None
_window_state_restored = False


def on_shown():
    # print('程序启动')
    try:
        restore_result = api.maintenance_apply_pending_restore()
        if isinstance(restore_result, dict) and restore_result.get('restored'):
            print(f'[Restore] {restore_result.get("msg", "备份恢复完成")}')
    except Exception as err:
        print(f'[Restore] 应用待恢复备份失败: {err}')
    db.init()    # 初始化数据库
    try:
        api.workflow_start()
    except Exception as err:
        print(f'[Startup] 启动自动化服务失败: {err}')


def on_loaded():
    # print('DOM加载完毕')
    pass


def on_closing(window=None):
    # print('程序关闭')
    if window is not None:
        _save_window_state(window)
    try:
        api.workflow_stop()
    except Exception as err:
        print(f'[Shutdown] 停止自动化服务失败: {err}')
    try:
        api.mindmap_stop()
    except Exception as err:
        print(f'[Shutdown] 停止思维导图服务失败: {err}')
    try:
        api.task_shutdown()
    except Exception as err:
        print(f'[Shutdown] 停止任务队列失败: {err}')
    _terminate_dev_supervisor()
    _start_dev_shutdown_watchdog()


def _terminate_dev_supervisor():
    '''开发环境下由 nodemon 启动时，关闭窗口后连带结束其父进程'''
    if not Config.devEnv:
        return

    nodemon_flag = str(os.getenv('NODEMON', '')).strip().lower()
    if nodemon_flag not in ('1', 'true', 'yes', 'on'):
        return

    parent_pid = os.getppid()
    if parent_pid <= 1:
        return

    try:
        if Config.appSystem == 'Windows':
            subprocess.run(
                ['taskkill', '/PID', str(parent_pid), '/T', '/F'],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            os.kill(parent_pid, signal.SIGTERM)
    except Exception as err:
        print(f'[Shutdown] 结束开发父进程失败: {err}')


def _start_dev_shutdown_watchdog():
    '''正常关闭若被 GUI 后端卡住，宽限期后才强制结束开发进程。'''
    global _dev_shutdown_watchdog
    if not Config.devEnv or _dev_shutdown_watchdog is not None:
        return
    _dev_shutdown_watchdog = threading.Timer(DEV_SHUTDOWN_GRACE_SECONDS, lambda: os._exit(0))
    _dev_shutdown_watchdog.daemon = True
    _dev_shutdown_watchdog.start()


def _cancel_dev_shutdown_watchdog():
    global _dev_shutdown_watchdog
    if _dev_shutdown_watchdog is not None:
        _dev_shutdown_watchdog.cancel()
        _dev_shutdown_watchdog = None


def _probe_vite_server(host: str, port: int) -> bool:
    '''验证目标确实是 Vite 开发服务器，避免误连同端口上的其它服务。'''
    url = f'http://{host}:{port}/@vite/client'
    try:
        request = urllib.request.Request(url, headers={'Accept': 'text/javascript'})
        with urllib.request.urlopen(request, timeout=0.8) as response:
            content_type = response.headers.get_content_type()
            snippet = response.read(16384)
            return (
                response.status == 200
                and content_type in ('text/javascript', 'application/javascript')
                and (b'[vite] connecting' in snippet or b'createHotContext' in snippet)
            )
    except (OSError, urllib.error.URLError, ValueError):
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


def _window_state_path():
    return Path(Config.appDataDir) / 'window-state.json'


def _load_window_state():
    try:
        payload = json.loads(_window_state_path().read_text(encoding='utf-8'))
        width = int(payload.get('width') or 0)
        height = int(payload.get('height') or 0)
        if not MIN_WINDOW_WIDTH <= width <= 10000 or not MIN_WINDOW_HEIGHT <= height <= 10000:
            return None
        return {
            'width': width,
            'height': height,
            'x': int(payload['x']) if payload.get('x') is not None else None,
            'y': int(payload['y']) if payload.get('y') is not None else None,
        }
    except (OSError, ValueError, TypeError, KeyError):
        return None


def _save_window_state(window):
    try:
        payload = {
            'schemaVersion': 1,
            'width': max(MIN_WINDOW_WIDTH, int(window.width)),
            'height': max(MIN_WINDOW_HEIGHT, int(window.height)),
            'x': int(window.x),
            'y': int(window.y),
            'savedAt': time.time(),
        }
        path = _window_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, path)
    except Exception as err:
        print(f'[Window] 保存窗口状态失败: {err}')


def _resize_window_for_primary_screen(window, restored=False):
    '''GUI 初始化完成后，按主屏幕尺寸恢复原有的窗口比例。'''
    try:
        screens = webview.screens
        if not screens:
            return
        screen = screens[0]
        if restored:
            visible = any(
                window.x < item.x + item.width
                and window.x + window.width > item.x
                and window.y < item.y + item.height
                and window.y + window.height > item.y
                for item in screens
            )
            if not visible:
                window.move(
                    int(screen.x + max(0, screen.width - window.width) / 2),
                    int(screen.y + max(0, screen.height - window.height) / 2),
                )
        else:
            width = max(MIN_WINDOW_WIDTH, int(screen.width * 2 / 3))
            height = max(MIN_WINDOW_HEIGHT, int(screen.height * 4 / 5))
            if width > 0 and height > 0:
                window.resize(width, height)
    except Exception as err:
        # 屏幕查询或后端不支持 resize 时保留稳定的初始尺寸即可。
        print(f'[Window] 未能按屏幕调整窗口尺寸: {err}')


def _on_window_shown(window):
    _resize_window_for_primary_screen(window, _window_state_restored)
    on_shown()


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
            if _probe_vite_server(host, hint_port):
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
                if _probe_vite_server(host, port):
                    Config.devPort = str(port)
                    resolved = f'http://{host}:{port}/'
                    print(f'[DevServer] 已检测到 Vite 端口 {port}，将使用 {resolved}')
                    return resolved
        time.sleep(0.5)
    raise RuntimeError(
        f'未检测到 Vite 开发服务器（已扫描端口 {base_port}-{base_port + max(1, span) - 1}），'
        '请确认前端已启动并查看 pnpm run dev 的输出。'
    )


def WebViewApp(ifDev=False, ifCef=False, open_files=None):
    global _window_state_restored

    # 在任何 pywebview GUI 相关访问前确定后端，尤其不能让 --cef 被默认 GUI 抢先初始化。
    guiCEF = 'cef' if ifCef else None

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
        # 以 Config.codeDir（打包后的真实资源根目录）定位 web，
        # 与 static 的定位方式保持一致；PyInstaller 6.x 会把数据文件
        # 放入 _internal/ 子目录，若用相对 CWD 的 "./web" 会找不到而白屏
        MAIN_DIR = os.path.join(Config.codeDir, "web")
        template = os.path.join(MAIN_DIR, "index.html")    # 设置页面，指向本地

        # 修复某些情况下，打包后软件打开白屏的问题
        mimetypes.add_type('application/javascript', '.js')

    launch_files = []
    for raw_path in open_files or []:
        path = Path(str(raw_path)).expanduser().resolve()
        if path.is_file():
            launch_files.append(str(path))
    if launch_files:
        separator = '&' if '?' in template else '?'
        query = urllib.parse.urlencode({'openFiles': json.dumps(launch_files, ensure_ascii=False)})
        template = f'{template}{separator}{query}'

    window_state = _load_window_state()
    _window_state_restored = bool(window_state)
    width = window_state['width'] if window_state else INITIAL_WINDOW_WIDTH
    height = window_state['height'] if window_state else INITIAL_WINDOW_HEIGHT

    # 创建窗口
    window = webview.create_window(
        title=Config.appName,
        url=template,
        js_api=api,
        width=width,
        height=height,
        x=window_state.get('x') if window_state else None,
        y=window_state.get('y') if window_state else None,
        min_size=(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT),
        frameless=True,  # 禁用系统默认窗口装饰，使用自定义顶栏
        resizable=True,
        easy_drag=False
    )

    # 获取窗口实例
    api.setWindow(window)

    # 绑定事件
    window.events.shown += lambda: _on_window_shown(window)
    window.events.loaded += on_loaded
    window.events.closing += lambda: on_closing(window)

    # 启动窗口
    try:
        webview.start(debug=Config.devEnv, http_server=True, gui=guiCEF)
    finally:
        _cancel_dev_shutdown_watchdog()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dev", action="store_true", dest="if_dev", help="if_dev")
    parser.add_argument("-c", "--cef", action="store_true", dest="if_cef", help="if_cef")
    parser.add_argument('files', nargs='*', help='启动后打开的本地文件')
    args = parser.parse_args()

    ifDev = args.if_dev    # 是否开启开发环境
    ifCef = args.if_cef    # 是否开启cef模式

    WebViewApp(ifDev, ifCef, args.files)
