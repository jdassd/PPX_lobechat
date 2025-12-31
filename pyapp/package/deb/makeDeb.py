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
import shutil
import subprocess
import sys
from pathlib import Path

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

# 使用 pathlib 和 shutil 进行文件操作，避免 shell 注入风险
buildPath = Path(buildDir)
scriptPath = Path(scriptDir)
logoFile = Path(logoPath)

# 创建目录结构
(buildPath / 'bin').mkdir(parents=True, exist_ok=True)
(buildPath / appName / 'DEBIAN').mkdir(parents=True, exist_ok=True)
(buildPath / appName / 'opt' / appName / 'bin').mkdir(parents=True, exist_ok=True)
(buildPath / appName / 'usr' / 'share' / 'applications').mkdir(parents=True, exist_ok=True)
(buildPath / appName / 'usr' / 'share' / 'icons' / 'hicolor' / '128x128' / 'apps').mkdir(parents=True, exist_ok=True)

# 移动可执行文件到 bin 目录
src_exe = buildPath / appDistName
dst_exe = buildPath / 'bin' / appDistName
if src_exe.exists():
    shutil.move(str(src_exe), str(dst_exe))

# 复制文件
shutil.copy2(str(dst_exe), str(buildPath / appName / 'opt' / appName / 'bin' / appName))
shutil.copy2(str(scriptPath / 'control'), str(buildPath / appName / 'DEBIAN' / 'control'))

postinst_src = scriptPath / 'postinst'
postinst_dst = buildPath / appName / 'DEBIAN' / 'postinst'
shutil.copy2(str(postinst_src), str(postinst_dst))
postinst_dst.chmod(0o755)

shutil.copy2(str(scriptPath / f'{appName}.desktop'), str(buildPath / appName / 'usr' / 'share' / 'applications' / f'{appName}.desktop'))
shutil.copy2(str(logoFile), str(buildPath / appName / 'usr' / 'share' / 'icons' / 'hicolor' / '128x128' / 'apps' / f'{appName}.png'))

# 构建 deb 包
subprocess.run(['dpkg-deb', '--build', appName], cwd=str(buildPath), check=True)

# 清理并重命名
shutil.rmtree(str(buildPath / appName), ignore_errors=True)
shutil.move(str(buildPath / 'bin' / appDistName), str(buildPath / appDistName))
shutil.rmtree(str(buildPath / 'bin'), ignore_errors=True)

shutil.move(str(buildPath / f'{appName}.deb'), str(buildPath / f'{appName}-V{appVersion}_Linux.deb'))

