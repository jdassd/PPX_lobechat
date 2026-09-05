"""Browser → real desktop API → worker → output verification (isolated test data)."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import fitz
from PIL import Image
from playwright.sync_api import expect, sync_playwright
from web_collection_flow import verify_web_collection

from api.api import API
from api.core.context import stop_process
from pyapp.config.config import Config


def main():
    with tempfile.TemporaryDirectory(prefix="ppx-e2e-") as temp:
        root = Path(temp)
        Config.appDataDir = str(root / "app-data")
        Config.downloadDir = str(root / "outputs")
        Path(Config.appDataDir).mkdir()
        first, missing = root / "first.png", root / "retry.png"
        Image.new("RGBA", (300, 200), (30, 90, 180, 100)).save(first)
        pdf_source = root / 'thousand-pages.pdf'
        document = fitz.open()
        for number in range(1, 1001):
            document.new_page(width=200, height=250).insert_text((20, 40), f'PAGE {number}')
        document.save(pdf_source)
        document.close()
        chosen = [first, missing]
        api = API()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server_log = (root / "vite.log").open("w", encoding="utf-8")
        server = subprocess.Popen(
            [
                "node",
                str(ROOT / "gui/node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--strictPort",
            ],
            cwd=ROOT / "gui",
            stdout=server_log,
            stderr=server_log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        report_dir = ROOT / "build/verification"
        report_dir.mkdir(parents=True, exist_ok=True)
        try:
            for _ in range(100):
                with socket.socket() as sock:
                    if sock.connect_ex(("127.0.0.1", port)) == 0:
                        break
                if server.poll() is not None:
                    raise RuntimeError("Vite failed to start")
                time.sleep(0.1)
            with sync_playwright() as playwright:
                browser_options = {"headless": True}
                edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
                if edge.exists():
                    browser_options["executable_path"] = str(edge)
                browser = playwright.chromium.launch(**browser_options)
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.set_default_timeout(15000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def dispatch(_source, method, args):
                    if method == "system_pyCreateFileDialog":
                        return [{"path": str(path), "filename": path.name, "ext": path.suffix, "dir": str(path.parent)} for path in chosen]
                    if method == "system_pySelectDirDialog":
                        return str(root / "outputs")
                    if method.startswith("system_") and method not in {
                        "system_getAppConfig",
                        "system_getEnv",
                        "system_getSetting",
                    }:
                        return {"code": 0, "success": True}
                    try:
                        return getattr(api, method)(*args)
                    except Exception as exc:
                        return {"code": -1, "msg": str(exc)}

                page.expose_binding("ppxCall", dispatch)
                methods = [name for name in dir(api) if not name.startswith("_") and callable(getattr(api, name))]
                context.add_init_script(
                    "window.pywebview = {api: Object.fromEntries("
                    + json.dumps(methods)
                    + ".map(method => [method, (...args) => window.ppxCall(method, args)]))};"
                )
                page.goto(f"http://127.0.0.1:{port}")
                navigation = page.get_by_role("navigation", name="工具")
                navigation.get_by_role("button", name="图片处理", exact=True).click()
                page.get_by_text("目标体积", exact=True).click()
                value = page.locator('input[role="spinbutton"]:visible').first
                value.fill("128")
                value.press("Tab")
                navigation.get_by_role("button", name="PDF 工具", exact=True).click()
                navigation.get_by_role("button", name="图片处理", exact=True).click()
                expect(page.locator('input[role="spinbutton"]:visible').first).to_have_value("128")
                page.reload()
                navigation.get_by_role("button", name="图片处理", exact=True).click()
                expect(page.locator('input[role="spinbutton"]:visible').first).to_have_value("128")
                page.locator("button:visible").filter(has_text="选择文件").first.click()
                page.get_by_role("button", name="开始压缩", exact=True).click()
                page.get_by_role("button", name="打开任务中心", exact=True).click()
                try:
                    expect(page.locator(".task-card").filter(has_text="部分成功")).to_be_visible(timeout=30000)
                except Exception:
                    page.screenshot(path=str(report_dir / "failure.png"), full_page=True)
                    print(
                        json.dumps(
                            {"tasks": api.task_list(), "errors": errors, "body": page.locator("body").inner_text()},
                            ensure_ascii=False,
                            default=str,
                        )
                    )
                    raise
                tasks = api.task_list()["tasks"]
                partial = next(task for task in tasks if task["status"] == "partial")
                assert len(partial["outputs"]) == 1, partial
                Image.new("RGBA", (250, 150), (180, 90, 30, 50)).save(missing)
                page.get_by_role("button", name="重试", exact=True).first.click()
                expect(page.locator('.task-title-row .el-tag').filter(has_text=re.compile('^已完成$')).first).to_be_visible(timeout=60000)
                retry = next(task for task in api.task_list()["tasks"] if task.get("retryOf") == partial["id"])
                assert retry["args"][0]["files"] == [str(missing)], retry
                with Image.open(retry["outputs"][0]["path"]) as output:
                    assert output.size == (250, 150)
                    assert output.mode == "RGBA"
                page.get_by_role("button", name="检查结果 / 继续处理", exact=False).first.click()
                page.locator(".el-dialog:visible .el-select__wrapper").click()
                page.get_by_role("option", name="图片工具", exact=True).click()
                page.get_by_role("button", name="将全部结果交给下一工具", exact=True).click()
                expect(page.get_by_text("已带入 1 个结果", exact=False)).to_be_visible()
                chosen = [pdf_source]
                navigation.get_by_role('button', name='PDF 工具', exact=True).click()
                page.get_by_role('button', name='页面工作台', exact=True).click()
                page.get_by_role('button', name='选择 PDF', exact=True).click()
                expect(page.get_by_text('原 1000 页 → 保留 1000 页', exact=True)).to_be_visible(timeout=20000)
                expect(page.locator('.page-card')).to_have_count(24)
                page.get_by_placeholder('原页码范围：1-8,12', exact=True).fill('1-2')
                page.get_by_role('button', name='批选', exact=True).click()
                page.get_by_role('button', name='删除所选 2', exact=True).click()
                expect(page.get_by_text('原 1000 页 → 保留 998 页', exact=True)).to_be_visible()
                page.get_by_role('button', name='撤销', exact=True).click()
                page.get_by_placeholder('原页码范围：1-8,12', exact=True).fill('1')
                page.get_by_role('button', name='批选', exact=True).click()
                page.get_by_role('button', name='旋转所选', exact=True).click()
                position = page.locator('.page-toolbar input[role="spinbutton"]')
                position.fill('3')
                position.press('Tab')
                page.get_by_role('button', name='移动', exact=True).click()
                page.locator('input[placeholder="输出目录"]:visible').fill(str(root / 'pdf-output'))
                page.get_by_role('button', name='生成新 PDF', exact=True).click()
                expect(page.get_by_role('button', name='打开结果', exact=True)).to_be_visible(timeout=60000)
                pdf_task = next(task for task in api.task_list()['tasks'] if task['method'] == 'pdf_page_workbench')
                with fitz.open(pdf_task['outputs'][0]['path']) as result:
                    assert len(result) == 1000
                    assert 'PAGE 2' in result[0].get_text()
                    assert 'PAGE 1' in result[2].get_text() and result[2].rotation == 90
                navigation.get_by_role("button", name="自动化工作流", exact=True).click()
                try:
                    expect(page.get_by_text("高级 JSON 编辑", exact=True).first).to_be_visible(timeout=15000)
                except Exception:
                    page.screenshot(path=str(report_dir / "failure.png"), full_page=True)
                    print(json.dumps({"errors": errors, "body": page.locator("body").inner_text()}, ensure_ascii=False))
                    raise
                chosen = [first]
                editor = page.locator('.workflow-editor')
                editor.locator('.two-columns input').first.fill('Browser verified workflow')
                first_step = editor.locator('.step-card').first
                first_step.locator('.step-row .el-select__wrapper').first.click()
                page.get_by_role('option', name='批量压缩图片', exact=True).click()
                first_step.locator('.operation-form .el-form-item').filter(has_text='输入文件').get_by_role('button', name='选择', exact=True).click()
                editor.get_by_role('button', name='+ 添加步骤', exact=True).click()
                next_step = editor.locator('.step-card').nth(1)
                next_step.locator('.step-row .el-select__wrapper').first.click()
                choices_id = next_step.locator('.step-row [role="combobox"]').first.get_attribute('aria-controls')
                page.locator('[id="' + choices_id + '"]').get_by_role('option', name='旋转与翻转图片', exact=True).click()
                next_step.locator('.operation-form .el-form-item').filter(has_text='输入文件').locator('.reference .el-select__wrapper').click()
                page.get_by_role('option', name='第一个步骤', exact=True).click()
                editor.get_by_role('button', name='保存', exact=True).click()
                expect(editor.get_by_role('button', name='立即运行', exact=True)).to_be_enabled(timeout=15000)
                editor.get_by_role('button', name='立即运行', exact=True).click()
                expect(page.get_by_text('工作流执行完成', exact=True)).to_be_visible(timeout=60000)
                workflow_task = next(task for task in api.task_list()['tasks'] if task['method'] == 'workflow_run')
                assert workflow_task['status'] == 'success', workflow_task
                assert len(workflow_task['result']['run']['steps']) == 2
                rotated = workflow_task['result']['run']['steps'][1]['result']['outputAssets'][0]['path']
                with Image.open(rotated) as image:
                    assert image.size == (200, 300), workflow_task['result']['run']['steps']
                for name in ('Word 工具', 'Excel 工具', '视频处理', '文件批处理', '文本工具', '文档中心', '网页数据采集', '印章图片生成', '转换中心', '设置与维护', '系统诊断（高级）'):
                    button = navigation.get_by_role('button', name=name, exact=True)
                    if button.count():
                        button.click()
                        page.wait_for_timeout(500)
                assert not errors, errors
                page.get_by_role('button', name='打开任务中心', exact=True).click()
                page.get_by_role('button', name='暂停队列', exact=True).click()
                expect(page.get_by_role('button', name='继续队列', exact=True)).to_be_visible()
                canceled = api.task_submit({'method': 'image_batch_compress', 'args': [{'files': [str(first)], 'outputDir': str(root / 'must-not-exist')}]})
                assert canceled['code'] == 0, canceled
                page.get_by_role('button', name='刷新', exact=True).click()
                pending_card = page.locator('.task-card').filter(has_text='排队中')
                expect(pending_card).to_have_count(1)
                pending_card.get_by_role('button', name='取消', exact=True).click()
                expect(page.locator('.task-title-row .el-tag').filter(has_text=re.compile('^已取消$'))).to_be_visible()
                assert api.task_get(canceled['taskId'])['task']['status'] == 'canceled'
                assert not (root / 'must-not-exist').exists()
                page.get_by_role('button', name='继续队列', exact=True).click()
                verify_web_collection(api, context)
                report_dir = ROOT / "build/verification"
                report_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(report_dir / 'workspace.png'), full_page=True)
                (report_dir / 'workspace.json').write_text(json.dumps({
                    'passed': True, 'pageErrors': errors,
                    'checks': ['draft retention', 'restart configuration', 'partial failure', 'retry only failed input',
                               'output dimensions and alpha', 'handoff scoped to target module', '1000-page PDF editing/undo/reorder/export',
                               'two-step workflow via forms', 'pause only blocks new tasks', 'cancel queued task',
                               'browser collection detail retry without duplicate rows']
                }, indent=2), encoding='utf-8')
                browser.close()
                print(
                    "PASS: draft retention, restart configuration, real processing, partial failure, retry only failed input, output validation, scoped result handoff, 1000-page PDF editing/undo/reorder/export, two-step workflow via forms, queue pause/cancel, zero page errors"
                )
        finally:
            api.task_shutdown()
            api.workflow_stop()
            stop_process(server)
            server_log.close()


if __name__ == "__main__":
    main()
