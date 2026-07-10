#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2025-06-24 15:44:44
LastEditTime: 2025-06-26 15:46:23
Description: 数据库类 - TinyDB
usage: 运行前，请确保本机已经搭建Python3开发环境，且已经安装 tinydb, cryptography 模块。
'''

import json
import os

from cryptography.fernet import Fernet
from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from api.db.json.models import Models
from pyapp.config.config import Config
from pyapp.db.keymanager import getDBKey


class DB:
    '''数据库操作类'''

    dbPath = ''    # 数据库路径

    def init(self):
        '''初始化数据库'''
        # 如果没有数据库，则新建数据库
        if Config.devEnv:
            # 开发环境
            dbDir = os.path.join(Config.staticDir, 'db', 'json')
        else:
            # 生产环境
            dbDir = os.path.join(Config.appDataDir, 'static', 'db', 'json')

        if not os.path.isdir(dbDir):
            # 新建本地电脑文件夹
            os.makedirs(dbDir)
        DB.dbPath = os.path.join(dbDir, 'base.json')    # 本地数据库

        if Config.ifCoverDB:
            # 显式要求重置时，跳过读取旧库。此路径允许在密钥变更或旧库
            # 损坏后重建；普通打开路径仍会拒绝覆盖无法解密的已有数据库。
            with SessionDB(reset=True) as db:
                # 创建一个空的表，名称为 ppx_storage_var
                db.table(Models.PPXStorageVar)
        elif not os.path.exists(DB.dbPath):
            # 数据库不存在时，新建数据库。
            with SessionDB() as db:
                # 创建一个空的表，名称为 ppx_storage_var
                db.table(Models.PPXStorageVar)


class SessionDBError(RuntimeError):
    '''加密数据库无法安全读取或初始化时抛出的异常'''


# 加密数据库
class SessionDB:
    def __init__(self, file_path=None, reset=False):
        '''
        创建加密数据库会话。

        ``reset=True`` 是显式的破坏性操作：忽略已有文件内容并在会话
        正常退出时用空库覆盖它。常规调用必须保持默认值，以便已有库
        无法读取或解密时不会被意外覆盖。
        '''
        if file_path is None:
            if Config.devEnv:
                # 开发环境
                dbDir = os.path.join(Config.staticDir, 'db', 'json')
            else:
                # 生产环境
                dbDir = os.path.join(Config.appDataDir, 'static', 'db', 'json')
            file_path = os.path.join(dbDir, 'base.json')
        self.file_path = file_path
        self.reset = reset
        self._db = None
        self._can_persist = False
        self.cipher = Fernet(getDBKey())    # 密钥：运行时从用户数据目录读取/生成，兼容历史硬编码密钥

    def _encrypt(self, data):
        return self.cipher.encrypt(json.dumps(data).encode())

    def _decrypt(self, data):
        return json.loads(self.cipher.decrypt(data).decode())

    def __enter__(self):
        # 同一实例被重复使用时，不能保留上一次成功打开的可写状态。
        self._db = None
        self._can_persist = False
        if self.reset:
            data = {}
        else:
            try:
                with open(self.file_path, 'rb') as f:
                    encrypted_data = f.read()
            except FileNotFoundError as e:
                # 仅在目标文件确实不存在时初始化空库。悬空链接等已存在但
                # 无法读取的路径不能当作新库处理，否则会覆盖用户原有数据。
                if os.path.lexists(self.file_path):
                    raise SessionDBError(f'无法读取数据库文件：{self.file_path}') from e
                data = {}
            except OSError as e:
                raise SessionDBError(f'无法读取数据库文件：{self.file_path}') from e
            else:
                try:
                    data = self._decrypt(encrypted_data)
                except Exception as e:
                    raise SessionDBError(f'无法解密或解析数据库文件：{self.file_path}') from e

                if not isinstance(data, dict):
                    raise SessionDBError(f'数据库文件格式无效：{self.file_path}')

        self._db = TinyDB(storage=MemoryStorage)
        try:
            self._db.storage.write(data)
        except Exception as e:
            self._db = None
            raise SessionDBError(f'无法初始化数据库：{self.file_path}') from e
        self._can_persist = True
        return self._db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._db is not None and self._can_persist:
            data = self._db.storage.read()
            with open(self.file_path, 'wb') as f:
                f.write(self._encrypt(data))
        return False
