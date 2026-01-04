#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务相关 API
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict

from api.utils import api_error, api_success


class FinanceTool:
    """财务工具"""

    _digits = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
    _units = ['', '拾', '佰', '仟']
    _section_units = ['', '万', '亿', '兆']

    def _validate(self, options: Dict | None) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _parse_amount(self, raw) -> Decimal:
        if raw is None:
            raise ValueError('请输入金额')
        text = str(raw).strip()
        if not text:
            raise ValueError('请输入金额')
        text = text.replace(',', '').replace('￥', '').replace('RMB', '').replace('CNY', '')
        text = text.strip()
        if not text:
            raise ValueError('请输入金额')
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError('金额格式不正确') from exc
        if value.is_nan() or value.is_infinite():
            raise ValueError('金额无效')
        return value

    def _section_to_cn(self, section: int) -> str:
        result = ''
        unit_pos = 0
        zero = False
        while section > 0:
            digit = section % 10
            if digit == 0:
                if not zero and result:
                    result = f'{self._digits[0]}{result}'
                zero = True
            else:
                result = f'{self._digits[digit]}{self._units[unit_pos]}{result}'
                zero = False
            unit_pos += 1
            section //= 10
        return result

    def _integer_to_cn(self, num: int) -> str:
        if num == 0:
            return self._digits[0]
        result = ''
        zero = False
        section_pos = 0
        while num > 0:
            section = num % 10000
            if section == 0:
                if result:
                    zero = True
            else:
                section_str = self._section_to_cn(section)
                segment = f'{section_str}{self._section_units[section_pos]}'
                if zero:
                    result = f'{self._digits[0]}{result}'
                    zero = False
                if result and section < 1000:
                    result = f'{segment}{self._digits[0]}{result}'
                else:
                    result = f'{segment}{result}'
            num //= 10000
            section_pos += 1
        return result

    def _fraction_to_cn(self, fraction: int) -> str:
        jiao = fraction // 10
        fen = fraction % 10
        if jiao == 0 and fen == 0:
            return '整'
        result = ''
        if jiao > 0:
            result = f'{result}{self._digits[jiao]}角'
        elif fen > 0:
            result = f'{result}{self._digits[0]}'
        if fen > 0:
            result = f'{result}{self._digits[fen]}分'
        return result

    def finance_rmb_uppercase(self, options: Dict | None = None):
        """人民币金额转中文大写"""
        try:
            opts = self._validate(options)
            raw = opts.get('amount') or opts.get('value') or ''
            value = self._parse_amount(raw)
            negative = value < 0
            if negative:
                value = -value
            value = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            integer_part = int(value)
            fraction = int((value - Decimal(integer_part)) * 100)
            integer_cn = self._integer_to_cn(integer_part)
            fraction_cn = self._fraction_to_cn(fraction)
            result = f'{integer_cn}元{fraction_cn}'
            if negative:
                result = f'负{result}'
            result = f'人民币{result}'
            return api_success('转换完成', result=result, amount=str(value))
        except Exception as exc:
            return api_error(f'金额转换失败：{exc}')
