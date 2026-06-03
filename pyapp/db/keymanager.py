#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2025-06-26 16:00:00
LastEditTime: 2025-06-26 16:00:00
Description: 数据库密钥管理。
    把 Fernet 数据库加密密钥移出源码，运行时从用户数据目录读取/生成密钥文件。
    并兼容历史版本（v1.1.0 及更早）使用的硬编码密钥，确保老用户数据可正常读取。
usage:
    from pyapp.db.keymanager import getDBKey
    key = getDBKey()    # 返回 bytes 类型的 Fernet 密钥
'''

import os

from cryptography.fernet import Fernet

from pyapp.config.config import Config

# 历史版本（v1.1.0 及更早）的硬编码数据库密钥。
# 仅用于兼容解密老用户已加密的本地数据库，请勿用于新数据加密。
LEGACY_DB_KEY = b'fFXM1fxWfEeu7zoLTwS2ccgBPB2z6X6fCC7iB-W2ciM='

# 密钥文件名（存放于 Config.appDataDir 目录下，不进入源码、不入库）
KEY_FILENAME = '.dbkey'


def _getKeyFilePath():
    '''获取密钥文件的绝对路径'''
    return os.path.join(Config.appDataDir, KEY_FILENAME)


def _getLegacyDBPath():
    '''获取历史版本数据库文件的绝对路径（用于判断是否为老用户升级）'''
    if Config.devEnv:
        # 开发环境
        dbDir = os.path.join(Config.staticDir, 'db', 'json')
    else:
        # 生产环境
        dbDir = os.path.join(Config.appDataDir, 'static', 'db', 'json')
    return os.path.join(dbDir, 'base.json')


def _writeKeyFile(key):
    '''把密钥写入密钥文件'''
    keyPath = _getKeyFilePath()
    # appDataDir 由 Config.getDir() 保证存在，这里再兜底一次
    keyDir = os.path.dirname(keyPath)
    if keyDir and not os.path.isdir(keyDir):
        os.makedirs(keyDir)
    with open(keyPath, 'wb') as f:
        f.write(key)


def getDBKey():
    '''获取数据库 Fernet 密钥（bytes）

    解析逻辑：
    1. 若密钥文件已存在，直接读取返回（每台设备独立密钥）。
    2. 若密钥文件不存在：
       - 若本机已存在历史版本数据库（说明是老用户升级），
         则把历史硬编码密钥 LEGACY_DB_KEY 写入密钥文件，
         保证老数据可继续读取，零数据丢失、无需重新加密。
       - 否则（全新安装），随机生成一把新密钥写入密钥文件。
    '''
    keyPath = _getKeyFilePath()

    # 1. 密钥文件已存在，直接读取
    if os.path.exists(keyPath):
        with open(keyPath, 'rb') as f:
            key = f.read().strip()
        if key:
            return key
        # 文件存在但为空，按不存在处理，继续往下生成

    # 2. 密钥文件不存在（或为空）
    if os.path.exists(_getLegacyDBPath()):
        # 老用户升级：沿用历史硬编码密钥，保证旧数据库可读
        key = LEGACY_DB_KEY
    else:
        # 全新安装：生成每台设备独立的随机密钥
        key = Fernet.generate_key()

    _writeKeyFile(key)
    return key
