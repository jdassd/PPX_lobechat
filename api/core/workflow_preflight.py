"""Bounded inspection of a manual run; never saves state or executes operations."""
from api.core.workflow_bindings import BINDING, ResolutionLimitError, lookup, resolve
from api.operations import validate_operation_args

MAX_ERRORS = 100
MAX_NODES = 10_000
MAX_DEPTH = 12
MAX_STEPS = 100
MAX_BINDINGS = 1_000
MAX_CHARS = 2_000_000


def _bounded(value):
    nodes = chars = bindings = 0
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            return '配置最多包含 10000 个节点，嵌套不超过 12 层'
        if isinstance(item, str):
            chars += len(item)
            if chars > MAX_CHARS:
                return '配置字符串总长度不能超过 200 万字符'
            for _ in BINDING.finditer(item):
                bindings += 1
                if bindings > MAX_BINDINGS:
                    return '变量引用不能超过 1000 项'
        elif isinstance(item, (dict, list)):
            if nodes + len(stack) + len(item) > MAX_NODES:
                return '配置最多包含 10000 个节点'
            if isinstance(item, dict):
                if any(not isinstance(key, str) for key in item):
                    return '配置字段名称必须是字符串'
                chars += sum(len(key) for key in item)
                if chars > MAX_CHARS:
                    return '配置字符串总长度不能超过 200 万字符'
                stack.extend((child, depth + 1) for child in item.values())
            else:
                stack.extend((child, depth + 1) for child in item)
        elif item is not None and not isinstance(item, (bool, int, float)):
            return '配置必须使用 JSON 支持的数据类型'
    return None


