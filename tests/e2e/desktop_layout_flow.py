"""Exercise desktop layout bounds and the window resize bridge from the UI."""

from __future__ import annotations

import json

from playwright.sync_api import expect


def _assert_reachable(page, locator, label, viewport):
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    assert box, f'{label} has no rendered bounds at {viewport}'
    width = page.locator('body').evaluate('(node) => node.clientWidth')
    height = page.locator('body').evaluate('(node) => node.clientHeight')
    assert box['x'] >= -1 and box['y'] >= -1, f'{label} starts outside viewport at {viewport}: {box}'
    assert box['x'] + box['width'] <= width + 1, f'{label} is clipped horizontally at {viewport}: {box}'
    assert box['y'] + box['height'] <= height + 1, f'{label} is clipped vertically at {viewport}: {box}'
    hit = locator.evaluate('''(node) => {
      const rect = node.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const target = document.elementFromPoint(x, y);
      return Boolean(target && (target === node || node.contains(target)));
    }''')
    assert hit, f'{label} is covered by another element at {viewport}: {box}'
    return {'label': label, 'bounds': {key: round(value, 1) for key, value in box.items()}}


def _assert_no_page_overflow(page, viewport, view_name):
    overflow = page.evaluate('''() => ({
      document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
      workspace: document.querySelector('.workspace')?.scrollWidth - document.querySelector('.workspace')?.clientWidth,
      activeView: document.querySelector('.active-tool-view')?.scrollWidth - document.querySelector('.active-tool-view')?.clientWidth,
    })''')
    assert all(value <= 1 for value in overflow.values()), f'{view_name} has horizontal overflow at {viewport}: {overflow}'
    return overflow


def _verify_minimum_viewport(page, width, height, report_dir):
    viewport = f'{width}x{height}'
    page.set_viewport_size({'width': width, 'height': height})
    page.wait_for_timeout(80)
    page.locator('.sidebar .home').click()
    nav = page.get_by_role('navigation', name='工具', exact=True)
    close = page.get_by_role('button', name='关闭', exact=True)
    reachable = [_assert_reachable(page, close, '标题栏关闭按钮', viewport)]
    checked = [_assert_no_page_overflow(page, viewport, '首页')]

    reachable.append(_assert_reachable(page, page.locator('.sidebar').get_by_role('button', name='首页', exact=True), '主导航：首页', viewport))
    home_scroll = page.locator('.home-scroll')
    home_metrics = home_scroll.evaluate('(node) => ({clientHeight: node.clientHeight, scrollHeight: node.scrollHeight, clientWidth: node.clientWidth, scrollWidth: node.scrollWidth})')
    assert home_metrics['clientHeight'] > 0 and home_metrics['scrollHeight'] >= home_metrics['clientHeight'], (viewport, home_metrics)
    home_scroll.evaluate('(node) => { node.scrollTop = node.scrollHeight }')
    home_action = page.locator('.home-scroll .module-cta')
    reachable.append(_assert_reachable(page, home_action, '首页模块管理入口', viewport))
    page.screenshot(path=str(report_dir / f'desktop-layout-home-{width}x{height}.png'), full_page=True, animations='disabled')
    home_scroll.evaluate('(node) => { node.scrollTop = 0 }')

    pdf_nav = page.get_by_role('navigation', name='工具', exact=True).get_by_role('button', name='PDF 工具', exact=True)
    reachable.append(_assert_reachable(page, pdf_nav, '主导航：PDF工具', viewport))
    pdf_nav.click()
    tabs = page.get_by_role('navigation', name='子功能', exact=True)
    cut_tab = tabs.get_by_role('button', name='页码切割', exact=True)
    reachable.append(_assert_reachable(page, cut_tab, 'PDF页码切割入口', viewport))
    cut_tab.click()
    form_area = page.locator('.ws .form-area')
    cut_scroll = form_area.evaluate('(node) => ({clientHeight: node.clientHeight, scrollHeight: node.scrollHeight, clientWidth: node.clientWidth, scrollWidth: node.scrollWidth})')
    assert cut_scroll['clientHeight'] > 0 and cut_scroll['scrollWidth'] <= cut_scroll['clientWidth'] + 1, (viewport, cut_scroll)
    form_area.evaluate('(node) => { node.scrollTop = node.scrollHeight }')
    cut_panel = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='按页码摘取页面', exact=True))
    cut_button = cut_panel.get_by_role('button', name='生成新 PDF', exact=True)
    reachable.append(_assert_reachable(page, cut_button, '页码切割执行按钮', viewport))
    checked.append(_assert_no_page_overflow(page, viewport, 'PDF页码切割'))
    page.screenshot(path=str(report_dir / f'desktop-layout-pdf-cut-{width}x{height}.png'), full_page=True, animations='disabled')

    file_nav = nav.get_by_role('button', name='文件批处理', exact=True)
    reachable.append(_assert_reachable(page, file_nav, '主导航：文件批处理', viewport))
    file_nav.click()
    page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='文件搜索', exact=True).click()
    search = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='查找文件，再继续处理', exact=True))
    search_button = search.get_by_role('button', name='开始搜索', exact=True)
    reachable.append(_assert_reachable(page, search_button, '文件搜索执行按钮', viewport))
    checked.append(_assert_no_page_overflow(page, viewport, '文件搜索'))

    text_nav = nav.get_by_role('button', name='文本工具', exact=True)
    reachable.append(_assert_reachable(page, text_nav, '主导航：文本工具', viewport))
    text_nav.click()
    tabs = page.get_by_role('navigation', name='子功能', exact=True)
    json_tab = tabs.get_by_role('button', name='JSON 工具', exact=True)
    reachable.append(_assert_reachable(page, json_tab, '文本JSON工具入口', viewport))
    json_tab.click()
    json_panel = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='JSON 格式化、压缩与查询', exact=True))
    json_button = json_panel.get_by_role('button', name='执行', exact=True)
    reachable.append(_assert_reachable(page, json_button, 'JSON执行按钮', viewport))
    checked.append(_assert_no_page_overflow(page, viewport, '文本JSON'))
    page.screenshot(path=str(report_dir / f'desktop-layout-text-json-{width}x{height}.png'), full_page=True, animations='disabled')

    return {'width': width, 'height': height, 'homeContent': home_metrics, 'pdfCutScroll': cut_scroll, 'reachableControls': reachable, 'horizontalOverflow': checked}


