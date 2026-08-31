#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FlyingMouse Format integration used by the PPX conversion center."""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from api.utils.error_handler import api_error, api_success
from pyapp.config.config import Config

ENGINE_NAME = 'FlyingMouse Format'
ENGINE_AUTHOR = '牢蜂（LaoFeng）'
ENGINE_LICENSE = '个人非商用许可'
_CONVERSION_TIMEOUT = 6 * 60 * 60
_QUERY_TIMEOUT = 90
_FORMAT_PATTERN = re.compile(r'^[a-z0-9]+$')


class FlyingMouseRuntimeError(RuntimeError):
    """An actionable error returned by the FlyingMouse CLI."""

    def __init__(self, message: str, error_code: str = ''):
        super().__init__(message)
        self.error_code = error_code


def _path_from_env(name: str) -> Path | None:
    raw = str(os.getenv(name) or '').strip().strip('"')
    return Path(raw).expanduser() if raw else None


def _source_roots() -> Iterable[Path]:
    code_root = Path(Config.codeDir).resolve()
    project_root = Path(__file__).resolve().parents[1]
    for candidate in (
        code_root / 'vendor' / 'flyingmouse-format',
        code_root / 'flyingmouse-format',
    ):
        yield candidate

    configured = _path_from_env('PPX_FLYINGMOUSE_ROOT') or _path_from_env('FLYINGMOUSE_FORMAT_ROOT')
    if configured:
        yield configured

    for candidate in (
        code_root.parent / 'flyingmouse-format',
        project_root.parent / 'flyingmouse-format',
    ):
        yield candidate


def _bundled_node() -> Path | None:
    code_root = Path(Config.codeDir).resolve()
    executable_name = 'node.exe' if platform.system() == 'Windows' else 'node'
    for candidate in (
        code_root / 'vendor' / 'flyingmouse-runtime' / executable_name,
        code_root / 'flyingmouse-runtime' / executable_name,
    ):
        if candidate.is_file():
            return candidate
    return None


def _installed_executables() -> Iterable[Path]:
    configured = _path_from_env('PPX_FLYINGMOUSE_EXECUTABLE') or _path_from_env('FLYINGMOUSE_FORMAT_EXECUTABLE')
    if configured:
        yield configured

    system = platform.system()
    if system == 'Windows':
        local_app_data_raw = str(os.getenv('LOCALAPPDATA') or '').strip()
        if local_app_data_raw:
            local_app_data = Path(local_app_data_raw)
            yield local_app_data / 'Programs' / 'FlyingMouse Format' / 'FlyingMouse Format.exe'
            yield local_app_data / 'Programs' / 'flyingmouse-format' / 'FlyingMouse Format.exe'
    elif system == 'Darwin':
        yield Path('/Applications/FlyingMouse Format.app/Contents/MacOS/FlyingMouse Format')
        yield Path.home() / 'Applications' / 'FlyingMouse Format.app' / 'Contents' / 'MacOS' / 'FlyingMouse Format'


def _public_runtime(runtime: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'available': bool(runtime.get('available')),
        'mode': runtime.get('mode') or '',
        'path': runtime.get('path') or '',
        'detail': runtime.get('detail') or '',
    }


def discover_flyingmouse_runtime() -> Dict[str, Any]:
    """Find a source checkout or installed FlyingMouse CLI without executing it."""
    checked: List[str] = []
    configured_node = _path_from_env('PPX_FLYINGMOUSE_NODE_PATH') or _path_from_env('FLYINGMOUSE_NODE_PATH')
    bundled_node = _bundled_node()
    if configured_node and configured_node.is_file():
        node_command = str(configured_node)
    elif bundled_node:
        node_command = str(bundled_node)
    else:
        node_command = shutil.which('node')

    explicit_cli = _path_from_env('PPX_FLYINGMOUSE_CLI_PATH') or _path_from_env('FLYINGMOUSE_FORMAT_CLI_PATH')
    source_candidates = [explicit_cli] if explicit_cli else []
    source_candidates.extend(root / 'cli.js' for root in _source_roots())
    seen = set()
    for cli_path in source_candidates:
        if not cli_path:
            continue
        cli_path = cli_path.resolve()
        identity = os.path.normcase(str(cli_path))
        if identity in seen:
            continue
        seen.add(identity)
        checked.append(str(cli_path))
        if not cli_path.is_file():
            continue
        if not node_command:
            continue
        bundled_root = (Path(Config.codeDir).resolve() / 'vendor' / 'flyingmouse-format').resolve()
        is_bundled = cli_path == bundled_root / 'cli.js'
        return {
            'available': True,
            'mode': 'bundled' if is_bundled else 'source',
            'path': str(cli_path),
            'cwd': str(cli_path.parent),
            'command': [node_command, str(cli_path)],
            'detail': 'PPX 内置 FlyingMouse Format 已就绪' if is_bundled else f'已连接源码运行时：{cli_path.parent}',
        }

    for executable in _installed_executables():
        executable = executable.expanduser().resolve()
        checked.append(str(executable))
        if not executable.is_file():
            continue
        return {
            'available': True,
            'mode': 'installed',
            'path': str(executable),
            'cwd': str(executable.parent),
            'command': [str(executable), '--cli'],
            'detail': f'已连接安装版：{executable}',
        }

    bundled_cli = Path(Config.codeDir).resolve() / 'vendor' / 'flyingmouse-format' / 'cli.js'
    if bundled_cli.is_file() and not node_command:
        detail = 'PPX 内置 FlyingMouse 源码存在，但内置 Node 运行时缺失；请重新安装完整版本。'
    elif any(Path(item).is_file() and Path(item).suffix.lower() == '.js' for item in checked) and not node_command:
        detail = '已找到 FlyingMouse 源码，但未检测到 Node.js 18+；开发环境请运行 pnpm run prepare:flyingmouse。'
    else:
        detail = '未检测到内置 FlyingMouse Format；请重新安装完整版本。开发环境可运行 pnpm run prepare:flyingmouse。'
    return {
        'available': False,
        'mode': '',
        'path': '',
        'cwd': '',
        'command': [],
        'detail': detail,
        'checked': checked[:8],
    }