def _walk_bindings(value, path=''):
    if isinstance(value, dict):
        for key, item in value.items():
            escaped = key.replace('~', '~0').replace('/', '~1')
            yield from _walk_bindings(item, f'{path}/{escaped}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_bindings(item, f'{path}/{index}')
    elif isinstance(value, str):
        for match in BINDING.finditer(value):
            yield path, match.group(1)


def _has_step_binding(value):
    return isinstance(value, str) and any(match.group(1).split('.')[0] == 'steps' for match in BINDING.finditer(value))


class _ExpansionBudget:
    def __init__(self):
        self.nodes = self.chars = 0

    def consume(self, value, depth=0, shallow=False):
        stack = [(value, depth)]
        while stack:
            item, level = stack.pop()
            self.nodes += 1
            if isinstance(item, str):
                self.chars += len(item)
            elif isinstance(item, dict):
                self.chars += sum(len(str(key)) for key in item)
                if not shallow:
                    stack.extend((child, level + 1) for child in item.values())
            elif isinstance(item, list) and not shallow:
                stack.extend((child, level + 1) for child in item)
            if self.nodes > MAX_NODES or self.chars > MAX_CHARS or level > MAX_DEPTH:
                raise ResolutionLimitError('变量展开后的配置超过检查上限，请拆分工作流或减少重复引用')


def _resolve_known(value, context, budget, depth=0):
    if isinstance(value, dict):
        budget.consume(value, depth, shallow=True)
        return {key: _resolve_known(item, context, budget, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        budget.consume(value, depth, shallow=True)
        return [_resolve_known(item, context, budget, depth + 1) for item in value]
    if _has_step_binding(value):
        resolved = value
    else:
        try:
            resolved = resolve(value, context, max_string_length=MAX_CHARS - budget.chars)
        except ResolutionLimitError:
            raise
        except ValueError:
            resolved = value  # Missing variables are recorded at their exact field.
    budget.consume(resolved, depth)
    return resolved


def preflight(options, validate_steps):
    errors, deferred, reports = [], [], []
    total_errors = 0

    def error(index, step_id, field, code, message):
        nonlocal total_errors
        total_errors += 1
        if len(errors) < MAX_ERRORS:
            errors.append({'stepId': step_id, 'index': index, 'fieldPath': field, 'code': code, 'message': message})

    def result():
        return {'valid': total_errors == 0, 'errors': errors, 'deferred': deferred, 'steps': reports,
                'errorCount': total_errors, 'truncated': total_errors > len(errors)}

    if not isinstance(options, dict):
        error(None, '', '', 'INVALID_OPTIONS', '预检参数必须是对象')
        return result()
    limit = _bounded(options)
    if limit:
        error(None, '', '', 'LIMIT_EXCEEDED', limit)
        return result()
    raw_steps = options.get('steps')
    if isinstance(raw_steps, list) and len(raw_steps) > MAX_STEPS:
        error(None, '', '/steps', 'LIMIT_EXCEEDED', '步骤不能超过 100 个')
        return result()
    inputs, watch = options.get('input', {}), options.get('watch', {})
    if not isinstance(inputs, dict) or not isinstance(watch, dict):
        error(None, '', '/input', 'INVALID_INPUT', '运行输入和监听信息必须是对象')
        return result()
    if not isinstance(raw_steps, list) or not raw_steps:
        error(None, '', '/steps', 'INVALID_STEPS', '工作流至少需要一个步骤')
        return result()
    steps, seen = [], set()
    for index, raw in enumerate(raw_steps):
        step_id = str(raw.get('id') or f'step-{index + 1}') if isinstance(raw, dict) else ''
        if isinstance(raw, dict) and raw.get('args') is not None and not isinstance(raw['args'], dict):
            error(index, step_id, '/args', 'INVALID_ARGUMENT', '步骤参数必须是对象')
            continue
        try:
            candidate = {**raw, 'id': step_id} if isinstance(raw, dict) else raw
            step = validate_steps([candidate])[0]
        except (ValueError, TypeError):
            error(index, step_id, '/steps', 'INVALID_STEP', '请检查步骤操作、参数对象和重试设置；操作必须属于工作流白名单')
            continue
        if step['id'] in seen:
            error(index, step['id'], '/id', 'DUPLICATE_STEP_ID', f'步骤 ID 重复：{step["id"]}')
        seen.add(step['id'])
        steps.append((index, step))
    if errors:
        return result()

    context, prior = {'input': inputs, 'watch': watch}, set()
    budget = _ExpansionBudget()
    for index, step in steps:
        step_id = step['id']
        start_errors, start_deferred = total_errors, len(deferred)
        for path, expression in _walk_bindings(step['args']):
            parts = expression.split('.')
            root = parts[0]
            if root == 'steps':
                if len(parts) > 1 and parts[1] not in prior:
                    code = 'SELF_OR_FUTURE_STEP' if parts[1] == step_id else 'MISSING_OR_FUTURE_STEP'
                    error(index, step_id, path, code, f'只能引用前序步骤的结果：{expression}')
                else:
                    deferred.append({'stepId': step_id, 'index': index, 'fieldPath': path,
                                     'expression': expression, 'sourceStepId': parts[1] if len(parts) > 1 else '',
                                     'message': '前序输出的内容和字段将在实际执行后核对'})
            elif root in {'input', 'watch'}:
                try:
                    lookup(context, expression)
                except ValueError:
                    error(index, step_id, path, 'MISSING_VARIABLE', f'运行输入缺少变量或数组下标越界：{expression}')
            else:
                error(index, step_id, path, 'UNKNOWN_ROOT', f'不支持的变量来源：{root}')
        try:
            known = _resolve_known(step['args'], context, budget)
        except ResolutionLimitError as exc:
            error(index, step_id, '/args', 'LIMIT_EXCEEDED', str(exc))
            reports.append({'id': step_id, 'name': step['name'], 'method': step['method'], 'index': index,
                            'valid': False, 'errorCount': total_errors - start_errors,
                            'deferredCount': len(deferred) - start_deferred})
            return result()
        dynamic = {key for key, value in step['args'].items() if _has_step_binding(value)}
        for problem in validate_operation_args(step['method'], known, allow_bindings=False, detailed=True, deferred_fields=dynamic):
            key = problem['field']
            error(index, step_id, '/' + key.replace('~', '~0').replace('/', '~1'), 'INVALID_ARGUMENT', problem['message'])
        reports.append({'id': step_id, 'name': step['name'], 'method': step['method'], 'index': index,
                        'valid': total_errors == start_errors, 'errorCount': total_errors - start_errors,
                        'deferredCount': len(deferred) - start_deferred})
        prior.add(step_id)
    return result()
