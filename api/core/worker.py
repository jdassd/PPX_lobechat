"""Isolated processing worker, usable from Python and frozen desktop executables."""
from __future__ import annotations

import contextlib
import json
import queue
import re
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

from api.core.context import TaskCancelled, TaskContext, stop_process, task_context

ISOLATED_PREFIXES = ('image_', 'pdf_', 'word_', 'excel_', 'ocr_', 'video_', 'format_center_', 'seal_', 'document_index_build', 'file_compress', 'file_decompress')


def run_in_worker(method, args, context):
    from pyapp.config.config import Config
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        command += ['-u', str(Path(__file__).resolve().parents[2] / 'main.py')]
    command += ['--operation-worker']
    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='replace', **kwargs)
    events = queue.Queue()
    errors = deque(maxlen=12)

    def read_events():
        for line in process.stdout:
            try:
                events.put(json.loads(line))
            except ValueError:
                errors.append(line[-500:])
        events.put({'type': 'eof'})

    def read_errors():
        for line in process.stderr:
            errors.append(line[-500:])

    readers = [threading.Thread(target=read_events, daemon=True), threading.Thread(target=read_errors, daemon=True)]
    for reader in readers:
        reader.start()
    config = {name: str(getattr(Config, name, '')) for name in
              ('appDataDir', 'staticDir', 'codeDir', 'downloadDir', 'appSystem')}
    canceled_at = None
    temporary_paths = set()
    started = time.monotonic()
    try:
        process.stdin.write(json.dumps({'method': method, 'args': args, 'config': config}, ensure_ascii=False) + '\n')
        process.stdin.flush()
        while True:
            if context.cancel.is_set() and canceled_at is None:
                canceled_at = time.monotonic()
                try:
                    process.stdin.write('{"cancel":true}\n')
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
            if canceled_at and time.monotonic() - canceled_at > 2:
                raise TaskCancelled('已停止处理进程，已完成输出保留')
            if time.monotonic() - started > 7200:
                raise TimeoutError('处理超过两小时，已停止执行')
            try:
                event = events.get(timeout=0.1)
            except queue.Empty:
                continue
            if event.get('type') == 'progress':
                payload = event['payload']
                if payload.get('temporaryPath'):
                    temporary_paths.add(payload['temporaryPath'])
                if payload.get('temporaryRemoved'):
                    temporary_paths.discard(payload['temporaryRemoved'])
                asset = payload.get('outputAsset')
                if asset and not any(item['path'] == asset['path'] for item in context.outputs):
                    context.outputs.append(asset)
                context.emit(**payload)
            elif event.get('type') == 'result':
                return event['result']
            elif event.get('type') == 'eof':
                if context.cancel.is_set():
                    raise TaskCancelled('已取消处理')
                raise RuntimeError('处理进程异常退出：' + ''.join(errors)[-1500:])
    finally:
        stop_process(process)
        for raw in temporary_paths:
            temporary = Path(raw)
            if re.fullmatch(r'\..+\.[0-9a-f]{32}\.tmp.*', temporary.name):
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
        for reader in readers:
            reader.join(timeout=1)


def worker_main():
    # Windows GUI bundles intentionally set Python's standard streams to None.
    # Recover only the pipes explicitly supplied by our owning desktop process.
    if sys.platform == 'win32':
        import ctypes
        import msvcrt
        import os
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetStdHandle.restype = ctypes.c_void_p
        kernel.GetStdHandle.argtypes = [ctypes.c_ulong]
        for name, number, mode, flag in [('stdin', -10, 'r', os.O_RDONLY), ('stdout', -11, 'w', os.O_WRONLY), ('stderr', -12, 'w', os.O_WRONLY)]:
            if getattr(sys, name) is None:
                handle = kernel.GetStdHandle(number & 0xffffffff)
                if not handle or handle == ctypes.c_void_p(-1).value:
                    raise RuntimeError('处理进程缺少宿主通信管道')
                stream = os.fdopen(msvcrt.open_osfhandle(handle, flag), mode, encoding='utf-8', buffering=1)
                setattr(sys, name, stream)
    # Pipes use the same UTF-8 protocol in source and frozen builds, regardless
    # of the host locale (Windows CI commonly defaults to cp1252).
    for name in ('stdin', 'stdout', 'stderr'):
        stream = getattr(sys, name)
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    sink = sys.stdout

    def send(kind, **data):
        sink.write(json.dumps({'type': kind, **data}, ensure_ascii=False, default=str) + '\n')
        sink.flush()

    request = json.loads(sys.stdin.readline())
    context = TaskContext(callback=lambda payload: send('progress', payload=payload))

    def read_cancel():
        for line in sys.stdin:
            if line.strip() == '{"cancel":true}':
                context.cancel.set()

    with contextlib.redirect_stdout(sys.stderr), task_context(context):
        try:
            from pyapp.config.config import Config
            for name, value in request.get('config', {}).items():
                if name in {'appDataDir', 'staticDir', 'codeDir', 'downloadDir', 'appSystem'} and value:
                    setattr(Config, name, value)
            from api.api import API
            from api.operations import OPERATIONS, execute_operation
            method = request['method']
            if method not in OPERATIONS or not method.startswith(ISOLATED_PREFIXES):
                raise ValueError('该操作不能在处理进程中执行')
            api = API()
            threading.Thread(target=read_cancel, daemon=True).start()
            result = execute_operation(method, getattr(api, method), request.get('args', []))
        except Exception as exc:
            result = {'code': -1, 'msg': str(exc), 'errorCode': 'CANCELED' if context.cancel.is_set() else 'WORKER_FAILED'}
        result.setdefault('outputAssets', context.outputs)
        result.setdefault('itemResults', context.item_results)
        result.setdefault('inputItems', context.input_items)
    send('result', result=result)
