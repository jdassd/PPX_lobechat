"""CAJ panel → real task worker → reopened PDF, including partial retry."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import fitz
from playwright.sync_api import expect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_caj_to_pdf import make_embedded_pdf_caj


def verify_caj_pdf_flow(api, page, root, chosen, report_dir):
    fixture_dir = root / 'caj-fixtures'
    fixture_dir.mkdir()
    good = fixture_dir / 'paper.caj'
    bad = fixture_dir / 'unsupported.caj'
    good.write_bytes(make_embedded_pdf_caj(pages=2, page_ids=[30, 3]))
    bad.write_bytes(b'HN\xc8\0' + bytes(512))
    source_digest = hashlib.sha256(good.read_bytes()).hexdigest()
    chosen[:] = [good, bad]
    navigation = page.get_by_role('navigation', name='工具', exact=True)
    navigation.get_by_role('button', name='PDF 工具', exact=True).click()
    page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='CAJ 转 PDF', exact=True).click()
    panel = page.locator('.caj-panel:visible')
    expect(panel.get_by_role('button', name='开始转换', exact=True)).to_be_disabled()
    panel.get_by_role('button', name='选择 CAJ 文件', exact=True).click()
    expect(panel.locator('.file-row')).to_have_count(2)
    panel.get_by_role('button', name='开始转换', exact=True).click()
    expect(panel.locator('.result-row')).to_have_count(2, timeout=60000)
    expect(panel.locator('.result-heading')).to_contain_text('1 项成功，1 项失败')
    expect(panel.locator('.error-copy')).to_contain_text('HN/C8')
    output = fixture_dir / 'paper.pdf'
    with fitz.open(output) as result:
        assert result.page_count == 2
        assert 'text 1' in result[0].get_text()
        assert 'text 2' in result[1].get_text()
        result[0].get_pixmap().save(str(report_dir / 'caj-pdf-page.png'))
    assert hashlib.sha256(good.read_bytes()).hexdigest() == source_digest
    assert not (fixture_dir / 'unsupported.pdf').exists()
    partial = next(task for task in api.task_list()['tasks'] if task['method'] == 'pdf_caj_to_pdf')
    assert partial['status'] == 'partial', partial
    assert len(partial['outputs']) == 1, partial

    screenshots = []
    for theme in ('light', 'dark'):
        if page.locator('html').get_attribute('data-theme') != theme:
            page.get_by_role('button', name='切换主题', exact=True).click()
        page.set_viewport_size({'width': 1000, 'height': 850})
        assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        name = f'caj-pdf-{theme}.png'
        page.screenshot(path=str(report_dir / name), full_page=True, animations='disabled')
        screenshots.append(name)

    # Recover the unsupported input, then retry through the actual task UI.
    bad.write_bytes(make_embedded_pdf_caj('recovered CAJ'))
    # Change the search while activation's old request is still in flight.
    # The latest criteria must run immediately after it, without waiting for
    # the five-second polling timer or letting the old response replace them.
    page.evaluate('''() => {
      const api = window.pywebview.api;
      window.__cajOriginalTaskList = api.task_list;
      let first = true;
      api.task_list = async (...args) => {
        if (first) { first = false; await new Promise(resolve => setTimeout(resolve, 1200)); }
        return window.__cajOriginalTaskList(...args);
      };
    }''')
    page.get_by_role('button', name='打开任务中心', exact=True).click()
    page.get_by_placeholder('搜索任务、输出路径或错误信息', exact=True).fill('CAJ 转 PDF')
    card = page.locator('.task-card').filter(has_text='CAJ 转 PDF').filter(has_text='部分成功')
    expect(card).to_have_count(1, timeout=15000)
    card.get_by_role('button', name='重试', exact=True).click()
    completed = page.locator('.task-card').filter(has_text='CAJ 转 PDF').filter(
        has=page.locator('.task-title-row .el-tag').filter(has_text=re.compile('^已完成$')))
    expect(completed).to_have_count(1, timeout=60000)
    retry = next(task for task in api.task_list()['tasks'] if task.get('retryOf') == partial['id'])
    assert retry['status'] == 'success', retry
    assert retry['args'][0]['files'] == [str(bad)], retry
    with fitz.open(fixture_dir / 'unsupported.pdf') as document:
        assert 'recovered CAJ' in document[0].get_text()

    page.evaluate('''() => {
      window.pywebview.api.task_list = window.__cajOriginalTaskList;
      delete window.__cajOriginalTaskList;
    }''')
    page.get_by_placeholder('搜索任务、输出路径或错误信息', exact=True).fill('')
    navigation.get_by_role('button', name='PDF 工具', exact=True).click()
    page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='CAJ 转 PDF', exact=True).click()
    panel = page.locator('.caj-panel:visible')
    expect(panel.get_by_role('textbox', name='输出目录', exact=True)).to_have_value('')
    panel.get_by_role('button', name='开始转换', exact=True).click()
    expect(panel.locator('.result-heading')).to_contain_text('2 项成功，0 项失败', timeout=60000)
    assert (fixture_dir / 'paper_2.pdf').is_file()
    assert (fixture_dir / 'unsupported_2.pdf').is_file()
    panel.get_by_role('button', name='选择目录', exact=True).click()
    expect(panel.get_by_role('textbox', name='输出目录', exact=True)).to_have_value(str(root / 'outputs'))
    panel.get_by_role('button', name='开始转换', exact=True).click()
    expect(panel.get_by_role('button', name='打开输出目录', exact=True)).to_be_visible(timeout=60000)
    assert (root / 'outputs/paper.pdf').is_file()
    panel.get_by_role('button', name='使用源目录', exact=True).click()
    expect(panel.get_by_role('textbox', name='输出目录', exact=True)).to_have_value('')
    assert hashlib.sha256(good.read_bytes()).hexdigest() == source_digest
    report = {
        'passed': True,
        'fixtures': 'synthetic containers following the pinned upstream CAJ layout; no real-world CAJ corpus',
        'checks': ['missing page tree and page order', 'source directory default', 'partial result and HN error',
                   'task-center retry only failed input', 'latest search wins over delayed activation refresh',
                   'repeated conversion avoids overwrites',
                   'custom output directory and reset', 'source bytes unchanged', 'light and dark panel render'],
        'screenshots': screenshots,
    }
    (report_dir / 'caj-pdf-flow.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
