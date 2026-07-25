#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思维导图（团队协作）API

将原独立部署的 FastAPI 思维导图服务内嵌为工具箱内的本地服务：
  - lazy import：模块顶层不导入 fastapi/uvicorn/sqlalchemy，依赖缺失时返回友好错误。
  - 配置注入：api.mindmap 服务端在 import 时读取环境变量（DATA_DIR/DATABASE_URL/
    JWT_SECRET/MINDMAP_STATIC_DIR），因此必须先设置环境变量再导入服务端模块。
    同进程内第二次启动会复用首次 import 的配置——各值按安装目录稳定，无影响。
  - 线程模型：uvicorn.Server 运行在后台 daemon 线程，主线程只做启停与状态查询。
  - 端口策略：固定首选端口（保证浏览器 localStorage 登录态跨重启保留），
    被占用时向后顺延扫描。
  - 局域网协作：开启后服务绑定 0.0.0.0，队友用浏览器访问本机局域网地址即可协同。
"""
from __future__ import annotations

import os
import secrets
import socket
import threading
import time

from api.utils import api_error, api_success

DEFAULT_PORT = 8323
PORT_SCAN_RANGE = 16
START_TIMEOUT = 15  # 秒
HEALTH_TIMEOUT = 2  # 单次健康检查超时（秒）
HEALTH_RETRIES = 10


class MindMapTool:
    """思维导图工具，混入 API 类"""

    _mm_lock = threading.Lock()
    _mm_server = None          # uvicorn.Server
    _mm_thread: threading.Thread | None = None
    _mm_port: int = 0
    _mm_lan: bool = False

    # ---------- 内部工具 ----------

    def _mm_data_dir(self) -> str:
        try:
            from pyapp.config.config import Config
            base = Config.appDataDir
        except Exception:
            base = ''
        if not base:
            base = os.path.join(os.path.expanduser('~'), '.ppx-mindmap')
        path = os.path.join(base, 'mindmap')
        os.makedirs(path, exist_ok=True)
        return path

    def _mm_static_dir(self) -> str:
        try:
            from pyapp.config.config import Config
            return os.path.join(Config.staticDir, 'mindmap')
        except Exception:
            return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'static', 'mindmap')

    def _mm_jwt_secret(self) -> str:
        """JWT 密钥首次生成后持久化，保证令牌跨应用重启有效。"""
        path = os.path.join(self._mm_data_dir(), 'jwt.secret')
        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    secret = f.read().strip()
                if secret:
                    return secret
        except OSError as exc:
            raise RuntimeError(f'无法读取思维导图登录密钥：{exc}') from exc
        secret = secrets.token_hex(32)
        temp_path = path + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(secret)
                f.flush()
                os.fsync(f.fileno())
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, path)
        except OSError as exc:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
            raise RuntimeError(f'无法保存思维导图登录密钥：{exc}') from exc
        return secret

    def _mm_prepare_env(self) -> None:
        """在导入 api.mindmap 服务端模块之前注入配置环境变量。"""
        data_dir = self._mm_data_dir()
        os.environ['DATA_DIR'] = data_dir
        # 注意：数据库文件名为 smm.db——旧集成遗留的 mindmap.db 表结构不兼容，不能复用
        os.environ['DATABASE_URL'] = f"sqlite+aiosqlite:///{data_dir.replace(os.sep, '/')}/smm.db"
        os.environ['JWT_SECRET'] = self._mm_jwt_secret()
        os.environ['MINDMAP_STATIC_DIR'] = self._mm_static_dir()

    @staticmethod
    def _mm_port_free(host: str, port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
            return True
        except OSError:
            return False

    def _mm_pick_port(self, host: str) -> int:
        for port in range(DEFAULT_PORT, DEFAULT_PORT + PORT_SCAN_RANGE):
            if self._mm_port_free(host, port):
                return port
        raise RuntimeError(f'未找到可用端口（{DEFAULT_PORT}-{DEFAULT_PORT + PORT_SCAN_RANGE - 1} 均被占用）')

    @staticmethod
    def _mm_lan_ips() -> list:
        """列出本机局域网 IPv4 地址（去掉回环/链路本地）。"""
        ips = []
        try:
            import psutil
            for addrs in psutil.net_if_addrs().values():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            ips.append(ip)
        except Exception:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(('8.8.8.8', 80))
                    ips.append(s.getsockname()[0])
            except Exception:
                pass
        # 保序去重
        return list(dict.fromkeys(ips))

    @staticmethod
    def _mm_health_ok(port: int) -> bool:
        """轮询健康检查端点，确认 HTTP 栈真正就绪。"""
        import urllib.request
        url = f'http://127.0.0.1:{port}/api/health'
        for _ in range(HEALTH_RETRIES):
            try:
                with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
            time.sleep(0.2)
        return False

    def _mm_running(self) -> bool:
        return (
            self._mm_thread is not None
            and self._mm_thread.is_alive()
            and self._mm_server is not None
            and getattr(self._mm_server, 'started', False)
            and not getattr(self._mm_server, 'should_exit', False)
        )

    def _mm_state(self, message: str = '操作成功'):
        running = self._mm_running()
        port = self._mm_port if running else 0
        return api_success(
            message,
            running=running,
            port=port,
            lan=self._mm_lan if running else False,
            localUrl=f'http://127.0.0.1:{port}/' if running else '',
            lanUrls=[f'http://{ip}:{port}/' for ip in self._mm_lan_ips()] if (running and self._mm_lan) else [],
        )

    def _mm_stop_locked(self, timeout: float = 8.0) -> None:
        """持有 _mm_lock 时调用：停止服务线程。"""
        server, thread = self._mm_server, self._mm_thread
        if server is not None:
            server.should_exit = True
        if thread is not None and thread.is_alive():
            thread.join(timeout)
        type(self)._mm_server = None
        type(self)._mm_thread = None
        type(self)._mm_port = 0

    # ---------- 暴露给前端的方法 ----------

    def mindmap_status(self):
        """查询思维导图服务状态"""
        try:
            with self._mm_lock:
                return self._mm_state()
        except Exception as exc:
            return api_error(f'查询状态失败: {exc}')

    def mindmap_start(self, lan=False):
        """启动（或复用）本地思维导图服务；lan=True 时绑定 0.0.0.0 供局域网协作"""
        lan = bool(lan)
        try:
            # 服务端模块在 import 时读取环境变量，必须先注入配置再导入
            self._mm_prepare_env()
            try:
                import uvicorn

                from api.mindmap.main import app
            except ImportError as exc:
                return api_error(f'思维导图组件依赖缺失，请重新运行 pnpm run init 安装依赖（{exc}）')

            with self._mm_lock:
                if self._mm_running():
                    if self._mm_lan == lan:
                        return self._mm_state('服务已在运行')
                    # 切换绑定地址需要重启
                    self._mm_stop_locked()

                host = '0.0.0.0' if lan else '127.0.0.1'
                port = self._mm_pick_port(host)
                # 显式固定事件循环与协议实现，保证 PyInstaller 依赖图确定
                # （不引入 websockets/uvloop/httptools）
                uv_config = uvicorn.Config(
                    app,
                    host=host,
                    port=port,
                    log_config=None,
                    log_level='warning',
                    loop='asyncio',
                    http='h11',
                    ws='none',
                )
                server = uvicorn.Server(uv_config)
                thread = threading.Thread(target=server.run, name='mindmap-server', daemon=True)
                thread.start()

                deadline = time.time() + START_TIMEOUT
                while time.time() < deadline:
                    if getattr(server, 'started', False):
                        break
                    if not thread.is_alive():
                        return api_error(f'思维导图服务启动失败（进程异常退出，端口 {port}）')
                    time.sleep(0.05)
                else:
                    server.should_exit = True
                    return api_error('思维导图服务启动超时')

                if not self._mm_health_ok(port):
                    server.should_exit = True
                    return api_error('思维导图服务健康检查未通过')

                type(self)._mm_server = server
                type(self)._mm_thread = thread
                type(self)._mm_port = port
                type(self)._mm_lan = lan
                return self._mm_state('服务已启动')
        except Exception as exc:
            return api_error(f'启动失败: {exc}')

    def mindmap_stop(self):
        """停止本地思维导图服务"""
        try:
            with self._mm_lock:
                if not self._mm_running():
                    self._mm_stop_locked()
                    return api_success('服务未在运行', running=False)
                self._mm_stop_locked()
                return api_success('服务已停止', running=False)
        except Exception as exc:
            return api_error(f'停止失败: {exc}')

    def mindmap_open_browser(self, url=''):
        """在系统默认浏览器中打开思维导图"""
        try:
            import webbrowser
            target = url or (f'http://127.0.0.1:{self._mm_port}/' if self._mm_port else '')
            if not target:
                return api_error('服务未在运行')
            webbrowser.open(target)
            return api_success('已在浏览器打开')
        except Exception as exc:
            return api_error(f'打开浏览器失败: {exc}')
