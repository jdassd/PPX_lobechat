#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
FilePath: /PPX/pyapp/update/update.py
Author: 潘高
LastEditors: 潘高
Date: 2023-03-23 21:24:30
LastEditTime: 2023-06-01 15:55:30
Description: 应用更新
usage: 运行前，请确保本机已经搭建Python3开发环境，且已经安装 httpx 模块。
        详细教程请移步至 https://blog.pangao.vip/Python环境搭建及模块安装/
'''

import hashlib
import os
import re
import shlex
import subprocess
from urllib.parse import urlparse

import httpx

from pyapp.config.config import Config


class AppUpdate:
    '''程序升级'''

    cancelDownload = False    # 是否取消下载

    def check(self, payload=None):
        '''检查是否有更新：0=>有新版本; -1=>联网失败; 1=>已经是最新版本'''
        channel = self.__resolve_channel(payload)
        resNewInfo = self.__getNewInfo(channel)
        if not resNewInfo['status']:
            # 联网失败
            return {'code': -1, 'msg': '连接服务器失败，请稍后再试'}
        else:
            oldVersion = Config.appVersion
            newVersion = resNewInfo['version']
            ifUpdate = self.__compareVersion(oldVersion, newVersion)    # 判断是否需要更新
            if not ifUpdate:
                # 已是最新版本
                return {'code': 1, 'msg': f'{oldVersion}已是最新版本', 'channel': channel}
            else:
                return {
                    'code': 0,
                    'msg': f'有新版{newVersion}可供更新，当前版本为{oldVersion}。',
                    'htmlUrl': resNewInfo['htmlUrl'],
                    'assets': resNewInfo['assets'],
                    'body': resNewInfo['body'],
                    'channel': channel,
                    'version': newVersion
                }

    def run(self, payload=None):
        '''执行更新：0=>下载程序包成功; -1=>联网失败; -2=>下载程序包失败; 1=>已经是最新版本'''
        resCheck = self.check(payload)
        if resCheck['code'] == 0:
            resApp = self.__getApp(resCheck['assets'])
            if not resApp or not resApp.get('status'):
                msg = str(resApp.get('msg', '未知错误')) if resApp else '未找到适用的安装包'
                return {'code': -2, 'msg': '下载程序包失败: ' + msg, 'channel': resCheck.get('channel')}
            else:
                return {
                    'code': 0,
                    'msg': '下载程序包成功并通过 SHA-256 校验',
                    'downloadPath': resApp['downloadPath'],
                    'sha256': resApp.get('sha256'),
                    'channel': resCheck.get('channel')
                }
        else:
            return resCheck

    def cancel(self):
        '''取消下载'''
        AppUpdate.cancelDownload = True

    def __resolve_channel(self, payload=None):
        if isinstance(payload, dict):
            value = str(payload.get('channel') or '').strip().lower()
            if value in ('stable', 'beta'):
                return value
        if isinstance(payload, str):
            value = str(payload).strip().lower()
            if value in ('stable', 'beta'):
                return value
        return 'stable'

    def __getNewInfo(self, channel='stable'):
        '''获取服务端版本信息'''
        try:
            # 15秒后连接超时，15秒后读取超时
            if channel == 'beta':
                r = httpx.get(Config.appReleasesUrl, timeout=(15, 15))
                res_json = r.json()
                if not isinstance(res_json, list):
                    return {'status': False, 'msg': '获取测试版信息失败'}
                # 取最新的预发布版本
                target = None
                for item in res_json:
                    if isinstance(item, dict) and item.get('prerelease') and not item.get('draft'):
                        target = item
                        break
                if not target:
                    return {'status': False, 'msg': '暂无可用测试版'}
                version = target.get('tag_name') or target.get('name')
                html_url = target.get('html_url')
                assets = target.get('assets') or []
                body = target.get('body') or ''
                return {
                    'status': True,
                    'version': version,
                    'htmlUrl': html_url,
                    'assets': assets,
                    'body': body
                }

            r = httpx.get(Config.appUpdateUrl, timeout=(15, 15))
            resJson = r.json()
            version = resJson.get('tag_name') or resJson.get('name')    # 版本号
            htmlUrl = resJson.get('html_url')    # 下载页面
            assets = resJson.get('assets') or []    # 下载资源
            body = resJson.get('body') or ''    # 版本介绍
            return {
                'status': True,
                'version': version,
                'htmlUrl': htmlUrl,
                'assets': assets,
                'body': body
            }
        except Exception as e:
            return {
                'status': False,
                'msg': str(e)
            }

    def __compareVersion(self, oldVersion, newVersion):
        '''判断是否需要更新'''
        def parse(version):
            raw = str(version or '').strip().lower()
            raw = raw.lstrip('v')
            # 支持预发布版本: 1.2.3-beta.1
            if '-' in raw:
                raw = raw.split('-', 1)[0]
            parts = raw.split('.')
            if len(parts) < 3:
                return None
            try:
                return int(parts[0]), int(parts[1]), int(parts[2])
            except (ValueError, TypeError):
                return None

        old_parsed = parse(oldVersion)
        new_parsed = parse(newVersion)
        if not old_parsed or not new_parsed:
            return False

        oldMajor, oldMinor, oldPatch = old_parsed
        newMajor, newMinor, newPatch = new_parsed

        if newMajor > oldMajor:
            return True
        if newMajor < oldMajor:
            return False

        if newMinor > oldMinor:
            return True
        if newMinor < oldMinor:
            return False

        return newPatch > oldPatch

    def __getApp(self, assetsList):
        '''获取程序包'''
        # 判断更新哪个系统版本。Linux 仅为 Debian/Ubuntu 系选择 .deb 包。
        system_extensions = {
            'Windows': '.exe',
            'Darwin': '.dmg'
        }
        if Config.appSystem == 'Linux':
            if not self.__isDebianOrUbuntu():
                return {
                    'status': False,
                    'msg': '当前 Linux 发行版不支持自动更新；自动更新仅支持 Debian/Ubuntu 系的 .deb 安装包，请前往发布页面下载适合当前发行版的安装包并手动安装。'
                }
            appExt = '.deb'
        else:
            appExt = system_extensions.get(Config.appSystem)
        if appExt is None:
            return {
                'status': False,
                'msg': f'当前系统 {Config.appSystem or "未知系统"} 不支持自动更新（仅支持 Windows、macOS 和 Linux）'
            }

        for assets in assetsList:
            if not isinstance(assets, dict):
                continue
            name = str(assets.get('name') or '')
            ext = os.path.splitext(name)[-1].lower()
            if ext == appExt:
                safe_name = self.__safeAssetName(name, appExt)
                if not safe_name:
                    return {'status': False, 'msg': '安装包文件名不安全，已拒绝下载'}
                try:
                    size = int(assets.get('size') or 0)
                except (TypeError, ValueError):
                    size = 0
                size = size if size > 0 else None
                url = assets.get('browser_download_url')
                if not url:
                    return {'status': False, 'msg': f'安装包 {name} 缺少下载地址'}
                if not self.__trustedDownloadUrl(url):
                    return {'status': False, 'msg': '安装包下载地址不可信，仅允许 GitHub HTTPS 地址'}
                expected_sha256 = self.__assetSha256(assets)
                if not expected_sha256:
                    return {'status': False, 'msg': '发布资产缺少有效的 GitHub SHA-256 摘要，已拒绝下载'}
                # 确保下载目录存在
                if not os.path.exists(Config.downloadDir):
                    try:
                        os.makedirs(Config.downloadDir, exist_ok=True)
                    except Exception as e:
                        return {'status': False, 'msg': f'创建下载目录失败: {str(e)}'}
                download_root = os.path.abspath(Config.downloadDir)
                downloadPath = os.path.abspath(os.path.join(download_root, safe_name))
                try:
                    if os.path.commonpath((download_root, downloadPath)) != download_root:
                        return {'status': False, 'msg': '安装包保存路径不安全，已拒绝下载'}
                except ValueError:
                    return {'status': False, 'msg': '安装包保存路径不安全，已拒绝下载'}
                # 超时重连3次
                timeoutCount = 0
                while timeoutCount < 3:
                    resDownload = self.__download(url, downloadPath, size, expected_sha256)
                    if resDownload['msg'] == '连接超时':
                        timeoutCount += 1
                    else:
                        return resDownload
                # 超时3次后返回失败
                return {'status': False, 'msg': '连接超时，请稍后重试'}
        # 未找到匹配的安装包
        return {'status': False, 'msg': f'未找到适用于当前系统的安装包（需要 {appExt} 文件）'}

    @staticmethod
    def __safeAssetName(name, expected_extension):
        '''只接受不含目录片段、且扩展名符合当前平台的发布文件名。'''
        raw = str(name or '').strip()
        normalized = raw.replace('\\', '/')
        if not normalized or '/' in normalized or normalized in ('.', '..'):
            return ''
        if os.path.splitext(normalized)[-1].lower() != expected_extension:
            return ''
        return normalized

    @staticmethod
    def __trustedDownloadUrl(url):
        '''更新包只能从 GitHub 官方 HTTPS 域名下载。'''
        try:
            parsed = urlparse(str(url))
        except ValueError:
            return False
        host = (parsed.hostname or '').lower()
        return parsed.scheme == 'https' and (
            host in ('github.com', 'api.github.com') or host.endswith('.githubusercontent.com')
        )

    @staticmethod
    def __assetSha256(asset):
        '''GitHub Release Asset exposes digest as ``sha256:<64 hex>``.'''
        if not isinstance(asset, dict):
            return ''
        digest = str(asset.get('digest') or '').strip().lower()
        match = re.fullmatch(r'sha256:([0-9a-f]{64})', digest)
        return match.group(1) if match else ''

    @staticmethod
    def __isDebianOrUbuntu():
        '''仅识别可使用 .deb 安装包的 Debian/Ubuntu 系发行版。'''
        release = {}
        try:
            with open('/etc/os-release', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, value = line.split('=', 1)
                    if key not in ('ID', 'ID_LIKE'):
                        continue
                    try:
                        value = ' '.join(shlex.split(value, comments=False, posix=True))
                    except ValueError:
                        value = value.strip().strip('\"\'')
                    release[key] = value.lower()
        except (OSError, UnicodeError):
            return False

        identifiers = set(release.get('ID_LIKE', '').split())
        identifiers.add(release.get('ID', ''))
        return bool(identifiers.intersection({'debian', 'ubuntu'}))

    def __download(self, url, downloadPath, size, expected_sha256):
        '''下载大文件'''
        from api.api import API
        api = API()
        AppUpdate.cancelDownload = False
        partial_path = downloadPath + '.part'

        def cleanup_partial():
            try:
                os.remove(partial_path)
            except FileNotFoundError:
                pass

        cleanup_partial()
        try:
            hasher = hashlib.sha256()
            with open(partial_path, "wb") as f:
                with httpx.Client(follow_redirects=True) as client:
                    with client.stream("GET", url, timeout=(5, 3600)) as r:
                        r.raise_for_status()
                        if not self.__trustedDownloadUrl(r.url):
                            raise httpx.HTTPError('下载重定向到了不可信地址')
                        downloadSize = 0
                        response_size = r.headers.get('content-length')
                        try:
                            response_size = int(response_size) if response_size else 0
                        except (TypeError, ValueError):
                            response_size = 0
                        total_size = size or (response_size if response_size > 0 else None)
                        # 64KB 块能显著减少大安装包的 Python 循环和 UI 通知开销。
                        for chunk in r.iter_bytes(chunk_size=64 * 1024):
                            if AppUpdate.cancelDownload:
                                raise InterruptedError('取消更新')
                            if chunk:
                                f.write(chunk)
                                hasher.update(chunk)
                                downloadSize += len(chunk)
                            infoPy2jsDict = {
                                'sizeShow': self.bytes2Size(downloadSize)
                                + (' / ' + self.bytes2Size(total_size) if total_size else ' / 未知大小'),
                                'percentage': min(99, int(downloadSize / total_size * 100)) if total_size else 0,
                            }
                            api.system_py2js('py2js_updateAppProgress', infoPy2jsDict)
                        f.flush()
                        os.fsync(f.fileno())
            if size and downloadSize != size:
                cleanup_partial()
                return {
                    'status': False,
                    'msg': f'安装包大小校验失败（期望 {self.bytes2Size(size)}，实际 {self.bytes2Size(downloadSize)}）'
                }
            actual_sha256 = hasher.hexdigest()
            if actual_sha256 != expected_sha256:
                cleanup_partial()
                return {
                    'status': False,
                    'msg': f'安装包 SHA-256 校验失败（期望 {expected_sha256}，实际 {actual_sha256}）'
                }
            os.replace(partial_path, downloadPath)
            api.system_py2js(
                'py2js_updateAppProgress',
                {'sizeShow': self.bytes2Size(downloadSize), 'percentage': 100}
            )
            return {'status': True, 'msg': '下载成功并通过 SHA-256 校验', 'downloadPath': downloadPath, 'sha256': actual_sha256}
        except InterruptedError:
            cleanup_partial()
            return {'status': False, 'msg': '取消更新'}
        except httpx.TimeoutException:
            cleanup_partial()
            return {'status': False, 'msg': '连接超时'}
        except httpx.NetworkError:
            cleanup_partial()
            return {'status': False, 'msg': '联网失败'}
        except httpx.HTTPError as e:
            cleanup_partial()
            return {'status': False, 'msg': str(e)}
        except Exception as e:
            cleanup_partial()
            return {'status': False, 'msg': str(e)}

    def bytes2Size(self, bytes):
        '''将字节大小转为带单位的值'''
        try:
            bytes = max(0, int(bytes or 0))
        except (TypeError, ValueError):
            bytes = 0
        if bytes < 1024:    # 比特
            bytes = str(round(bytes, 0)) + ' B'    # 字节
        elif bytes >= 1024 and bytes < 1024 * 1024:
            bytes = str(round(bytes / 1024, 0)) + ' KB'    # 千字节
        elif bytes >= 1024 * 1024 and bytes < 1024 * 1024 * 1024:
            bytes = str(round(bytes / 1024 / 1024, 1)) + ' MB'    # 兆字节
        elif bytes >= 1024 * 1024 * 1024 and bytes < 1024 * 1024 * 1024 * 1024:
            bytes = str(round(bytes / 1024 / 1024 / 1024, 2)) + ' GB'    # 千兆字节
        elif bytes >= 1024 * 1024 * 1024 * 1024 and bytes < 1024 * 1024 * 1024 * 1024 * 1024:
            bytes = str(round(bytes / 1024 / 1024 / 1024 / 1024, 2)) + ' TB'    # 太字节
        elif bytes >= 1024 * 1024 * 1024 * 1024 * 1024 and bytes < 1024 * 1024 * 1024 * 1024 * 1024 * 1024:
            bytes = str(round(bytes / 1024 / 1024 / 1024 / 1024 / 1024, 2)) + ' PB'    # 拍字节
        elif bytes >= 1024 * 1024 * 1024 * 1024 * 1024 * 1024 and bytes < 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024:
            bytes = str(round(bytes / 1024 / 1024 / 1024 / 1024 / 1024 / 1024, 2)) + ' EB'    # 艾字节
        return bytes

    def IfMacAppleM(self):
        '''判断是苹果M芯片还是Intel芯片'''
        p = subprocess.Popen(['sysctl', 'machdep.cpu.brand_string'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        res = out.decode('UTF-8')
        if res.find('Apple M') > -1:
            return True
        else:
            return False
