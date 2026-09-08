"""Shared binding semantics for workflow execution and read-only inspection."""
import copy
import json
import re

BINDING = re.compile(r'\{\{\s*([a-zA-Z_][\w]*(?:\.[\w-]+)*)\s*\}\}')


class ResolutionLimitError(ValueError):
    """An inspection exceeded its expansion budget; execution has no such default."""


def lookup(context, expression):
    value = context
    for part in expression.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, (list, tuple)) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ValueError(f'找不到工作流变量：{expression}')
    return copy.deepcopy(value)


def resolve(value, context, *, max_string_length=None):
    if isinstance(value, list):
        return [resolve(item, context, max_string_length=max_string_length) for item in value]
    if isinstance(value, dict):
        return {str(key): resolve(item, context, max_string_length=max_string_length) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    full = BINDING.fullmatch(value)
    if full:
        return lookup(context, full.group(1))

    length = len(BINDING.sub('', value)) if max_string_length is not None else 0
    if max_string_length is not None and length > max_string_length:
        raise ResolutionLimitError('变量展开后的配置超过检查上限，请拆分工作流或减少重复引用')

    def replace(match):
        nonlocal length
        resolved = lookup(context, match.group(1))
        if isinstance(resolved, (dict, list)):
            text = json.dumps(resolved, ensure_ascii=False)
        else:
            text = '' if resolved is None else str(resolved)
        if max_string_length is not None:
            length += len(text)
            if length > max_string_length:
                raise ResolutionLimitError('变量展开后的配置超过检查上限，请拆分工作流或减少重复引用')
        return text

    return BINDING.sub(replace, value)