def _json_line(text: str) -> Dict[str, Any] | None:
    for line in reversed(str(text or '').splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _creation_flags() -> int:
    if platform.system() != 'Windows':
        return 0
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    flags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    return flags


def _terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if platform.system() == 'Windows':
            subprocess.run(
                ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                capture_output=True,
                timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.communicate(timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def _run_cli(runtime: Dict[str, Any], arguments: List[str], timeout: int) -> Dict[str, Any]:
    if not runtime.get('available'):
        raise FlyingMouseRuntimeError(runtime.get('detail') or 'FlyingMouse Format 未就绪', 'ENGINE_UNAVAILABLE')

    command = [*runtime['command'], *arguments]
    if '--json' not in command:
        command.append('--json')

    runtime_dir = Path(Config.appDataDir or Config.staticDir) / 'flyingmouse-runtime'
    runtime_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.setdefault('FLYINGMOUSE_RUNTIME_DIR', str(runtime_dir))

    process = None
    try:
        process = subprocess.Popen(
            command,
            cwd=runtime.get('cwd') or None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=environment,
            creationflags=_creation_flags(),
            start_new_session=platform.system() != 'Windows',
        )
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            _terminate_process_tree(process)
        raise FlyingMouseRuntimeError('转换引擎执行超时，请减少单次文件数量后重试', 'ENGINE_TIMEOUT') from exc
    except OSError as exc:
        if process is not None:
            _terminate_process_tree(process)
        raise FlyingMouseRuntimeError(f'无法启动 FlyingMouse Format：{exc}', 'ENGINE_START_FAILED') from exc

    output = _json_line(stdout)
    error_output = _json_line(stderr)
    if process.returncode != 0:
        payload = error_output or output or {}
        message = str(payload.get('error') or '').strip()
        if not message:
            message = next((line.strip() for line in reversed(stderr.splitlines()) if line.strip()), '')
        raise FlyingMouseRuntimeError(
            message or f'FlyingMouse Format 执行失败（退出码 {process.returncode}）',
            str(payload.get('errorCode') or 'ENGINE_FAILED'),
        )
    if not output:
        raise FlyingMouseRuntimeError('FlyingMouse Format 未返回可解析的 JSON 结果', 'ENGINE_INVALID_RESPONSE')
    if output.get('ok') is False:
        raise FlyingMouseRuntimeError(
            str(output.get('error') or '转换失败'),
            str(output.get('errorCode') or 'CONVERSION_FAILED'),
        )
    return output


def _options_dict(options: Dict[str, Any] | None) -> Dict[str, Any]:
    if options is None:
        return {}
    if not isinstance(options, dict):
        raise ValueError('参数格式错误')
    return options


def _input_files(options: Dict[str, Any], minimum: int = 1) -> List[Path]:
    raw_files = options.get('files') or options.get('fileList') or []
    if isinstance(raw_files, (str, os.PathLike)):
        raw_files = [raw_files]
    if not isinstance(raw_files, list):
        raise ValueError('文件列表格式错误')
    if len(raw_files) > 200:
        raise ValueError('单次最多处理 200 个文件，请分批转换')
    paths: List[Path] = []
    seen = set()
    for item in raw_files[:200]:
        raw = item.get('path') if isinstance(item, dict) else item
        if not isinstance(raw, (str, os.PathLike)):
            continue
        path = Path(raw).expanduser().resolve()
        identity = os.path.normcase(str(path))
        if identity in seen:
            continue
        if not path.is_file():
            raise FileNotFoundError(f'源文件不存在：{path}')
        seen.add(identity)
        paths.append(path)
    if len(paths) < minimum:
        raise ValueError(f'请至少选择 {minimum} 个文件')
    return paths


def _target_format(options: Dict[str, Any]) -> str:
    value = str(options.get('targetFormat') or '').strip().lower().lstrip('.')
    if not value or not _FORMAT_PATTERN.fullmatch(value):
        raise ValueError('请选择有效的目标格式')
    return value


def _output_directory(options: Dict[str, Any]) -> Path:
    raw = str(options.get('outputDir') or '').strip()
    target = Path(raw).expanduser() if raw else Path(Config.downloadDir or Path.home() / 'Downloads') / 'PPX转换结果'
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise ValueError('输出位置不是有效目录')
    return target


def _pdf_output_path(options: Dict[str, Any], output_dir: Path) -> Path | None:
    raw_name = str(options.get('outputName') or '').strip()
    if not raw_name:
        return None
    name = Path(raw_name).name
    if name != raw_name or name in {'.', '..'}:
        raise ValueError('输出文件名无效')
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    return output_dir / name


def _conversion_payload(result: Dict[str, Any], output_dir: Path, message: str) -> Dict[str, Any]:
    outputs = result.get('outputs') if isinstance(result.get('outputs'), list) else []
    files = [str(item.get('path')) for item in outputs if isinstance(item, dict) and item.get('path')]
    warnings = []
    for item in outputs:
        if not isinstance(item, dict):
            continue
        item_warnings = item.get('warnings') or []
        if isinstance(item_warnings, list):
            warnings.extend(str(warning) for warning in item_warnings if warning)
    return api_success(
        message,
        files=files,
        outputs=outputs,
        outputDir=str(output_dir),
        warnings=warnings,
        engine={'name': ENGINE_NAME, 'author': ENGINE_AUTHOR, 'license': ENGINE_LICENSE},
    )


class FormatCenterMixin:
    """Expose FlyingMouse conversion commands through the existing pywebview API."""

    def format_center_capabilities(self):
        runtime = discover_flyingmouse_runtime()
        if not runtime.get('available'):
            return api_success(
                '转换引擎未就绪',
                available=False,
                detail=runtime.get('detail'),
                runtime=_public_runtime(runtime),
                engine={'name': ENGINE_NAME, 'author': ENGINE_AUTHOR, 'license': ENGINE_LICENSE},
            )
        try:
            capabilities = _run_cli(runtime, ['capabilities'], _QUERY_TIMEOUT)
            return api_success(
                '转换引擎已就绪',
                available=True,
                detail=runtime.get('detail'),
                runtime=_public_runtime(runtime),
                capabilities=capabilities,
                groups=capabilities.get('groups') or {},
                optional=capabilities.get('optional') or [],
                engine={'name': ENGINE_NAME, 'author': ENGINE_AUTHOR, 'license': ENGINE_LICENSE},
            )
        except FlyingMouseRuntimeError as exc:
            return api_success(
                '已找到转换引擎，但能力检测失败',
                available=False,
                detail=str(exc),
                errorCode=exc.error_code,
                runtime=_public_runtime(runtime),
                engine={'name': ENGINE_NAME, 'author': ENGINE_AUTHOR, 'license': ENGINE_LICENSE},
            )

    def format_center_targets(self, options: Dict[str, Any] | None = None):
        try:
            opts = _options_dict(options)
            raw_inputs = opts.get('files') or opts.get('extensions') or []
            if isinstance(raw_inputs, (str, os.PathLike)):
                raw_inputs = [raw_inputs]
            if not isinstance(raw_inputs, list) or not raw_inputs:
                return api_error('请先选择要转换的文件')
            if len(raw_inputs) > 200:
                return api_error('单次最多分析 200 个文件，请分批转换')

            extensions = []
            for item in raw_inputs[:200]:
                raw = item.get('path') if isinstance(item, dict) else item
                value = str(raw or '').strip()
                suffix = Path(value).suffix.lower().lstrip('.')
                extension = suffix or value.lower().lstrip('.')
                if not _FORMAT_PATTERN.fullmatch(extension):
                    return api_error(f'无法识别文件格式：{value}')
                if extension not in extensions:
                    extensions.append(extension)

            runtime = discover_flyingmouse_runtime()
            if not runtime.get('available'):
                return api_error(runtime.get('detail') or '转换引擎未就绪', errorCode='ENGINE_UNAVAILABLE')

            items = []
            for extension in extensions:
                item = _run_cli(runtime, ['targets', extension], _QUERY_TIMEOUT)
                items.append(item)
            common_targets = list(items[0].get('targets') or [])
            for item in items[1:]:
                allowed = set(item.get('targets') or [])
                common_targets = [target for target in common_targets if target in allowed]
            return api_success(
                '已分析可用目标格式',
                items=items,
                extensions=extensions,
                commonTargets=common_targets,
                mixed=len(extensions) > 1,
            )
        except FlyingMouseRuntimeError as exc:
            return api_error(str(exc), errorCode=exc.error_code)
        except Exception as exc:
            return api_error(f'分析格式失败：{exc}')

    def format_center_convert(self, options: Dict[str, Any] | None = None):
        try:
            opts = _options_dict(options)
            files = _input_files(opts)
            target = _target_format(opts)
            output_dir = _output_directory(opts)
            runtime = discover_flyingmouse_runtime()
            common_arguments = ['--to', target, '--output-dir', str(output_dir)]

            compression_level = str(opts.get('compressionLevel') or '').strip()
            if target == 'zip' and compression_level in {'0', '1', '6', '9'}:
                common_arguments.extend(['--compression-level', compression_level])
            video_codec = str(opts.get('videoCodec') or '').strip().lower()
            if video_codec in {'h264', 'h265', 'av1'}:
                common_arguments.extend(['--video-codec', video_codec])
            # FlyingMouse 的桌面界面允许批量中的单项失败后继续。CLI 的多文件模式会在
            # 首个错误处退出，因此适配层逐项调用并汇总，保留已经成功的输出。
            outputs = []
            failures = []
            for source in files:
                try:
                    result = _run_cli(runtime, ['convert', str(source), *common_arguments], _CONVERSION_TIMEOUT)
                    if isinstance(result.get('outputs'), list):
                        outputs.extend(result['outputs'])
                except FlyingMouseRuntimeError as exc:
                    failures.append({'input': str(source), 'error': str(exc), 'errorCode': exc.error_code})

            if not outputs:
                first_error = failures[0]['error'] if failures else '转换引擎没有生成输出文件'
                return api_error(first_error, failures=failures, outputDir=str(output_dir))

            succeeded = len(outputs)
            failed = len(failures)
            message = f'已转换 {succeeded} 个文件' if not failed else f'已转换 {succeeded} 个文件，{failed} 个失败'
            response = _conversion_payload({'outputs': outputs}, output_dir, message)
            response.update({'failures': failures, 'partial': bool(failures)})
            return response
        except FlyingMouseRuntimeError as exc:
            return api_error(str(exc), errorCode=exc.error_code)
        except Exception as exc:
            return api_error(f'转换失败：{exc}')

    def format_center_images_to_pdf(self, options: Dict[str, Any] | None = None):
        try:
            opts = _options_dict(options)
            files = _input_files(opts)
            output_dir = _output_directory(opts)
            output_path = _pdf_output_path(opts, output_dir)
            runtime = discover_flyingmouse_runtime()
            arguments = ['images-to-pdf', *(str(path) for path in files)]
            arguments.extend(['--output', str(output_path)] if output_path else ['--output-dir', str(output_dir)])
            result = _run_cli(runtime, arguments, _CONVERSION_TIMEOUT)
            return _conversion_payload(result, output_dir, f'已将 {len(files)} 张图片合成为 PDF')
        except FlyingMouseRuntimeError as exc:
            return api_error(str(exc), errorCode=exc.error_code)
        except Exception as exc:
            return api_error(f'图片合成 PDF 失败：{exc}')

    def format_center_merge_pdfs(self, options: Dict[str, Any] | None = None):
        try:
            opts = _options_dict(options)
            files = _input_files(opts, minimum=2)
            if any(path.suffix.lower() != '.pdf' for path in files):
                return api_error('PDF 合并只支持 PDF 文件')
            output_dir = _output_directory(opts)
            output_path = _pdf_output_path(opts, output_dir)
            runtime = discover_flyingmouse_runtime()
            arguments = ['merge-pdfs', *(str(path) for path in files)]
            arguments.extend(['--output', str(output_path)] if output_path else ['--output-dir', str(output_dir)])
            result = _run_cli(runtime, arguments, _CONVERSION_TIMEOUT)
            return _conversion_payload(result, output_dir, f'已合并 {len(files)} 个 PDF')
        except FlyingMouseRuntimeError as exc:
            return api_error(str(exc), errorCode=exc.error_code)
        except Exception as exc:
            return api_error(f'合并 PDF 失败：{exc}')
