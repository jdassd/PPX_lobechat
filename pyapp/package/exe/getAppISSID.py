#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-04-25 10:25:55
LastEditTime: 2025-06-26 16:00:00
Description: 生成 appISSID 打包唯一编号。

    appISSID 为 Inno Setup 安装包的唯一 GUID，需在打包时由 getIss.py 从 config.py 读取，
    因此仍写入 config.py。本脚本仅在 appISSID 为空（未生成）时写入一次，
    且使用精确正则匹配 + 异常处理，避免历史版本中“全局 replace、写入失败无提示”的健壮性隐患。
'''
import random
import re
from pathlib import Path


class GetAPPISSID:
    '''生成 appISSID 打包唯一编号'''

    def getItem(self, k=4):
        '''从0123456789ABCDEF中随机获取k个字符组成一个新的字符串'''
        itemList = random.choices(population="0123456789ABCDEF", k=k)
        return ''.join(itemList)

    def getAppISSID(self):
        '''生成 appISSID 打包唯一编号'''
        return f'{self.getItem(8)}-{self.getItem(4)}-{self.getItem(4)}-{self.getItem(4)}-{self.getItem(12)}'

    def run(self):
        '''写入 pyapp/config/config.py（仅当 appISSID 为空时生成一次）'''
        configPath = Path(__file__).absolute().parent.parent.parent.joinpath('config', 'config.py')
        try:
            with open(configPath, 'r', encoding='UTF-8') as f:
                configContent = f.read()
        except OSError as e:
            print(f'GetAPPISSID Error => 读取配置文件失败: {e}')
            return

        # 仅在 appISSID 为空字符串时写入，避免覆盖已生成的编号（生成后请勿修改）。
        # 使用精确匹配 appISSID = ''，且限制只替换一次，防止误伤其他内容。
        newContent, count = re.subn(
            r"appISSID = ''",
            f"appISSID = '{self.getAppISSID()}'",
            configContent,
            count=1,
        )

        if count == 0:
            # appISSID 已存在，无需生成，保持幂等
            print('GetAPPISSID => appISSID 已存在，跳过生成')
            return

        try:
            with open(configPath, 'w', encoding='UTF-8') as f:
                f.write(newContent)
        except OSError as e:
            print(f'GetAPPISSID Error => 写入配置文件失败: {e}')


if __name__ == '__main__':
    GetAPPISSID().run()