def verify_desktop_layout(page, report_dir):
    viewports = ((1440, 900), (1120, 780), (900, 700), (768, 620))
    screenshots = []
    for width, height in viewports:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(80)
        shell = page.locator('.app-shell').bounding_box()
        assert shell and shell['width'] <= width + 1 and shell['height'] <= height + 1, (width, height, shell)
        assert page.locator('.app-shell').evaluate('(node) => node.scrollWidth <= node.clientWidth + 1'), f'App shell overflows horizontally at {width}px'
        if width in (1440, 900, 768):
            name = f'desktop-layout-{width}.png'
            page.screenshot(path=str(report_dir / name), full_page=True, animations='disabled')
            screenshots.append(name)

    # Validate that native resizing is requested once on pointer-down and that
    # the non-native fallback folds a burst of pointer-move events into one RAF.
    handle = page.locator('.window-resize-handles .resize-e')
    assert handle.count() == 1, 'Desktop resize handle is unavailable in the webview bridge'
    page.evaluate("""() => {
      window.__resizeEvidence = {nativeCalls: [], fallbackCalls: []};
      window.pywebview.api.begin_native_resize = async (direction) => {
        window.__resizeEvidence.nativeCalls.push(direction);
        return {code: 0, supported: true};
      };
      window.pywebview.api.resize_window = async (payload) => {
        window.__resizeEvidence.fallbackCalls.push(payload);
        return {code: 0, success: true};
      };
    }""")
    handle.dispatch_event('pointerdown', {'pointerId': 7, 'pointerType': 'mouse', 'isPrimary': True, 'button': 0, 'buttons': 1, 'clientX': 1200, 'clientY': 400})
    page.wait_for_timeout(20)
    native = page.evaluate('window.__resizeEvidence')
    assert native['nativeCalls'] == ['e'], native
    assert native['fallbackCalls'] == [], native

    page.evaluate("""() => {
      window.__resizeEvidence.nativeCalls = [];
      window.__resizeEvidence.fallbackCalls = [];
      window.pywebview.api.begin_native_resize = async (direction) => {
        window.__resizeEvidence.nativeCalls.push(direction);
        return {code: 0, supported: false};
      };
    }""")
    handle.dispatch_event('pointerdown', {'pointerId': 8, 'pointerType': 'mouse', 'isPrimary': True, 'button': 0, 'buttons': 1, 'clientX': 1200, 'clientY': 400})
    page.evaluate("""() => {
      for (let index = 1; index <= 24; index += 1) {
        window.dispatchEvent(new PointerEvent('pointermove', {
          pointerId: 8, pointerType: 'mouse', isPrimary: true, buttons: 1,
          clientX: 1200 + index, clientY: 400
        }));
      }
    }""")
    page.wait_for_timeout(80)
    fallback = page.evaluate('window.__resizeEvidence')
    assert fallback['nativeCalls'] == ['e'], fallback
    assert len(fallback['fallbackCalls']) == 1, fallback
    assert fallback['fallbackCalls'][0]['width'] > 0 and fallback['fallbackCalls'][0]['height'] > 0, fallback
    page.evaluate("window.dispatchEvent(new PointerEvent('pointerup', {pointerId: 8, pointerType: 'mouse', button: 0, buttons: 0}))")
    expect(handle).to_be_visible()

    minimum_viewports = ((640, 400), (627, 364), (617, 360), (605, 348), (603, 341))
    minimum_evidence = [_verify_minimum_viewport(page, width, height, report_dir) for width, height in minimum_viewports]
    page.set_viewport_size({'width': 1440, 'height': 900})
    report = {
        'passed': True,
        'browserViewportBounds': [{'width': width, 'height': height} for width, height in viewports],
        'minimumViewportUsability': minimum_evidence,
        'nativeResize': 'one direction request on pointer-down; no JS resize calls',
        'fallbackResize': '24 pointer moves coalesced into one resize request',
        'screenshots': screenshots + [
            f'desktop-layout-{view}-{width}x{height}.png'
            for width, height in minimum_viewports
            for view in ('home', 'pdf-cut', 'text-json')
        ],
        'limitations': ['Browser viewport checks establish rendered control reachability at the measured CSS sizes; they do not establish native Windows compositor flicker behavior.'],
    }
    (report_dir / 'desktop-layout-flow.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
