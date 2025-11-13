#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理相关 API
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import urllib.parse
from pathlib import Path
from typing import Dict, List

from api.utils import api_error, api_success, ensure_file_path


class TextTool:
    """文本工具"""

    _hash_algorithms = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
    }

    def _validate(self, options: Dict | None) -> Dict:
        if options is None:
            return {}
        if not isinstance(options, dict):
            raise ValueError('参数格式错误')
        return options

    def _split_words(self, text: str) -> List[str]:
        cleaned = re.sub(r'[_\-\s]+', ' ', text)
        chunks = re.split(r'(?=[A-Z])', cleaned)
        words = []
        for chunk in chunks:
            if not chunk:
                continue
            words.extend(re.findall(r'[A-Za-z0-9]+', chunk))
        return [w.lower() for w in words if w]

    def text_encode_decode(self, options: Dict | None = None):
        """编码/解码"""
        try:
            opts = self._validate(options)
            codec = str(opts.get('codecType', 'base64')).lower()
            operation = str(opts.get('operation', 'encode')).lower()
            content = opts.get('content', '') or ''
            if codec == 'base64':
                if operation == 'encode':
                    result = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                else:
                    result = base64.b64decode(content.encode('utf-8')).decode('utf-8')
            elif codec == 'url':
                if operation == 'encode':
                    result = urllib.parse.quote(content, safe='')
                else:
                    result = urllib.parse.unquote(content)
            elif codec == 'html':
                result = html.escape(content) if operation == 'encode' else html.unescape(content)
            elif codec == 'charset':
                direction = opts.get('direction', 'utf8_to_gbk')
                encoding_map = {
                    'utf8_to_gbk': ('utf-8', 'gbk'),
                    'gbk_to_utf8': ('gbk', 'utf-8'),
                }
                if direction not in encoding_map:
                    raise ValueError('不支持的字符集方向')
                src_enc, dst_enc = encoding_map[direction]
                result = content.encode(src_enc).decode(dst_enc)
            else:
                raise ValueError('未知的编码类型')
            return api_success('转换成功', result=result)
        except Exception as exc:
            return api_error(f'转换失败：{exc}')

    def _load_json(self, raw: str):
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    def _query_json(self, data, path: str):
        if not path:
            return data
        tokens = [token for token in re.split(r'\.|\[|\]', path) if token and token != '$']
        current = data
        for token in tokens:
            if token.isdigit() and isinstance(current, list):
                idx = int(token)
                current = current[idx]
                continue
            if isinstance(current, dict) and token in current:
                current = current[token]
                continue
            raise KeyError(f'路径 {token} 不存在')
        return current

    def text_format_json(self, options: Dict | None = None):
        """JSON 工具"""
        try:
            opts = self._validate(options)
            content = opts.get('content', '')
            operation = opts.get('operation', 'format')
            data = self._load_json(content)
            if operation == 'format':
                return api_success('美化完成', result=json.dumps(data, ensure_ascii=False, indent=2))
            if operation == 'compress':
                return api_success('压缩完成', result=json.dumps(data, ensure_ascii=False, separators=(',', ':')))
            if operation == 'validate':
                return api_success('JSON 格式校验通过', result=True)
            if operation == 'query':
                query = opts.get('path', '')
                result = self._query_json(data, query)
                return api_success('查询完成', result=result)
            raise ValueError('未知操作类型')
        except Exception as exc:
            return api_error(f'JSON 处理失败：{exc}')

    def text_case_transform(self, options: Dict | None = None):
        """大小写转换"""
        try:
            opts = self._validate(options)
            content = opts.get('content', '') or ''
            mode = str(opts.get('mode', 'upper')).lower()
            if mode == 'upper':
                result = content.upper()
            elif mode == 'lower':
                result = content.lower()
            elif mode == 'title':
                result = content.title()
            elif mode == 'sentence':
                result = content.capitalize()
            elif mode == 'camel':
                words = self._split_words(content)
                result = words[0] + ''.join(w.title() for w in words[1:]) if words else ''
            elif mode == 'pascal':
                result = ''.join(w.title() for w in self._split_words(content))
            elif mode == 'snake':
                result = '_'.join(self._split_words(content))
            elif mode == 'kebab':
                result = '-'.join(self._split_words(content))
            else:
                raise ValueError('未知转换类型')
            return api_success('转换成功', result=result)
        except Exception as exc:
            return api_error(f'转换失败：{exc}')

    def text_hash_calculate(self, options: Dict | None = None):
        """哈希计算"""
        try:
            opts = self._validate(options)
            source_type = opts.get('sourceType', 'text')
            algorithm = str(opts.get('hashType', 'md5')).lower()
            if algorithm not in self._hash_algorithms:
                raise ValueError('不支持的哈希算法')
            hasher = self._hash_algorithms[algorithm]()
            if source_type == 'file':
                file_info = opts.get('file')
                if isinstance(file_info, dict):
                    file_path = file_info.get('path')
                else:
                    file_path = file_info
                path = ensure_file_path(file_path)
                with path.open('rb') as handler:
                    for chunk in iter(lambda: handler.read(8192), b''):
                        hasher.update(chunk)
            else:
                content = opts.get('content', '') or ''
                hasher.update(content.encode('utf-8'))
            return api_success('哈希计算完成', result=hasher.hexdigest())
        except Exception as exc:
            return api_error(f'哈希计算失败：{exc}')
