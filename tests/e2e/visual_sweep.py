"""Isolated visual smoke sweep for the desktop frontend through its real API."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    import sys

    sys.path.insert(0, str(ROOT))
    from api.api import API
    from api.core.context import stop_process
    from pyapp.config.config import Config

    report_dir = ROOT / "build/verification"
    report_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppx-visual-") as temp:
        Config.appDataDir = str(Path(temp) / "app-data")
        Config.downloadDir = str(Path(temp) / "outputs")
        Path(Config.appDataDir).mkdir()
        api = API()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        log = (Path(temp) / "vite.log").open("w", encoding="utf-8")
        server = subprocess.Popen(
            ["node", str(ROOT / "gui/node_modules/vite/bin/vite.js"), "preview", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
            cwd=ROOT / "gui", stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            for _ in range(100):
                with socket.socket() as sock:
                    if sock.connect_ex(("127.0.0.1", port)) == 0:
                        break
                if server.poll() is not None:
                    raise RuntimeError("Vite preview failed to start")
                time.sleep(0.1)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.set_default_timeout(15000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                context.add_init_script(
                    "localStorage.setItem('ppx-v2-modules', JSON.stringify({video: true, seal: true, system: true}))"
                )

                def dispatch(_source, method, args):
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
                page.wait_for_load_state("networkidle")
                page.locator(".home-inner").wait_for()

                def set_theme(theme):
                    if page.locator("html").get_attribute("data-theme") != theme:
                        page.get_by_role("button", name="切换主题", exact=True).click()
                    expect(page.locator("html")).to_have_attribute("data-theme", theme)
                    page.wait_for_timeout(300)

                favorite = page.locator(".action-card").first.locator(".favorite-toggle")
                was_favorite = "active" in (favorite.get_attribute("class") or "")
                favorite.focus()
                page.keyboard.press("Enter")
                page.wait_for_timeout(100)
                now_favorite = "active" in (page.locator(".action-card").first.locator(".favorite-toggle").get_attribute("class") or "")
                assert now_favorite != was_favorite, "Favorite button did not respond to Enter"
                assert page.locator(".sidebar .home.on").count() == 1, "Favorite keyboard action navigated away from home"

                visual = []
                for width, height, suffix in ((1440, 1000, "desktop"), (900, 760, "narrow")):
                    page.set_viewport_size({"width": width, "height": height})
                    for theme in ("light", "dark"):
                        set_theme(theme)
                        horizontal_overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
                        assert not horizontal_overflow, f"Home horizontal overflow at {width}px, {theme}"
                        filename = f"home-{suffix}-{theme}.png"
                        page.screenshot(path=str(report_dir / filename), full_page=True, animations="disabled")
                        visual.append({"file": filename, "width": width, "height": height, "theme": theme})

                navigation = page.get_by_role("navigation", name="工具", exact=True)
                page.set_viewport_size({"width": 900, "height": 760})
                navigation.get_by_role("button", name="文本工具", exact=True).click()
                page.get_by_role("button", name="文本转换", exact=True).click()
                expect(page.locator(".subtab.on")).to_have_text("文本转换")
                transform_grid = page.locator(".text-grid:visible")
                input_box = transform_grid.locator("textarea").bounding_box()
                output_box = transform_grid.locator(".preview-panel").bounding_box()
                assert input_box and output_box and input_box["width"] >= 175 and output_box["width"] >= 175
                expect(transform_grid.locator(".preview-empty")).to_have_text("处理后在此查看结果")

                page.get_by_role("button", name="JSON 工具", exact=True).click()
                json_grid = page.locator(".text-grid:visible")
                json_grid.locator("textarea").fill('{"items":[{"name":"desk"}]}')
                json_grid.get_by_role("button", name="执行", exact=True).click()
                expect(json_grid.locator(".preview-body code")).to_contain_text('"name": "desk"')
                json_grid.locator("textarea").fill('{"items":')
                json_grid.get_by_role("button", name="执行", exact=True).click()
                expect(page.locator(".el-message--error").last).to_contain_text("不是有效的 JSON 格式")

                page.get_by_role("button", name="文本转换", exact=True).click()
                transform_grid = page.locator(".text-grid:visible")
                transform_grid.locator("textarea").fill("Atelier Paper")
                transform_grid.get_by_role("button", name="转换", exact=True).click()
                expect(transform_grid.locator(".preview-body code")).to_have_text("ATELIER PAPER")
                expect(page.locator(".el-message")).to_have_count(0)
                for theme in ("light", "dark"):
                    set_theme(theme)
                    filename = f"text-tools-narrow-{theme}.png"
                    page.screenshot(path=str(report_dir / filename), full_page=True, animations="disabled")
                    visual.append({"file": filename, "width": 900, "height": 760, "theme": theme})

                page.get_by_role("button", name="去重 / 排序", exact=True).click()
                dedup_grid = page.locator(".text-grid:visible")
                dedup_grid.locator("textarea").fill("pear\napple\npear\n")
                dedup_grid.get_by_role("button", name="执行", exact=True).click()
                expect(dedup_grid.locator(".preview-body code")).to_have_text("pear\napple")
                expect(page.locator(".stats-panel")).to_contain_text("移除行数")

                page.get_by_role("button", name="批量替换", exact=True).click()
                replace_grid = page.locator(".text-grid:visible")
                page.get_by_placeholder("查找内容（支持正则）", exact=True).fill("pear")
                page.get_by_placeholder("替换为（可留空）", exact=True).fill("apple")
                replace_grid.locator("textarea").fill("pear pear")
                replace_grid.get_by_role("button", name="执行", exact=True).click()
                expect(replace_grid.locator(".preview-body code")).to_have_text("apple apple")
                page.get_by_placeholder("查找内容（支持正则）", exact=True).fill("[")
                page.get_by_placeholder("替换为（可留空）", exact=True).fill("x")
                page.locator(".rule-row:visible .el-checkbox").filter(has_text="正则").click()
                replace_grid.locator("textarea").fill("invalid regex")
                replace_grid.get_by_role("button", name="执行", exact=True).click()
                expect(page.locator(".el-message--error").last).to_contain_text("批量替换失败")

                page.set_viewport_size({"width": 1440, "height": 1000})
                modules = ["转换中心", "图片处理", "PDF 工具", "Word 工具", "Excel 工具", "文档中心", "文件批处理", "自动化工作流", "网页数据采集", "文本工具", "视频处理", "印章图片生成", "设置与维护", "系统诊断（高级）"]
                navigated = []
                for name in modules:
                    button = navigation.get_by_role("button", name=name, exact=True)
                    if not button.count() and name != "系统诊断（高级）":
                        raise AssertionError(f"Missing module: {name}")
                    if button.count():
                        button.click()
                        page.wait_for_timeout(450)
                        assert page.locator(".active-tool-view").inner_text().strip(), f"Empty view: {name}"
                        navigated.append(name)
                assert not errors, errors
                result = {"passed": True, "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "visuals": visual, "favoriteKeyboard": "toggles without navigating", "textWorkflows": ["JSON format and invalid JSON feedback", "case transform", "deduplicate and statistics", "literal replacement and invalid regex feedback"], "navigationSmoke": navigated, "pageErrors": errors}
                (report_dir / "visual-sweep.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                browser.close()
        finally:
            api.task_shutdown()
            api.workflow_stop()
            stop_process(server)
            log.close()


if __name__ == "__main__":
    main()
