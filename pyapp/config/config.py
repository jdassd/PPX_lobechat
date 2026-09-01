#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2022-03-21 16:54:23
LastEditTime: 2025-06-26 15:47:25
Description: 配置文件
usage:
    from pyapp.config.config import Config
    print(Config.rootDir)
'''

import os
import platform
import sys


class Config:
    '''配置文件'''

    ##
    # 程序基础配置信息
    ##
    appName = '多功能工具箱'  # 应用名称
    appNameEN = 'tools'    # 应用名称-英文（用于生成缓存文件夹，必须是英文）
    appVersion = "v2.7.0"  # 应用版本号
    appDeveloper = "Jdassd"  # 应用开发者
    appBlogs = "https://baidu.com"  # 个人博客
    appPackage = 'ppx.jdassd'    # 应用包名，用于在本地电脑生成 vip.pangao.ppx 唯一文件夹
    appUpdateUrl = 'https://api.github.com/repos/jdassd/PPX_lobechat/releases/latest'    # 获取稳定版更新信息
    appReleasesUrl = 'https://api.github.com/repos/jdassd/PPX_lobechat/releases'    # 获取 Release 列表（含测试版）
    appISSID = '05027E0B-CD45-DE45-B2BD-30B885810FE5'    # Inno Setup 打包唯一编号。在执行 pnpm run init 之前，请设置为空，程序会自动生成唯一编号，生成后请勿修改！！！

    ##
    # 系统配置信息（不需要修改，可以自动获取）
    ##
    cpuArch = platform.processor()    # 本机CPU架构
    appSystem = platform.system()    # 本机系统类型
    appIsMacOS = appSystem == 'Darwin'    # 是否为macOS系统
    codeDir = os.path.abspath(getattr(sys, '_MEIPASS', sys.path[0] or os.getcwd()))    # 源码根目录或 PyInstaller 资源根目录
    staticDir = os.path.join(codeDir, 'static')    # 代码根目录下的static文件夹的绝对路径
    appDataDir = ''    # 电脑上可持久使用的隐藏目录
    downloadDir = ''    # 电脑上的下载目录

    ##
    # 其他配置信息
    ##
    devPort = '5173'    # 开发环境中的前端页面端口
    devEnv = True    # 是否为开发环境，不需要手动更改，在程序运行的时候自动判断
    ifCoverDB = False    # 是否覆盖电脑上存储的数据库，默认不覆盖。只有在变更数据库密码或者数据库改动非常大，不得已的情况下才建议覆盖数据库
    typeDB = 'json'    # 数据库类型，目前支持: json, sql
    pwDB = b''    # 数据库密码占位符（已废弃，请勿在此填写真实密钥）。typeDB=json 时，真实密钥在运行时由 pyapp/db/keymanager.py 从用户数据目录的 .dbkey 文件读取/生成，不再保存于源码中

    ##
    # 函数
    ##
    def init(self):
        '''初始化'''
        # 获取电脑上的目录
        self.getDir()

    def getDir(self):
        '''获取电脑上的目录'''
        homeDir = os.path.expanduser('~')
        if not homeDir or homeDir == '~':
            homeDir = os.getcwd()

        if Config.appSystem == 'Darwin':
            # Mac系统
            downloadDir = os.path.join(homeDir, 'Downloads')
            appDataDir = os.path.join(homeDir, 'Library', 'Application Support', Config.appPackage+'.'+Config.appNameEN)
        elif Config.appSystem == 'Windows':
            # win系统
            userProfile = os.getenv('USERPROFILE') or homeDir
            appDataRoot = os.getenv('APPDATA') or os.path.join(userProfile, 'AppData', 'Roaming')
            downloadDir = os.path.join(userProfile, 'Downloads')
            appDataDir = os.path.join(appDataRoot, Config.appPackage+'.'+Config.appNameEN)
        else:
            # Linux 及其它类 Unix 系统使用安全的用户目录回退，避免未知平台变量未初始化。
            downloadDir = os.path.join(homeDir, 'Downloads')
            appDataDir = os.path.join(homeDir, '.'+Config.appPackage+'.'+Config.appNameEN)

        os.makedirs(appDataDir, exist_ok=True)
        Config.appDataDir = appDataDir    # 电脑上可持久使用的隐藏目录
        Config.downloadDir = downloadDir    # 电脑上的下载目录
