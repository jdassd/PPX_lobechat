#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理相关 API
"""
from __future__ import annotations

import base64
import csv
import hashlib
import html
import json
import re
import urllib.parse
from collections import Counter, OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

try:  # pragma: no cover
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from api.utils import api_error, api_success, ensure_file_path


class TextTool:
    """文本工具"""

    _hash_algorithms = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256,
        'sha512': hashlib.sha512,
    }

    _regex_flags = {
        'ignorecase': re.IGNORECASE,
        'multiline': re.MULTILINE,
        'dotall': re.DOTALL,
        'unicode': re.UNICODE,
        'verbose': re.VERBOSE,
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

    def _compile_regex(self, pattern: str, flags: List[str] | str | None):
        flag_value = 0
        if isinstance(flags, str):
            flags = [flags]
        if isinstance(flags, list):
            for flag in flags:
                flag_value |= self._regex_flags.get(flag.lower(), 0)
        return re.compile(pattern, flag_value)

    def _resolve_timezone(self, label: str | None):
        if not label:
            return timezone.utc
        if ZoneInfo:
            try:
                return ZoneInfo(label)
            except Exception:
                pass
        match = re.match(r'UTC([+\-]?)(\d{1,2})(?::?(\d{2}))?', label.upper())
        if match:
            sign = -1 if match.group(1) == '-' else 1
            hours = int(match.group(2))
            minutes = int(match.group(3) or 0)
            delta = timedelta(hours=hours, minutes=minutes)
            return timezone(sign * delta)
        return timezone.utc

    def _parse_datetime(self, raw: str, tzinfo):
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            dt = None
            patterns = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d',
            ]
            for fmt in patterns:
                try:
                    dt = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                raise ValueError('无法解析日期时间格式')
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tzinfo)
        return dt

    def _normalize_lines(self, content: str, trim: bool, keep_empty: bool) -> List[str]:
        lines = content.splitlines()
        normalized = []
        for line in lines:
            current = line.strip() if trim else line.rstrip('\r')
            if not current and not keep_empty:
                continue
            normalized.append(current)
        return normalized

    def _resolve_file_arg(self, value):
        if isinstance(value, dict):
            return value.get('path')
        return value

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
        except Exception:
            # 统一对外提示为“不是JSON格式数据”，避免暴露内部异常细节
            return api_error('不是JSON格式数据')

    def text_regex_match(self, options: Dict | None = None):
        """正则搜索 / 替换 / 提取"""
        try:
            opts = self._validate(options)
            pattern = opts.get('pattern')
            if not pattern:
                raise ValueError('请输入正则表达式')
            content = opts.get('content', '') or ''
            operation = str(opts.get('operation', 'search')).lower()
            regex = self._compile_regex(pattern, opts.get('flags'))

            if operation == 'replace':
                replacement = opts.get('replacement', '')
                result, count = regex.subn(replacement, content)
                return api_success('替换完成', result=result, count=count)

            matches = []
            for match in regex.finditer(content):
                matches.append({
                    'match': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'groups': list(match.groups()),
                })
            if operation == 'extract':
                extracted = [item['match'] for item in matches]
                return api_success('提取完成', matches=matches, extracted=extracted, count=len(matches))
            return api_success('匹配完成', matches=matches, count=len(matches))
        except Exception as exc:
            return api_error(f'正则处理失败：{exc}')

    def text_convert_csv_json(self, options: Dict | None = None):
        """CSV 与 JSON 互转"""
        try:
            opts = self._validate(options)
            direction = str(opts.get('direction', 'csv_to_json')).lower()
            source_path = self._resolve_file_arg(opts.get('file') or opts.get('filePath') or opts.get('sourceFile'))
            path = ensure_file_path(source_path)
            delimiter = str(opts.get('delimiter') or ',')
            output_dir = Path(opts.get('outputDir') or path.parent)
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = opts.get('outputName') or f'{path.stem}_converted'

            if direction == 'csv_to_json':
                with path.open('r', encoding=opts.get('encoding') or 'utf-8-sig', newline='') as handler:
                    reader = csv.DictReader(handler, delimiter=delimiter)
                    rows = list(reader)
                dest = output_dir / f'{base_name}.json'
                with dest.open('w', encoding='utf-8') as handler:
                    json.dump(rows, handler, ensure_ascii=False, indent=2)
                return api_success('已转换为 JSON', file=str(dest), count=len(rows))

            with path.open('r', encoding=opts.get('encoding') or 'utf-8') as handler:
                data = json.load(handler)
            if isinstance(data, dict):
                rows = [data]
            elif isinstance(data, list):
                rows = data
            else:
                raise ValueError('JSON 必须为对象或对象列表')
            if not rows:
                raise ValueError('JSON 内容为空')
            if not isinstance(rows[0], dict):
                raise ValueError('JSON 列表元素必须为对象')

            fieldnames = sorted({key for row in rows for key in row.keys()})
            dest = output_dir / f'{base_name}.csv'
            with dest.open('w', encoding='utf-8-sig', newline='') as handler:
                writer = csv.DictWriter(handler, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(rows)
            return api_success('已转换为 CSV', file=str(dest), columns=len(fieldnames), rows=len(rows))
        except Exception as exc:
            return api_error(f'CSV/JSON 转换失败：{exc}')

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

    def text_deduplicate_sort(self, options: Dict | None = None):
        """去重 / 排序 / 词频统计"""
        try:
            opts = self._validate(options)
            content = opts.get('content', '') or ''
            trim = bool(opts.get('trimWhitespace', True))
            keep_empty = bool(opts.get('keepEmpty', False))
            case_sensitive = bool(opts.get('caseSensitive', True))
            lines = self._normalize_lines(content, trim, keep_empty)
            operation = str(opts.get('operation', 'deduplicate')).lower()

            seen = OrderedDict()
            for line in lines:
                key = line if case_sensitive else line.lower()
                if key not in seen:
                    seen[key] = line

            result_lines = list(seen.values())
            stats = {
                'originalCount': len(content.splitlines()),
                'effectiveCount': len(lines),
                'uniqueCount': len(result_lines),
                'removedCount': len(lines) - len(result_lines),
            }

            if operation == 'sort':
                sort_method = str(opts.get('sortMethod', 'alpha')).lower()
                descending = bool(opts.get('descending', False))
                if sort_method == 'length':
                    result_lines.sort(key=len, reverse=descending)
                else:
                    result_lines.sort(key=lambda item: item if case_sensitive else item.lower(), reverse=descending)
            elif operation == 'frequency':
                counter = Counter(line if case_sensitive else line.lower() for line in lines)
                freq = [
                    {'value': seen[key], 'count': count}
                    for key, count in counter.most_common(100)
                ]
                return api_success('词频统计完成', frequency=freq, stats=stats)

            return api_success('处理完成', result='\n'.join(result_lines), stats=stats)
        except Exception as exc:
            return api_error(f'文本处理失败：{exc}')

    def text_timestamp_convert(self, options: Dict | None = None):
        """时间戳与日期互转"""
        try:
            opts = self._validate(options)
            direction = str(opts.get('direction', 'ts_to_date')).lower()
            tz = self._resolve_timezone(opts.get('timezone'))
            unit = str(opts.get('unit', 's')).lower()
            if direction in {'ts_to_date', 'timestamp_to_datetime'}:
                raw = opts.get('timestamp') or opts.get('value') or 0
                timestamp = float(raw)
                if unit in {'ms', 'millisecond', 'milliseconds'}:
                    timestamp /= 1000.0
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(tz)
                return api_success('转换完成', datetime=dt.isoformat(), display=dt.strftime('%Y-%m-%d %H:%M:%S'), timestamp=int(timestamp), timestampMs=int(timestamp * 1000))
            raw = opts.get('datetime') or opts.get('value') or ''
            if not raw:
                raise ValueError('请输入日期时间')
            dt = self._parse_datetime(raw, tz)
            timestamp = dt.astimezone(timezone.utc).timestamp()
            result = {
                'timestamp': int(timestamp),
                'timestampMs': int(timestamp * 1000),
                'datetime': dt.isoformat(),
            }
            return api_success('转换完成', **result)
        except Exception as exc:
            return api_error(f'时间转换失败：{exc}')

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
                file_path = self._resolve_file_arg(file_info)
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

    def text_batch_replace(self, options: Dict | None = None):
        """批量替换"""
        try:
            opts = self._validate(options)
            content = opts.get('content', '') or ''
            rules = opts.get('rules') or []
            if not isinstance(rules, list) or not rules:
                raise ValueError('请至少添加一条规则')
            result = content
            report = []
            total_replaced = 0
            for idx, rule in enumerate(rules, start=1):
                if not rule or not rule.get('enabled', True):
                    continue
                search = rule.get('search') or rule.get('pattern') or ''
                if not search:
                    continue
                replacement = rule.get('replace') or rule.get('value') or ''
                limit = rule.get('limit')
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 0
                use_regex = bool(rule.get('regex'))
                case_sensitive = bool(rule.get('caseSensitive', True))
                flags = rule.get('flags')
                if use_regex:
                    pattern = self._compile_regex(search, flags)
                    if limit and limit > 0:
                        result, replaced = pattern.subn(replacement, result, count=limit)
                    else:
                        result, replaced = pattern.subn(replacement, result)
                else:
                    flag = 0 if case_sensitive else re.IGNORECASE
                    pattern = re.compile(re.escape(search), flag)
                    repl = replacement
                    if limit and limit > 0:
                        result, replaced = pattern.subn(lambda _: repl, result, count=limit)
                    else:
                        result, replaced = pattern.subn(lambda _: repl, result)
                total_replaced += replaced
                report.append({
                    'index': idx,
                    'search': search,
                    'replacement': replacement,
                    'count': replaced,
                })
            return api_success('批量替换完成', result=result, replaced=total_replaced, report=report)
        except Exception as exc:
            return api_error(f'批量替换失败：{exc}')

    def text_unicode_convert(self, options: Dict | None = None):
        """Unicode 转义处理"""
        try:
            opts = self._validate(options)
            content = opts.get('content', '') or ''
            mode = str(opts.get('mode', 'escape')).lower()
            if mode in {'escape', 'encode'}:
                escaped = content.encode('unicode_escape').decode('ascii')
                if opts.get('uppercase'):
                    escaped = re.sub(r'\\u[0-9a-fA-F]{4}', lambda match: match.group(0).upper(), escaped)
                    escaped = re.sub(r'\\U[0-9a-fA-F]{8}', lambda match: match.group(0).upper(), escaped)
                return api_success('已转换为 Unicode 转义', result=escaped)
            if mode in {'unescape', 'decode'}:
                decoded = content.encode('utf-8').decode('unicode_escape')
                return api_success('已还原字符', result=decoded)
            if mode in {'codepoint', 'codepoints'}:
                table = [
                    {'char': ch, 'code': f'U+{ord(ch):04X}', 'decimal': ord(ch)}
                    for ch in content
                ]
                return api_success('编码点列表', codepoints=table, count=len(table))
            if mode in {'from_codepoint', 'from_codepoints'}:
                raw_codes = opts.get('codePoints') or content
                if not raw_codes:
                    raise ValueError('请输入编码点')
                chars = []
                for chunk in re.split(r'[\s,;]+', str(raw_codes).strip()):
                    if not chunk:
                        continue
                    normalized = chunk.upper().lstrip('U+').lstrip('0X')
                    try:
                        code_int = int(normalized, 16)
                    except ValueError:
                        raise ValueError(f'非法编码点：{chunk}')
                    chars.append(chr(code_int))
                return api_success('编码点转换完成', result=''.join(chars), count=len(chars))
            raise ValueError('未知的转换模式')
        except Exception as exc:
            return api_error(f'Unicode 处理失败：{exc}')
