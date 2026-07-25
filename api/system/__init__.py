#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-03-26 20:48:26
LastEditTime: 2025-02-10 14:25:13
Description: 系统类组合入口
    原 api/system.py 已按职责拆分为多个 Mixin 模块，此处组合为统一的 System 类。
    对外接口保持完全等价：`from api.system import System` 仍然可用，
    所有公开方法名、参数、返回结构及 `System._window` 类属性均保持不变。
usage: 调用window.pywebview.api.<methodname>(<parameters>)从Javascript执行
'''

from api.system.base import SystemBaseMixin
from api.system.info import SystemInfoMixin
from api.system.process import ProcessMixin
from api.system.software import SoftwareMixin
from api.system.startup import StartupMixin
from api.system.window import WindowMixin


class System(
    SystemInfoMixin,
    ProcessMixin,
    StartupMixin,
    SoftwareMixin,
    WindowMixin,
    SystemBaseMixin
):
    '''系统类

    由以下 Mixin 组合而成（公共基础 SystemBaseMixin 置于 MRO 末尾，
    保证 _window 类属性与共享辅助方法对所有 Mixin 可见）：
      - SystemInfoMixin : 应用信息、文件对话框、系统状态、磁盘分析
      - ProcessMixin    : 进程管理
      - StartupMixin    : 开机启动项
      - SoftwareMixin   : 软件管理 / 强力清理（扫描、卸载、粉碎安装目录）
      - WindowMixin     : 窗口控制
      - SystemBaseMixin : 公共辅助、_window 类属性、状态文件读写
    '''


__all__ = ['System']
