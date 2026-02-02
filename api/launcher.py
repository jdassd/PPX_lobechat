#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
Date: 2026-01-15
Description: 启动器核心功能API
'''

import base64
import os
import subprocess
import uuid
from datetime import datetime
from io import BytesIO

from PIL import Image
from pyapp.config.config import Config
from pyapp.db.db import DB


class Launcher:
    '''启动器核心功能类'''

    def __init__(self):
        self.db = DB()

    def add_application(self, file_path):
        '''
        添加应用到启动器
        :param file_path: 文件路径（.lnk 或 .exe）
        :return: 应用信息字典
        '''
        try:
            # 解析快捷方式或可执行文件
            if file_path.lower().endswith('.lnk'):
                target_path, app_name = self._parse_shortcut(file_path)
            elif file_path.lower().endswith('.exe'):
                target_path = file_path
                app_name = os.path.basename(file_path).replace('.exe', '')
            else:
                return {'code': 400, 'message': '不支持的文件类型，仅支持 .lnk 和 .exe 文件'}

            # 检查文件是否存在
            if not os.path.exists(target_path):
                return {'code': 404, 'message': '目标文件不存在'}

            # 提取图标
            icon_base64 = self._extract_icon(target_path)

            # 获取当前应用数量，用于排序
            apps = self.get_applications()
            order = len(apps.get('data', [])) if apps.get('code') == 200 else 0

            # 创建应用数据
            app_data = {
                'id': str(uuid.uuid4()),
                'name': app_name,
                'path': target_path,
                'icon': icon_base64,
                'order': order,
                'created_at': datetime.now().isoformat(),
                'launch_count': 0
            }

            # 保存到数据库
            table = self.db.get('launcher_apps')
            table.insert(app_data)

            return {'code': 200, 'message': '添加成功', 'data': app_data}

        except Exception as e:
            return {'code': 500, 'message': f'添加失败: {str(e)}'}

    def remove_application(self, app_id):
        '''
        从启动器移除应用
        :param app_id: 应用ID
        :return: 操作结果
        '''
        try:
            table = self.db.get('launcher_apps')
            from tinydb import Query
            App = Query()
            
            result = table.remove(App.id == app_id)
            
            if result:
                return {'code': 200, 'message': '删除成功'}
            else:
                return {'code': 404, 'message': '应用不存在'}

        except Exception as e:
            return {'code': 500, 'message': f'删除失败: {str(e)}'}

    def get_applications(self):
        '''
        获取所有已添加的应用
        :return: 应用列表
        '''
        try:
            table = self.db.get('launcher_apps')
            apps = table.all()
            
            # 按 order 排序
            apps.sort(key=lambda x: x.get('order', 0))
            
            return {'code': 200, 'message': '获取成功', 'data': apps}

        except Exception as e:
            return {'code': 500, 'message': f'获取失败: {str(e)}', 'data': []}

    def launch_application(self, app_id):
        '''
        启动指定应用
        :param app_id: 应用ID
        :return: 操作结果
        '''
        try:
            table = self.db.get('launcher_apps')
            from tinydb import Query
            App = Query()
            
            apps = table.search(App.id == app_id)
            
            if not apps:
                return {'code': 404, 'message': '应用不存在'}
            
            app = apps[0]
            app_path = app.get('path')
            
            # 检查文件是否存在
            if not os.path.exists(app_path):
                return {'code': 404, 'message': '应用文件不存在，可能已被删除或移动'}
            
            # 启动应用
            if Config.appSystem == 'Windows':
                os.startfile(app_path)
            elif Config.appSystem == 'Darwin':  # macOS
                subprocess.Popen(['open', app_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', app_path])
            
            # 更新启动次数
            table.update({'launch_count': app.get('launch_count', 0) + 1}, App.id == app_id)
            
            return {'code': 200, 'message': '启动成功'}

        except Exception as e:
            return {'code': 500, 'message': f'启动失败: {str(e)}'}

    def update_app_order(self, app_ids):
        '''
        更新应用显示顺序
        :param app_ids: 应用ID列表（按新顺序排列）
        :return: 操作结果
        '''
        try:
            table = self.db.get('launcher_apps')
            from tinydb import Query
            App = Query()
            
            for index, app_id in enumerate(app_ids):
                table.update({'order': index}, App.id == app_id)
            
            return {'code': 200, 'message': '更新顺序成功'}

        except Exception as e:
            return {'code': 500, 'message': f'更新顺序失败: {str(e)}'}

    def _parse_shortcut(self, lnk_path):
        '''
        解析快捷方式文件
        :param lnk_path: .lnk 文件路径
        :return: (目标路径, 应用名称)
        '''
        try:
            if Config.appSystem == 'Windows':
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(lnk_path)
                target_path = shortcut.Targetpath
                app_name = os.path.basename(lnk_path).replace('.lnk', '')
                return target_path, app_name
            else:
                # 非 Windows 系统暂不支持 .lnk 文件
                raise Exception('当前系统不支持 .lnk 快捷方式文件')

        except Exception as e:
            raise Exception(f'解析快捷方式失败: {str(e)}')

    def _extract_icon(self, file_path):
        '''
        提取应用图标
        :param file_path: 文件路径
        :return: Base64 编码的图标
        '''
        try:
            if Config.appSystem == 'Windows':
                import win32api
                import win32con
                import win32ui
                import win32gui
                
                # 获取图标
                large, small = win32gui.ExtractIconEx(file_path, 0)
                
                if large:
                    # 使用大图标
                    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                    hbmp = win32ui.CreateBitmap()
                    hbmp.CreateCompatibleBitmap(hdc, 48, 48)
                    hdc_new = hdc.CreateCompatibleDC()
                    hdc_new.SelectObject(hbmp)
                    hdc_new.DrawIcon((0, 0), large[0])
                    
                    # 转换为PIL Image
                    bmpinfo = hbmp.GetInfo()
                    bmpstr = hbmp.GetBitmapBits(True)
                    img = Image.frombuffer(
                        'RGB',
                        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                        bmpstr, 'raw', 'BGRX', 0, 1
                    )
                    
                    # 销毁图标句柄
                    win32gui.DestroyIcon(large[0])
                    if small:
                        win32gui.DestroyIcon(small[0])
                    
                    # 转换为 Base64
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    icon_base64 = base64.b64encode(buffered.getvalue()).decode()
                    
                    return icon_base64
                else:
                    # 如果无法提取图标，返回默认图标
                    return self._get_default_icon()
            else:
                # 非 Windows 系统返回默认图标
                return self._get_default_icon()

        except Exception as e:
            print(f'提取图标失败: {str(e)}')
            return self._get_default_icon()

    def _get_default_icon(self):
        '''
        获取默认图标（Base64）
        :return: Base64 编码的默认图标
        '''
        # 创建一个简单的灰色默认图标
        img = Image.new('RGB', (48, 48), color=(200, 200, 200))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
