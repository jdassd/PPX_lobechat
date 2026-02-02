#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
Date: 2026-01-15
Description: 全局快捷键管理
'''

import threading
import keyboard
from pyapp.config.config import Config
from pyapp.db.db import DB


class HotkeyManager:
    '''全局快捷键管理类'''

    _window = None
    _hotkey_thread = None
    _current_hotkey = None
    _is_running = False

    def __init__(self):
        self.db = DB()

    def toggle_window_visibility(self):
        '''切换窗口显示/隐藏'''
        try:
            if self._window:
                # 检查窗口是否隐藏
                # pywebview 没有直接的 is_hidden 属性，我们通过尝试显示/隐藏来切换
                try:
                    self._window.hide()
                    # 如果成功隐藏，说明之前是显示的
                except:
                    # 如果隐藏失败，尝试显示
                    self._window.show()
            return {'code': 200, 'message': '窗口切换成功'}
        except Exception as e:
            return {'code': 500, 'message': f'窗口切换失败: {str(e)}'}

    def register_hotkey(self, key_combination=None):
        '''
        注册全局快捷键
        :param key_combination: 快捷键组合，如 'ctrl+shift+space'
        :return: 操作结果
        '''
        try:
            # 如果没有指定快捷键，从配置或数据库读取
            if not key_combination:
                config_table = self.db.get('launcher_config')
                configs = config_table.all()
                if configs and 'hotkey' in configs[0]:
                    key_combination = configs[0]['hotkey']
                else:
                    key_combination = Config.defaultHotkey

            # 先注销之前的快捷键
            if self._current_hotkey:
                self.unregister_hotkey()

            # 注册新快捷键
            keyboard.add_hotkey(key_combination, self.toggle_window_visibility)
            self._current_hotkey = key_combination
            
            return {'code': 200, 'message': f'快捷键 {key_combination} 注册成功'}

        except Exception as e:
            return {'code': 500, 'message': f'快捷键注册失败: {str(e)}'}

    def unregister_hotkey(self):
        '''
        注销全局快捷键
        :return: 操作结果
        '''
        try:
            if self._current_hotkey:
                keyboard.remove_hotkey(self._current_hotkey)
                self._current_hotkey = None
            return {'code': 200, 'message': '快捷键注销成功'}

        except Exception as e:
            return {'code': 500, 'message': f'快捷键注销失败: {str(e)}'}

    def update_hotkey(self, new_key_combination):
        '''
        更新快捷键配置
        :param new_key_combination: 新的快捷键组合
        :return: 操作结果
        '''
        try:
            # 更新数据库配置
            config_table = self.db.get('launcher_config')
            configs = config_table.all()
            
            if configs:
                from tinydb import Query
                Config_q = Query()
                config_table.update({'hotkey': new_key_combination}, Config_q.hotkey.exists())
            else:
                config_table.insert({'hotkey': new_key_combination})

            # 重新注册快捷键
            return self.register_hotkey(new_key_combination)

        except Exception as e:
            return {'code': 500, 'message': f'更新快捷键失败: {str(e)}'}

    def get_current_hotkey(self):
        '''
        获取当前快捷键配置
        :return: 快捷键字符串
        '''
        try:
            config_table = self.db.get('launcher_config')
            configs = config_table.all()
            
            if configs and 'hotkey' in configs[0]:
                hotkey = configs[0]['hotkey']
            else:
                hotkey = Config.defaultHotkey

            return {'code': 200, 'message': '获取成功', 'data': {'hotkey': hotkey}}

        except Exception as e:
            return {'code': 500, 'message': f'获取快捷键失败: {str(e)}'}

    def start_listener(self):
        '''
        启动快捷键监听（在后台线程运行）
        :return: 操作结果
        '''
        try:
            if not self._is_running:
                self._is_running = True
                # keyboard 库会自动在后台监听，无需额外线程
                self.register_hotkey()
            return {'code': 200, 'message': '快捷键监听已启动'}

        except Exception as e:
            return {'code': 500, 'message': f'启动监听失败: {str(e)}'}

    def stop_listener(self):
        '''
        停止快捷键监听
        :return: 操作结果
        '''
        try:
            if self._is_running:
                self.unregister_hotkey()
                self._is_running = False
            return {'code': 200, 'message': '快捷键监听已停止'}

        except Exception as e:
            return {'code': 500, 'message': f'停止监听失败: {str(e)}'}

    def get_launcher_config(self):
        '''
        获取启动器配置
        :return: 配置字典
        '''
        try:
            config_table = self.db.get('launcher_config')
            configs = config_table.all()
            
            if configs:
                config = configs[0]
            else:
                # 返回默认配置
                config = {
                    'hotkey': Config.defaultHotkey,
                    'window_always_on_top': True,
                    'auto_start': False,
                    'theme': 'dark'
                }
                config_table.insert(config)

            return {'code': 200, 'message': '获取配置成功', 'data': config}

        except Exception as e:
            return {'code': 500, 'message': f'获取配置失败: {str(e)}'}

    def update_launcher_config(self, config_data):
        '''
        更新启动器配置
        :param config_data: 配置字典
        :return: 操作结果
        '''
        try:
            config_table = self.db.get('launcher_config')
            configs = config_table.all()
            
            if configs:
                from tinydb import Query
                Config_q = Query()
                # 更新所有配置（假设只有一条配置记录）
                config_table.update(config_data, doc_ids=[configs[0].doc_id])
            else:
                config_table.insert(config_data)

            # 如果更新了快捷键，重新注册
            if 'hotkey' in config_data:
                self.register_hotkey(config_data['hotkey'])

            return {'code': 200, 'message': '配置更新成功'}

        except Exception as e:
            return {'code': 500, 'message': f'配置更新失败: {str(e)}'}
