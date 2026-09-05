"""Cooperative cancellation, measurable progress and owned child processes."""
from __future__ import annotations

import subprocess
import sys
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


class TaskCancelled(Exception):
    pass


@dataclass
class TaskContext:
    cancel: threading.Event = field(default_factory=threading.Event)
    callback: object = None
    outputs: list = field(default_factory=list)
    input_items: list = field(default_factory=list)
    item_results: list = field(default_factory=list)

    def emit(self, **payload):
        if 'inputItems' in payload:
            self.input_items = payload['inputItems']
        if payload.get('itemResult'):
            self.item_results.append(payload['itemResult'])
        if isinstance(payload.get('itemResults'), list):
            self.item_results = payload['itemResults']
        if self.callback:
            self.callback(payload)


_current = ContextVar('ppx_task_context', default=None)


@contextmanager
def task_context(context):
    token = _current.set(context)
    try:
        yield context
    finally:
        _current.reset(token)


def current_context():
    return _current.get()


def record_inputs(paths):
    context = _current.get()
    if context:
        context.emit(inputItems=[str(path) for path in paths])


def record_item(path, status, message='', outputs=None):
    context = _current.get()
    if context:
        context.emit(itemResult={'input': str(path), 'status': status, 'message': message, 'outputs': outputs or [],
                                'errorCode': 'OPERATION_FAILED' if status == 'failed' else None})


def checkpoint():
    context = _current.get()
    if context and context.cancel.is_set():
        raise TaskCancelled('任务已取消')


def report_progress(current=0, total=0, message='正在处理'):
    checkpoint()
    context = _current.get()
    if context:
        context.emit(current=current, total=total, message=message,
                     progress=min(99, round(current * 100 / total)) if total else None)


def iter_progress(items, message='正在处理'):
    total = len(items) if hasattr(items, '__len__') else 0
    report_progress(0, total, message)
    for index, item in enumerate(items, 1):
        checkpoint()
        yield item
        report_progress(index, total, message)


def publish_output(path):
    from api.core.outputs import output_asset
    context = _current.get()
    if context:
        asset = output_asset(path)
        if not any(item['path'] == asset['path'] for item in context.outputs):
            context.outputs.append(asset)
            context.emit(outputAsset=asset)


def stop_process(process):
    if process.poll() is not None:
        return
    try:
        import psutil
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.terminate()
            except psutil.Error:
                pass
        parent.terminate()
        _, alive = psutil.wait_procs([*children, parent], timeout=1)
        for child in alive:
            try:
                child.kill()
            except psutil.Error:
                pass
    except (ImportError, OSError):
        process.kill()
    except Exception:
        if process.poll() is None:
            process.kill()
    process.wait(timeout=5)


def run_process(args, *, timeout=300, text=True, input=None, check=False, **kwargs):
    """subprocess.run equivalent with cancellation and a bounded execution time."""
    import time
    checkpoint()
    kwargs.pop('capture_output', None)
    if sys.platform == 'win32':
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
    process = subprocess.Popen(args, stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, **kwargs)
    started = time.monotonic()
    first = True
    try:
        while True:
            checkpoint()
            if time.monotonic() - started > timeout:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                stdout, stderr = process.communicate(input=input if first else None, timeout=0.15)
                break
            except subprocess.TimeoutExpired:
                first = False
        result = subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result
    finally:
        if process.poll() is None:
            stop_process(process)
