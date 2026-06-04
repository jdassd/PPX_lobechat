#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2022-03-23 09:05:53
LastEditTime: 2024-09-08 20:47:03
Description: 生成 .spec APP 配置文件
'''

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import Config
try:
    # Generate platform icons from project root logo.png into pyapp/icon/.
    from icon.generate_icons import generate_logo_icons
except Exception:
    generate_logo_icons = None


parser = argparse.ArgumentParser()
parser.add_argument("-m", "--mac", action="store_true", dest="if_mac", help="if_mac")
parser.add_argument("-l", "--linux", action="store_true", dest="if_linux", help="if_linux")
args = parser.parse_args()
ifMac = args.if_mac
ifLinux = args.if_linux

# Ensure icon files are generated from root logo.png before packaging.
if 'generate_logo_icons' in globals() and generate_logo_icons is not None:
    generate_logo_icons()


buildPath = 'build'  # dist directory (relative)
console = True  # show console window（临时：beta 调试版开启控制台以显示白屏诊断输出；正式版本应改回 False）
appName = Config.appName  # project name (display)
appCollectName = Config.appNameEN  # dist folder name
version = Config.appVersion  # version string
logoExt = 'icns' if ifMac else 'png' if ifLinux else 'ico'

# Extra binaries and data folders
addDll = ''
addModules = "('../../gui/dist', 'web'), ('../../static', 'static')"


# Common first part of .spec content
def specFirstPart():
    return f'''
# -*- mode: python ; coding: utf-8 -*-

import os

import PyInstaller.config

# Dist directory (relative)
buildPath = '{buildPath}'
PyInstaller.config.CONF['distpath'] = buildPath

# Work path (PyInstaller cache)
cachePath = os.path.join(buildPath, 'cache')
if not os.path.exists(cachePath):
    os.makedirs(cachePath)
PyInstaller.config.CONF['workpath'] = cachePath

# Icon relative path
icoPath = os.path.join('..', 'icon', 'logo.{logoExt}')

# App name and version
appName = '{appName}'
version = '{version}'


a = Analysis(['../../main.py'],
            pathex=[],
            binaries=[{addDll}],
            datas=[{addModules}],
            hiddenimports=[],
            hookspath=[],
            hooksconfig={{}},
            runtime_hooks=[],
            excludes=[],
            win_no_prefer_redirects=False,
            win_private_assemblies=False,
            noarchive=False)
pyz = PYZ(a.pure, a.zipped_data)

'''


# Bundle as a single .app (macOS)
def specPackagePartAPP():
    return f'''
exe = EXE(pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=appName,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console={console},
        disable_windowed_traceback=False,
        target_arch=None,  # x86_64, arm64, universal2
        codesign_identity=None,
        entitlements_file=None)
coll = COLLECT(exe,
                a.binaries,
                a.zipfiles,
                a.datas,
                strip=False,
                upx=True,
                upx_exclude=[],
                name='{appCollectName}')
app = BUNDLE(coll,
            name=appName+'.app',
            icon=icoPath,
            version=version,
            bundle_identifier=None)

'''


# Bundle as a single .exe
def specPackagePartEXE():
    return f'''
exe = EXE(pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=appName,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console={console},
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icoPath)

'''


# Bundle as a folder
def specUnpackagePartEXE():
    return f'''
exe = EXE(pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=appName,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console={console},
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icoPath)
coll = COLLECT(exe,
            a.binaries,
            a.zipfiles,
            a.datas,
            strip=False,
            upx=True,
            upx_exclude=[],
            name='{appCollectName}')

'''


# spec output directory
specDir = os.path.dirname(__file__)


if ifMac:
    console = False  # no console window
    # macos.spec
    with open(os.path.join(specDir, 'macos.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartAPP())

    console = True  # with console window
    # macos-pre.spec
    with open(os.path.join(specDir, 'macos-pre.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartAPP())
elif ifLinux:
    # For Linux, use English name as executable name to avoid conflicts with deb packaging
    appName = appCollectName
    console = False  # no console window
    # linux.spec
    with open(os.path.join(specDir, 'linux.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartEXE())

    console = True  # with console window
    # linux-pre.spec
    with open(os.path.join(specDir, 'linux-pre.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartEXE())
else:
    console = False  # no console window
    # windows.spec
    with open(os.path.join(specDir, 'windows.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartEXE())
    # windows-folder.spec
    with open(os.path.join(specDir, 'windows-folder.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specUnpackagePartEXE())

    console = True  # with console window
    # windows-pre.spec
    with open(os.path.join(specDir, 'windows-pre.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartEXE())
    # windows-folder-pre.spec
    with open(os.path.join(specDir, 'windows-folder-pre.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specUnpackagePartEXE())

    console = False  # no console window
    # add missing cef binaries
    addDll = """
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/icudtl.dat', './'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/natives_blob.bin','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/subprocess.exe','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/libcef.dll','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/chrome_elf.dll','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/v8_context_snapshot.bin','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/cef.pak','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/cef_100_percent.pak','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/cef_200_percent.pak','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/cef_extensions.pak','./'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/icudtl.dat', './cefpython3'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/natives_blob.bin','./cefpython3'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/locales/en-US.pak','./locales'),
        ('../../pyapp/pyenv/pyenvCEF/Lib/site-packages/cefpython3/locales/zh-CN.pak','./locales')
    """
    # windows-cef.spec
    with open(os.path.join(specDir, 'windows-cef.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartEXE())
    # windows-folder-cef.spec
    with open(os.path.join(specDir, 'windows-folder-cef.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specUnpackagePartEXE())

    console = True  # with console window
    # windows-pre-cef.spec
    with open(os.path.join(specDir, 'windows-pre-cef.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specPackagePartEXE())
    # windows-folder-pre-cef.spec
    with open(os.path.join(specDir, 'windows-folder-pre-cef.spec'), 'w+', encoding='utf-8') as f:
        f.write(specFirstPart() + specUnpackagePartEXE())

