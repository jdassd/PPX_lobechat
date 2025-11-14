#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2024-09-09 21:06:15
LastEditTime: 2024-09-09 23:37:41
Description: 制作 linux 下的 deb 安装包
usage: 运行前，请确保本机已经搭建 Python3 开发环境，且已经安装必要模块
'''

import os
import sys

scriptDir = os.path.dirname(os.path.abspath(__file__))
pyappDir = os.path.dirname(os.path.dirname(scriptDir))
sys.path.append(pyappDir)
from config.config import Config
try:
    # Ensure icons (including Linux PNG) are generated from root logo.png.
    from icon.generate_icons import generate_logo_icons
except Exception:
    generate_logo_icons = None

appName = Config.appName  # 应用名称
appDistName = Config.appNameEN  # PyInstaller 输出的可执行文件名称
appVersion = Config.appVersion  # 应用版本号（例如 V5.3.0）
appVersion = appVersion[1:]  # 去掉第一位 V
appDeveloper = Config.appDeveloper  # 应用开发者
appBlogs = Config.appBlogs  # 个人博客

rootDir = os.path.dirname(pyappDir)

# 先根据根目录 logo.png 生成 pyapp/icon/logo.png
if 'generate_logo_icons' in globals() and generate_logo_icons is not None:
    generate_logo_icons()

logoPath = os.path.join(rootDir, 'pyapp', 'icon', 'logo.png')


# 生成软件包的控制文件
getControl = f"""
Package: {appName}
Version: {appVersion}
Section: base
Priority: optional
Architecture: all
Depends: python3
Maintainer: {appDeveloper}
Description: {appBlogs}

"""
with open(os.path.join(scriptDir, 'control'), 'w+', encoding='utf-8') as f:
    f.write(getControl)


# 生成桌面文件
getDesktop = f"""
[Desktop Entry]
Name={appName}
Comment={appBlogs}
Exec=/opt/{appName}/bin/{appName}
Icon=/usr/share/icons/hicolor/128x128/apps/{appName}.png
Terminal=false
Type=Application
Categories=Utility;  # 选择适当的类别

"""
with open(os.path.join(scriptDir, f'{appName}.desktop'), 'w+', encoding='utf-8') as f:
    f.write(getDesktop)


# 生成安装完成调用的 postinst 脚本
getPostinst = """
# !/bin/bash
# 更新桌面图标数据库
update-desktop-database /usr/share/applications || true
# 获取当前的用户名
username=`getent passwd \`who\` | head -n 1 | cut -d : -f 1`
# 判断桌面文件夹是否存在
if [ -d "/home/${username}/Desktop" ]; then
echo 'Desktop exist'
# 将桌面文件复制到桌面
cp """ + f'/usr/share/applications/{appName}.desktop' + """ /home/${username}/Desktop
else
echo '桌面文件夹不存在'
# 中文系统自动复制到中文桌面
cp """ + f'/usr/share/applications/{appName}.desktop' + """ /home/${username}/桌面
fi

"""
with open(os.path.join(scriptDir, 'postinst'), 'w+', encoding='utf-8') as f:
    f.write(getPostinst)


buildDir = os.path.join(rootDir, 'build')

os.system(f'mkdir -p {buildDir}/bin && mv {buildDir}/{appDistName} {buildDir}/bin/{appDistName}')
os.system(f'mkdir -p {buildDir}/{appName}/DEBIAN')
os.system(f'mkdir -p {buildDir}/{appName}/opt/{appName}/bin')
os.system(f'mkdir -p {buildDir}/{appName}/usr/share/applications')
os.system(f'mkdir -p {buildDir}/{appName}/usr/share/icons/hicolor/128x128/apps')
os.system(f'cp {buildDir}/bin/{appDistName} {buildDir}/{appName}/opt/{appName}/bin/{appName}')
os.system(f'cp {scriptDir}/control {buildDir}/{appName}/DEBIAN/control')
os.system(f'cp {scriptDir}/postinst {buildDir}/{appName}/DEBIAN/postinst && chmod 755 {buildDir}/{appName}/DEBIAN/postinst')
os.system(f'cp {scriptDir}/{appName}.desktop {buildDir}/{appName}/usr/share/applications/{appName}.desktop')
os.system(f'cp {logoPath} {buildDir}/{appName}/usr/share/icons/hicolor/128x128/apps/{appName}.png')

os.system(f'cd {buildDir}')
os.system(f'cd {buildDir} && dpkg-deb --build {appName}')

os.system(f'rm -fr {buildDir}/{appName} && mv {buildDir}/bin/{appDistName} {buildDir}/{appDistName} && rm -fr {buildDir}/bin')

os.system(f'mv {buildDir}/{appName}.deb {buildDir}/{appName}-V{appVersion}_Linux.deb')

