#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2025-06-18 17:11:35
LastEditTime: 2025-06-26 16:00:00
Description: 数据库密码初始化（保留以兼容 pnpm run init 流程）。

    说明：从本版本起，数据库密钥不再写入源码 config.py，而是在程序运行时
    由 pyapp/db/keymanager.py 从用户数据目录的 .dbkey 文件读取/生成。
    因此本脚本不再向源码写入任何真实密钥，仅确保 config.py 中的 pwDB 为占位空值，
    并清理开发环境下可能残留的旧明文密钥。
'''

from pathlib import Path


class GetKeyDB:
    '''数据库密码初始化'''

    def run(self):
        '''确保 config.py 中 pwDB 为占位空值，不再写入真实密钥'''
        configPath = Path(__file__).absolute().parent.parent.parent.joinpath('config', 'config.py')
        try:
            with open(configPath, 'r', encoding='UTF-8') as f:
                configContent = f.read()
        except OSError as e:
            print(f'GetKeyDB Error => 读取配置文件失败: {e}')
            return

        # 历史版本曾把真实密钥硬编码进源码，这里统一清空为占位空值，避免密钥进入仓库。
        # 仅处理形如  pwDB = b'...'  的赋值行，置空为  pwDB = b''
        import re
        newContent, count = re.subn(
            r"pwDB = b'[^']*'",
            "pwDB = b''",
            configContent,
            count=1,
        )

        if count > 0 and newContent != configContent:
            try:
                with open(configPath, 'w', encoding='UTF-8') as f:
                    f.write(newContent)
            except OSError as e:
                print(f'GetKeyDB Error => 写入配置文件失败: {e}')
                return

        # 清理开发环境下可能残留、由旧密钥加密的数据库（与历史行为保持一致）
        dbPath = Path(__file__).absolute().parent.parent.parent.parent.joinpath('static', 'db', 'json', 'base.json')
        if dbPath.exists():
            try:
                dbPath.unlink()
            except OSError as e:
                print(f'GetKeyDB Error => 删除旧数据库失败: {e}')


if __name__ == '__main__':
    GetKeyDB().run()
