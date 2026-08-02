#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理相关 API
"""
from __future__ import annotations

import base64
import csv
import difflib
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
        except json.JSONDecodeError as exc:
            return api_error(f'不是有效的 JSON 格式：第 {exc.lineno} 行第 {exc.colno} 列')
        except KeyError as exc:
            return api_error(f'查询路径不存在：{exc}')
        except ValueError as exc:
            return api_error(f'JSON 处理失败：{exc}')
        except Exception:
            return api_error('JSON 处理失败')

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

    @staticmethod
    def _decode_jwt_segment(segment: str, label: str):
        raw_segment = str(segment or '')
        normalized = raw_segment.rstrip('=')
        if not normalized or not re.fullmatch(r'[A-Za-z0-9_-]+', normalized):
            raise ValueError(f'{label}不是有效的 Base64URL 数据')
        if len(normalized) % 4 == 1:
            raise ValueError(f'{label}的 Base64URL 长度无效')
        padding = '=' * (-len(normalized) % 4)
        try:
            raw = base64.urlsafe_b64decode(normalized + padding)
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f'{label}不是有效的 UTF-8 JSON') from exc

    @staticmethod
    def _jwt_time_claim(value):
        try:
            timestamp = float(value)
            parsed = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return {'valid': True, 'timestamp': timestamp, 'iso': parsed.isoformat()}
        except (TypeError, ValueError, OSError, OverflowError):
            return {'valid': False, 'value': value, 'iso': ''}

    def text_decode_jwt(self, options: Dict | str | None = None):
        """Decode JWT metadata locally without claiming signature verification."""
        try:
            if isinstance(options, str):
                token = options
            else:
                token = str(self._validate(options).get('token') or '')
            token = token.strip()
            if not token:
                raise ValueError('请输入 JWT')
            if len(token) > 256_000:
                raise ValueError('JWT 超过 256 KB 限制')
            segments = token.split('.')
            if len(segments) != 3:
                raise ValueError('JWT 必须包含 header、payload 和 signature 三段')
            header = self._decode_jwt_segment(segments[0], 'Header')
            payload = self._decode_jwt_segment(segments[1], 'Payload')
            if not isinstance(header, dict) or not isinstance(payload, dict):
                raise ValueError('JWT 的 Header 和 Payload 必须是 JSON 对象')

            signature_segment = segments[2].rstrip('=')
            if signature_segment and not re.fullmatch(r'[A-Za-z0-9_-]+', signature_segment):
                raise ValueError('Signature 不是有效的 Base64URL 数据')
            signature_bytes = 0
            if signature_segment:
                if len(signature_segment) % 4 == 1:
                    raise ValueError('Signature 的 Base64URL 长度无效')
                signature_bytes = len(
                    base64.urlsafe_b64decode(signature_segment + '=' * (-len(signature_segment) % 4))
                )

            now = datetime.now(timezone.utc).timestamp()
            claim_times = {
                claim: self._jwt_time_claim(payload[claim])
                for claim in ('iat', 'nbf', 'exp')
                if claim in payload
            }
            expired = bool(claim_times.get('exp', {}).get('valid') and claim_times['exp']['timestamp'] <= now)
            not_yet_valid = bool(
                claim_times.get('nbf', {}).get('valid') and claim_times['nbf']['timestamp'] > now
            )
            issued_in_future = bool(
                claim_times.get('iat', {}).get('valid') and claim_times['iat']['timestamp'] > now + 300
            )
            algorithm = str(header.get('alg') or '')
            warnings = ['未提供验签密钥，本工具只解码内容，不验证签名真实性。']
            if not signature_segment or algorithm.lower() == 'none':
                warnings.append('Token 未携带可验证签名，不能用于身份或权限判断。')
            if expired:
                warnings.append('Token 已超过 exp 声明的有效期。')
            if not_yet_valid:
                warnings.append('Token 尚未到 nbf 声明的生效时间。')
            if issued_in_future:
                warnings.append('Token 的 iat 时间比本机时间晚超过 5 分钟。')
            if 'exp' not in payload:
                warnings.append('Payload 没有 exp 声明，无法判断过期时间。')

            return api_success(
                'JWT 解码完成（签名未验证）',
                header=header,
                payload=payload,
                algorithm=algorithm,
                tokenType=str(header.get('typ') or ''),
                signaturePresent=bool(signature_segment),
                signatureBytes=signature_bytes,
                signatureVerified=False,
                claimTimes=claim_times,
                expired=expired,
                notYetValid=not_yet_valid,
                issuedInFuture=issued_in_future,
                warnings=warnings,
                checkedAt=datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            )
        except Exception as exc:
            return api_error(f'JWT 解码失败：{exc}')

    def text_compare(self, options: Dict | None = None):
        """Compare two local text values as lines or words."""
        try:
            opts = self._validate(options)
            left_text = str(opts.get('left') or '')
            right_text = str(opts.get('right') or '')
            if len(left_text) > 1_000_000 or len(right_text) > 1_000_000:
                raise ValueError('单侧文本不能超过 100 万字符')
            mode = str(opts.get('mode') or 'lines').lower()
            if mode not in {'lines', 'words'}:
                raise ValueError('比较模式必须是 lines 或 words')
            ignore_whitespace = bool(opts.get('ignoreWhitespace', False))
            ignore_case = bool(opts.get('ignoreCase', False))

            if mode == 'lines':
                left_items = left_text.splitlines()
                right_items = right_text.splitlines()
            else:
                left_items = re.findall(r'\s+|[^\s]+', left_text)
                right_items = re.findall(r'\s+|[^\s]+', right_text)
                if ignore_whitespace:
                    left_items = [item for item in left_items if not item.isspace()]
                    right_items = [item for item in right_items if not item.isspace()]
            if len(left_items) + len(right_items) > 200_000:
                raise ValueError('比较项目总数不能超过 20 万，请缩小文本范围')

            def comparison_key(value: str) -> str:
                output = re.sub(r'\s+', ' ', value).strip() if ignore_whitespace else value
                return output.casefold() if ignore_case else output

            matcher = difflib.SequenceMatcher(
                None,
                [comparison_key(item) for item in left_items],
                [comparison_key(item) for item in right_items],
                autojunk=True,
            )
            operations = []
            stats = {'added': 0, 'removed': 0, 'unchanged': 0, 'changedGroups': 0}
            for tag, left_start, left_end, right_start, right_end in matcher.get_opcodes():
                left_segment = left_items[left_start:left_end]
                right_segment = right_items[right_start:right_end]
                operations.append({
                    'type': tag,
                    'left': left_segment,
                    'right': right_segment,
                    'leftStart': left_start + 1,
                    'rightStart': right_start + 1,
                })
                if tag == 'equal':
                    stats['unchanged'] += len(left_segment)
                else:
                    stats['removed'] += len(left_segment)
                    stats['added'] += len(right_segment)
                    stats['changedGroups'] += 1

            context_lines = max(0, min(int(opts.get('contextLines') or 3), 20))
            unified_diff = ''
            if mode == 'lines':
                unified_diff = '\n'.join(
                    difflib.unified_diff(
                        left_items,
                        right_items,
                        fromfile=str(opts.get('leftLabel') or '左侧'),
                        tofile=str(opts.get('rightLabel') or '右侧'),
                        lineterm='',
                        n=context_lines,
                    )
                )[:500_000]
            similarity = matcher.ratio()
            return api_success(
                '文本比较完成',
                mode=mode,
                operations=operations,
                stats=stats,
                similarity=round(similarity * 100, 1),
                identical=similarity == 1.0,
                unifiedDiff=unified_diff,
            )
        except Exception as exc:
            return api_error(f'文本比较失败：{exc}')
