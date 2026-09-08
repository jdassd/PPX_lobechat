"""Exercise persistent input lineage using real worker outputs and browser actions."""

import json
import re
from pathlib import Path

from openpyxl import Workbook
from PIL import Image
from playwright.sync_api import expect


def verify_input_origins(api, page, root, chosen, picker_calls, report_dir):
    fixtures = root / 'origins-fixtures'
    fixtures.mkdir()
    image = fixtures / 'origin-image.png'
    Image.new('RGB', (80, 60), 'navy').save(image)
    workbook = fixtures / 'origin-table.xlsx'
    book = Workbook()
    book.active.append(['name', 'value'])
    book.active.append(['Origin evidence', 7])
    book.save(workbook)
    book.close()
    note_dir = fixtures / 'document-source'
    note_dir.mkdir()
    note = note_dir / 'origin-note.txt'
    note.write_text('Origin browser evidence searchable content', encoding='utf-8')

    def tasks():
        return api.task_list({'limit': 1000})['tasks']

    def wait_task(task_id):
        for _ in range(300):
            task = api.task_get(task_id)['task']
            if task['status'] not in ('queued', 'running', 'canceling'):
                assert task['status'] == 'success', task
                return task
            page.wait_for_timeout(100)
        raise AssertionError(f'Task timeout: {task_id}')

    def seed(method, options):
        response = api.task_submit({'method': method, 'args': [options]})
        assert response['code'] == 0, response
        return wait_task(response['taskId'])

    def after_click(method, button):
        before = {task['id'] for task in tasks()}
        button.click()
        for _ in range(300):
            matching = [task for task in tasks() if task['id'] not in before and task['method'] == method]
            if matching:
                return wait_task(matching[0]['id'])
            page.wait_for_timeout(100)
        raise AssertionError(f'No browser-submitted task: {method}')

    def card_for(task):
        page.get_by_role('button', name='打开任务中心', exact=True).click()
        query = page.get_by_placeholder('搜索任务、输出路径或错误信息', exact=True)
        query.fill(task['method'])
        page.wait_for_timeout(200)
        page.get_by_role('button', name='刷新', exact=True).click()
        card = page.locator('.task-card').filter(has_text=Path(task['outputs'][0]['path']).name) if task.get('outputs') else page.locator('.task-card').first
        expect(card.first).to_be_visible()
        return card.first

    def send(task, label):
        card_for(task).get_by_role('button', name='检查结果 / 继续处理', exact=False).click()
        result = page.get_by_role('dialog', name='处理结果', exact=True)
        result.locator('.handoff-options .el-select__wrapper').click()
        page.get_by_role('option').filter(has_text=re.compile('^' + re.escape(label) + r' · 1 个文件')).click()
        result.get_by_role('button', name='交给下一工具', exact=True).click()
        expect(page.locator('.incoming-notice')).to_be_visible()

    def assert_origin(child, parent):
        origins = child.get('inputOrigins', [])
        assert len(origins) == 1, child
        assert origins[0]['sourceTaskId'] == parent['id'], child
        assert Path(origins[0]['inputPath']) == Path(parent['outputs'][0]['path']), child
        assert 'inputOrigins' not in json.dumps(child['args']), child
        assert 'sourceTaskId' not in json.dumps(child['args']), child

    page.evaluate("localStorage.setItem('ppx-v2-modules', JSON.stringify({document: true}))")
    page.reload()
    parent = seed('image_batch_compress', {'files': [str(image)], 'outputDir': str(fixtures / ('long-output-directory-' * 4))})
    send(parent, '旋转图片')
    before = {task['id'] for task in tasks()}
    picker_count = len(picker_calls)
    page.get_by_role('button', name='使用上一步结果：1 个文件', exact=True).click()
    assert len(picker_calls) == picker_count
    panel = page.locator('.panel:visible')
    panel.get_by_role('button', name='预览第一张图片的处理效果', exact=True).click()
    page.wait_for_timeout(600)
    assert {task['id'] for task in tasks()} == before, 'Receive/preview executed a task'
    child = after_click('image_rotate_flip', panel.get_by_role('button', name='开始处理', exact=True))
    assert_origin(child, parent)
    drafts = page.evaluate("Object.entries(localStorage).filter(([key]) => key.startsWith('ppx-workspace-v1:')).map(([, value]) => value).join(' ')")
    assert parent['id'] not in drafts and 'sourceTaskId' not in drafts and 'inputOrigins' not in drafts, drafts
    with Image.open(child['outputs'][0]['path']) as rotated:
        assert rotated.size == (60, 80)

    # A source excluded by the method filter must still be fetched via task_get.
    card_for(child).locator('.task-origins-button').click()
    dialog = page.get_by_role('dialog', name='输入来源', exact=True)
    expect(dialog.locator('.origin-path')).to_have_text(parent['outputs'][0]['path'])
    expect(page.locator('.task-card')).not_to_contain_text('批量压缩图片')
    page.set_viewport_size({'width': 980, 'height': 760})
    expect(page.locator('.el-message:visible')).to_have_count(0)
    page.wait_for_timeout(400)
    for theme in ('light', 'dark'):
        page.evaluate("theme => { document.documentElement.dataset.theme = theme; document.documentElement.classList.toggle('dark', theme === 'dark') }", theme)
        page.wait_for_timeout(400)
        close = dialog.get_by_role('button', name='关闭', exact=True).bounding_box()
        assert close and 0 <= close['y'] and close['y'] + close['height'] <= 760, close
        assert dialog.evaluate('(node) => node.scrollWidth <= node.clientWidth'), 'Dialog horizontal overflow'
        page.screenshot(path=str(report_dir / f'origins-{theme}.png'))
    dialog.get_by_role('button', name='查看来源任务', exact=True).click()
    expect(dialog.locator('.origin-task')).to_contain_text(parent['id'])
    expect(dialog.get_by_role('button', name='返回上一任务', exact=True)).to_be_visible()
    dialog.get_by_role('button', name='返回上一任务', exact=True).click()
    expect(dialog.locator('.origin-task')).to_contain_text(child['id'])
    dialog.get_by_role('button', name='查看来源任务', exact=True).click()
    dialog.get_by_role('button', name='检查结果 / 继续处理', exact=False).click()
    result = page.get_by_role('dialog', name='处理结果', exact=True)
    result.locator('.handoff-options .el-select__wrapper').click()
    page.get_by_role('option').filter(has_text=re.compile(r'^压缩图片 · 1 个文件')).click()
    result.get_by_role('button', name='交给下一工具', exact=True).click()
    expect(dialog).to_be_hidden()
    page.get_by_role('button', name='使用上一步结果：1 个文件', exact=True).click()
    compressed = after_click('image_batch_compress', page.locator('.panel:visible').get_by_role('button', name='开始压缩', exact=True))
    assert_origin(compressed, parent)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.evaluate("document.documentElement.dataset.theme = 'light'; document.documentElement.classList.remove('dark')")

    excel_parent = seed('excel_process', {'filePath': str(workbook), 'exportCombined': True, 'outputDir': str(fixtures / 'excel-output')})
    send(excel_parent, 'Excel 数据质检')
    panel = page.locator('.panel:visible')
    header = page.locator('.active-tool-view .el-form-item').filter(has_text='表头所在行').locator('input')
    header.fill('1')
    header.press('Tab')
    before = {task['id'] for task in tasks()}
    panel.get_by_role('button', name='选择 / 接收 Excel', exact=True).click()
    expect(panel.get_by_role('button', name='开始质检', exact=True)).to_be_enabled()
    assert {task['id'] for task in tasks()} == before
    panel.get_by_role('button', name='开始质检', exact=True).click()
    expect(panel.get_by_role('button', name='导出质量报告', exact=True)).to_be_visible()
    assert {task['id'] for task in tasks()} == before, 'Quality preview unexpectedly queued a task'
    report = after_click('excel_quality_report', panel.get_by_role('button', name='导出质量报告', exact=True))
    assert_origin(report, excel_parent)
    chosen[:] = [Path(excel_parent['outputs'][0]['path'])]
    panel.get_by_role('button', name='选择 / 接收 Excel', exact=True).click()
    expect(panel.get_by_role('button', name='开始质检', exact=True)).to_be_enabled()
    panel.get_by_role('button', name='开始质检', exact=True).click()
    expect(panel.get_by_role('button', name='导出质量报告', exact=True)).to_be_visible()
    local = after_click('excel_quality_report', panel.get_by_role('button', name='导出质量报告', exact=True))
    assert not local.get('inputOrigins'), 'Same-path native reselection retained stale lineage'

    doc_parent = seed('file_batch_copy', {'sourceDir': str(note_dir), 'targetDir': str(fixtures / 'document-output')})
    send(doc_parent, '建立文档索引')
    view = page.locator('.active-tool-view')
    view.get_by_role('button', name='添加文件', exact=True).click()
    indexed = after_click('document_index_build', view.get_by_role('button', name='更新索引', exact=True))
    assert_origin(indexed, doc_parent)
    assert api.document_index_search({'query': 'searchable'})['results']
    view.locator('.file-list').get_by_role('button', name='移除', exact=True).click()
    chosen[:] = [Path(doc_parent['outputs'][0]['path'])]
    view.get_by_role('button', name='添加文件', exact=True).click()
    reindexed = after_click('document_index_build', view.get_by_role('button', name='更新索引', exact=True))
    assert not reindexed.get('inputOrigins'), reindexed

    send(parent, '添加图片水印')
    panel = page.locator('.panel:visible')
    panel.get_by_text('图片', exact=True).click()
    chosen[:] = [image]
    before_picker = len(picker_calls)
    panel.locator('.el-form-item').filter(has_text='水印图片').get_by_role('button', name='选择', exact=True).click()
    assert len(picker_calls) == before_picker + 1
    expect(page.locator('.incoming-notice')).to_be_visible()
    page.get_by_role('button', name='使用上一步结果：1 个文件', exact=True).click()
    watermarked = after_click('image_add_watermark', panel.get_by_role('button', name='开始处理', exact=True))
    assert_origin(watermarked, parent)
    assert watermarked['args'][0]['watermarkImage'] == str(image)

    removed = api.task_clear({'ids': [parent['id']], 'statuses': ['success']})
    assert removed['code'] == 0, removed
    card_for(child).locator('.task-origins-button').click()
    dialog = page.get_by_role('dialog', name='输入来源', exact=True)
    expect(dialog.get_by_text('来源记录已清理，文件使用关系仍保留', exact=True)).to_be_visible()
    expect(dialog.get_by_role('button', name='查看来源任务', exact=True)).to_be_disabled()
    page.set_viewport_size({'width': 980, 'height': 760})
    expect(page.locator('.el-message:visible')).to_have_count(0)
    page.wait_for_timeout(400)
    page.screenshot(path=str(report_dir / 'origins-missing.png'))
    dialog.get_by_role('button', name='关闭', exact=True).click()
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.get_by_placeholder('搜索任务、输出路径或错误信息', exact=True).fill('')
    result = {'passed': True, 'chains': ['image compression → rotation', 'image parent dialog → compression', 'Excel → profile → quality report', 'file copy → document index'], 'checks': ['receive and preview never execute', 'precise parent and path', 'business args exclude lineage', 'same-path native replacement clears lineage', 'auxiliary watermark picker does not consume or supply main origin', 'workspace drafts exclude origin metadata', 'remove then local selection clears lineage', 'filtered parent lookup and back', 'parent handoff closes origins dialog', 'removed parent keeps relation', '980×760 light/dark no overflow'], 'taskIds': [child['id'], compressed['id'], report['id'], indexed['id']]}
    (report_dir / 'origins.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
