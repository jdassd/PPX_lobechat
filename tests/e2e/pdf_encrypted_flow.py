"""Exercise encrypted PDF cutting through the browser and real API bridge."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz
from playwright.sync_api import expect


def _make_pdf(path: Path, encryption: int, user_password: str, label: str) -> None:
    document = fitz.open()
    for index in range(1, 4):
        page = document.new_page(width=220, height=280)
        page.insert_text((24, 44), f'{label} PAGE {index}')
    document.save(path, encryption=encryption, owner_pw='e2e-owner-password', user_pw=user_password)
    document.close()


def _select_source(page, chosen, path: Path) -> None:
    chosen[:] = [path]
    panel = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='按页码摘取页面', exact=True))
    panel.get_by_role('button', name='选择 PDF', exact=True).click()
    expect(panel.locator('.file-chip')).to_have_text(path.name)
    return panel


def _choose_output_dir(page, panel, output_dir: Path) -> None:
    field = panel.locator('.el-form-item').filter(has=page.locator('.el-form-item__label').filter(has_text='输出目录'))
    field.get_by_role('button', name='选择目录', exact=True).click()
    expect(field.locator('input[readonly]')).to_have_value(str(output_dir))


def _read_pages(path: Path) -> list[str]:
    with fitz.open(path) as result:
        return [page.get_text().strip() for page in result]


def verify_pdf_encrypted_flow(api, page, root, chosen, report_dir):
    fixture_dir = root / 'pdf-encrypted-fixtures'
    fixture_dir.mkdir()
    output_dir = root / 'outputs'
    output_dir.mkdir(exist_ok=True)
    aes128 = fixture_dir / 'aes128.pdf'
    aes256 = fixture_dir / 'aes256.pdf'
    empty_password = fixture_dir / 'aes128-empty-user-password.pdf'
    _make_pdf(aes128, fitz.PDF_ENCRYPT_AES_128, 'open-secret-128', 'AES128')
    _make_pdf(aes256, fitz.PDF_ENCRYPT_AES_256, 'open-secret-256', 'AES256')
    _make_pdf(empty_password, fitz.PDF_ENCRYPT_AES_128, '', 'EMPTY')
    source_digests = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (aes128, aes256, empty_password)}

    navigation = page.get_by_role('navigation', name='工具', exact=True)
    navigation.get_by_role('button', name='PDF 工具', exact=True).click()
    tabs = page.get_by_role('navigation', name='子功能', exact=True)
    tabs.get_by_role('button', name='页码切割', exact=True).click()
    panel = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='按页码摘取页面', exact=True))
    password = panel.locator('input[autocomplete="new-password"]')
    _choose_output_dir(page, panel, output_dir)
    panel.locator('.el-radio-button').filter(has_text='指定页码').click()
    panel.get_by_placeholder('示例：1-3,5,8；支持用分号或换行分隔多个区间', exact=True).fill('1,3')

    panel = _select_source(page, chosen, aes128)
    password.fill('open-secret-128')
    expect(password).to_have_value('open-secret-128')
    assert 'open-secret-128' not in page.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage)))')
    panel.get_by_placeholder('例如：摘录.pdf', exact=True).fill('aes128-pages-1-and-3.pdf')
    panel.get_by_role('button', name='生成新 PDF', exact=True).click()
    expect(panel.get_by_text(str(output_dir / 'aes128-pages-1-and-3.pdf'), exact=True)).to_be_visible(timeout=60000)
    aes128_output = output_dir / 'aes128-pages-1-and-3.pdf'
    assert _read_pages(aes128_output) == ['AES128 PAGE 1', 'AES128 PAGE 3']
    assert hashlib.sha256(aes128.read_bytes()).hexdigest() == source_digests[aes128]

    # Replacing the source must clear the previous file's password and result.
    panel = _select_source(page, chosen, aes256)
    expect(password).to_have_value('')
    expect(panel.get_by_text(str(aes128_output), exact=True)).to_have_count(0)
    panel.locator('input[placeholder="例如：摘录.pdf"]:visible').fill('aes256-pages-1-and-3.pdf')
    password.fill('open-secret-256')
    panel.get_by_role('button', name='生成新 PDF', exact=True).click()
    expect(panel.get_by_text(str(output_dir / 'aes256-pages-1-and-3.pdf'), exact=True)).to_be_visible(timeout=60000)
    aes256_output = output_dir / 'aes256-pages-1-and-3.pdf'
    assert _read_pages(aes256_output) == ['AES256 PAGE 1', 'AES256 PAGE 3']
    assert hashlib.sha256(aes256.read_bytes()).hexdigest() == source_digests[aes256]

    # Wrong and absent credentials must fail without leaving output files.
    for supplied_password, output_name in (('wrong-password', 'wrong-password.pdf'), ('', 'missing-password.pdf')):
        panel.locator('input[placeholder="例如：摘录.pdf"]:visible').fill(output_name)
        password.fill(supplied_password)
        page.locator('.el-message--error').evaluate_all('(nodes) => nodes.forEach(node => node.remove())')
        panel.get_by_role('button', name='生成新 PDF', exact=True).click()
        error = page.locator('.el-message--error').last
        expect(error).to_be_visible(timeout=30000)
        expect(error).not_to_have_text('')
        assert not (output_dir / output_name).exists(), output_dir / output_name
        assert hashlib.sha256(aes256.read_bytes()).hexdigest() == source_digests[aes256]

    panel = _select_source(page, chosen, empty_password)
    expect(password).to_have_value('')
    panel.locator('input[placeholder="例如：摘录.pdf"]:visible').fill('empty-user-password.pdf')
    panel.get_by_role('button', name='生成新 PDF', exact=True).click()
    expect(panel.get_by_text(str(output_dir / 'empty-user-password.pdf'), exact=True)).to_be_visible(timeout=60000)
    empty_output = output_dir / 'empty-user-password.pdf'
    assert _read_pages(empty_output) == ['EMPTY PAGE 1', 'EMPTY PAGE 3']
    assert hashlib.sha256(empty_password.read_bytes()).hexdigest() == source_digests[empty_password]

    tabs.get_by_role('button', name='拆分 PDF', exact=True).click()
    split = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='按固定页数拆分', exact=True))
    chosen[:] = [aes256]
    split.get_by_role('button', name='选择 PDF', exact=True).click()
    split_password = split.locator('input[autocomplete="new-password"]')
    expect(split_password).to_have_value('')
    split_password.fill('open-secret-256')
    split.locator('input[role="spinbutton"]:visible').fill('2')
    split.locator('.el-form-item').filter(has=page.locator('.el-form-item__label').filter(has_text='输出目录')).get_by_role('button', name='选择目录', exact=True).click()
    split.get_by_role('button', name='开始拆分', exact=True).click()
    split_files = split.locator('.result-list .el-tag')
    expect(split_files).to_have_count(2, timeout=60000)
    split_paths = [Path(split_files.nth(index).inner_text()) for index in range(2)]
    assert [_read_pages(path) for path in split_paths] == [['AES256 PAGE 1', 'AES256 PAGE 2'], ['AES256 PAGE 3']]
    assert hashlib.sha256(aes256.read_bytes()).hexdigest() == source_digests[aes256]

    tabs.get_by_role('button', name='合并 PDF', exact=True).click()
    merge = page.locator('.panel:visible').filter(has=page.get_by_role('heading', name='将多个 PDF 合并', exact=True))
    # Earlier workspace workflows may have left their own queue in this draft.
    while merge.locator('.queue-row').count():
        merge.locator('.queue-row button[aria-label^="移除 "]').first.click()
    chosen[:] = [aes128, aes256]
    merge.get_by_role('button', name='添加 PDF', exact=True).click()
    rows = merge.locator('.queue-row')
    expect(rows).to_have_count(2)
    rows.nth(0).locator('input[aria-label="aes128.pdf 页码"]').fill('1-2')
    rows.nth(0).locator('input[type="password"]').fill('open-secret-128')
    rows.nth(1).locator('input[aria-label="aes256.pdf 页码"]').fill('2-3')
    rows.nth(1).locator('input[type="password"]').fill('open-secret-256')
    merge.locator('.el-form-item').filter(has=page.locator('.el-form-item__label').filter(has_text='输出目录')).get_by_role('button', name='选择目录', exact=True).click()
    merge.get_by_placeholder('例如：合并结果.pdf', exact=True).fill('encrypted-merge.pdf')
    merge.get_by_role('button', name='合并 PDF', exact=True).click()
    merged_path = output_dir / 'encrypted-merge.pdf'
    expect(merge.get_by_text(str(merged_path), exact=True)).to_be_visible(timeout=60000)
    assert _read_pages(merged_path) == ['AES128 PAGE 1', 'AES128 PAGE 2', 'AES256 PAGE 2', 'AES256 PAGE 3']
    assert hashlib.sha256(aes128.read_bytes()).hexdigest() == source_digests[aes128]
    assert hashlib.sha256(aes256.read_bytes()).hexdigest() == source_digests[aes256]
    assert 'open-secret-128' not in page.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage)))')
    assert 'open-secret-256' not in page.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage)))')

    report = {
        'passed': True,
        'checks': [
            'AES-128 and AES-256 correct-password cut and reopened page-order/text verification',
            'empty-user-password encrypted PDF cut without credentials',
            'wrong and missing password errors with no output artifact',
            'encrypted split and ordered per-file-password merge verified by reopening outputs',
            'source files unchanged',
            'password excluded from localStorage and cleared when changing source',
        ],
    }
    (report_dir / 'pdf-encrypted-flow.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
