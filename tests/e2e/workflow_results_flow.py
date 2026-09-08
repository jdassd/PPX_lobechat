"""Declared result selection and real text/data workflows through the browser."""
import json

from playwright.sync_api import expect


def verify_workflow_results(api, page, report_dir):
    navigation = page.get_by_role('navigation', name='工具', exact=True)
    navigation.get_by_role('button', name='自动化工作流', exact=True).click()
    page.get_by_role('tab', name='工作流', exact=True).click()
    page.locator('.template-card').filter(has_text='文本去重 → 统一格式').get_by_role('button', name='使用模板', exact=True).click()
    editor = page.locator('.workflow-editor')
    run = editor.get_by_role('button', name='立即运行', exact=True)
    expect(run).to_be_enabled()
    run_setup = editor.locator('.run-setup')
    run_setup.locator('[data-field-name="content"] textarea').fill(' apple \npear\napple\n\n')
    run_setup.locator('[data-field-name="mode"] .el-select__wrapper').click()
    page.get_by_role('option', name='全部大写', exact=True).click()
    second = editor.locator('[data-step-index="1"]')
    field = second.locator('[data-field-name="content"]')
    field.locator('.reference .el-select__wrapper').click()
    expect(page.get_by_role('option', name='逐行清理文本 · 处理结果', exact=True)).to_be_visible()
    expect(page.get_by_role('option').filter(has_text='结果文件列表')).to_have_count(0)
    page.get_by_role('option', name='逐行清理文本 · 处理结果', exact=True).click()
    expect(field.locator('input').first).to_have_value('{{steps.clean.result}}')
    workflow = next(item for item in api.workflow_list()['workflows'] if item['name'].startswith('文本去重'))

    def wait_run(workflow_id):
        result = None
        for _ in range(400):
            result = next((item for item in api.workflow_list()['runs'] if item['workflowId'] == workflow_id), None)
            if result and result['status'] != 'running':
                break
            page.wait_for_timeout(100)
        assert result and result['status'] == 'success', result
        expect(page.get_by_role('tab', name='运行记录', exact=True)).to_have_attribute('aria-selected', 'true')
        return result

    page.set_viewport_size({'width': 980, 'height': 760})
    field.evaluate("node => node.scrollIntoView({block: 'center'})")
    expect(page.locator('.el-message')).to_have_count(0)
    field.locator('.reference .el-select__wrapper').click()
    expect(page.get_by_role('option', name='逐行清理文本 · 处理结果', exact=True)).to_be_visible()
    page.screenshot(path=str(report_dir / 'result-fields.png'))
    page.keyboard.press('Escape')
    page.set_viewport_size({'width': 1440, 'height': 1000})
    run.click()
    text_run = wait_run(workflow['id'])
    assert text_run['steps'][1]['result']['result'] == 'APPLE\nPEAR'
    record = page.locator('.run-list .el-collapse-item').filter(has_text=workflow['name']).first
    record.locator('.el-collapse-item__header').click()
    data = record.locator('.workflow-data-result')
    expect(data).to_have_count(2)
    expect(data.locator('pre')).to_have_count(0)  # Large values stay unrendered until opened.
    data.nth(0).locator('summary').click()
    data.nth(1).locator('summary').click()
    expect(data.nth(0).locator('pre')).to_have_text('apple\npear')
    expect(data.nth(1).locator('pre')).to_have_text('APPLE\nPEAR')

    # A browser-local clipboard stub verifies the full payload without overwriting
    # the developer's system clipboard. Native clipboard availability is separate.
    page.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async text => { window.__copiedResult = text }}})")
    try:
        data.nth(1).get_by_role('button', name='复制完整结果', exact=True).click()
        page.wait_for_function("window.__copiedResult === 'APPLE\\nPEAR'")
        expect(page.locator('.el-message')).to_have_count(0)
        page.set_viewport_size({'width': 980, 'height': 760})
        for theme in ('light', 'dark'):
            page.evaluate("theme => { document.documentElement.dataset.theme = theme; document.documentElement.classList.toggle('dark', theme === 'dark') }", theme)
            data.nth(1).scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            assert data.nth(1).evaluate('(node) => node.scrollWidth <= node.clientWidth')
            page.screenshot(path=str(report_dir / f'data-results-{theme}.png'))
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.evaluate("document.documentElement.dataset.theme = 'light'; document.documentElement.classList.remove('dark')")

        # Real zero, false, empty and long results are all distinguishable. The
        # invalid JSON rule edit must block execution instead of using old rules.
        long_text = 'word ' * 4000
        original_rules = [{'search': 'absent', 'replace': ''}]
        fixture = api.workflow_save({'name': '数据类型验证', 'steps': [
            {'id': 'zero', 'name': '零次替换', 'method': 'text_batch_replace', 'args': {'content': 'hello', 'rules': original_rules}},
            {'id': 'flag', 'name': '查询布尔值', 'method': 'text_format_json', 'args': {'content': '{"flag":false}', 'operation': 'query', 'path': 'flag'}},
            {'id': 'empty', 'name': '空文本', 'method': 'text_case_transform', 'args': {'content': '', 'mode': 'upper'}},
            {'id': 'long', 'name': '长文本', 'method': 'text_case_transform', 'args': {'content': long_text, 'mode': 'upper'}},
        ]})['workflow']
        page.locator('.workflow-tool').get_by_role('button', name='刷新', exact=True).click()
        expect(page.locator('.workflow-tool > .el-loading-mask:visible')).to_have_count(0)
        page.get_by_role('tab', name='工作流', exact=True).click()
        page.locator('.workflow-list-item').filter(has_text=fixture['name']).click()
        rules = editor.locator('[data-step-index="0"] [data-field-name="rules"] textarea')
        rules.fill('{invalid')
        rules.press('Tab')
        expect(editor.locator('[data-step-index="0"] .field-error')).to_contain_text('JSON 列表')
        before = {item['id'] for item in api.task_list()['tasks']}
        run.click()
        expect(editor.get_by_test_id('preflight-report')).to_contain_text('替换规则必须是对象或列表')
        expect(run).to_be_enabled()
        assert {item['id'] for item in api.task_list()['tasks']} == before
        assert not any(item['workflowId'] == fixture['id'] for item in api.workflow_list()['runs'])
        rules.fill('')
        rules.press_sequentially(json.dumps(original_rules))
        expect(rules).to_have_value(json.dumps(original_rules))
        rules.press('Tab')
        expect(editor.locator('[data-step-index="0"] .field-error')).to_have_count(0)
        query_path = editor.locator('[data-step-index="1"] [data-field-name="path"]')
        expect(query_path.locator('input').first).to_have_value('flag')
        expect(query_path.get_by_role('button', name='选择', exact=True)).to_have_count(0)
        run.click()
        typed_run = wait_run(fixture['id'])
        record = page.locator('.run-list .el-collapse-item').filter(has_text=fixture['name']).first
        record.locator('.el-collapse-item__header').click()
        panels = record.locator('.workflow-data-result')
        expect(panels).to_have_count(4)
        for panel in panels.all():
            panel.locator('summary').click()
        panels.nth(0).locator('.el-select__wrapper').click()
        page.get_by_role('option', name='替换次数', exact=True).click()
        expect(panels.nth(0).locator('pre')).to_have_text('0')
        expect(panels.nth(1).locator('pre')).to_have_text('false')
        expect(panels.nth(2).locator('pre')).to_have_text('（空字符串）')
        expect(panels.nth(3).get_by_text('仅预览前 12000 个字符，复制可获得完整结果。', exact=True)).to_be_visible()
        assert len(panels.nth(3).locator('pre').text_content()) == 12000
        for index, expected in [(0, '0'), (1, 'false'), (2, ''), (3, long_text.upper())]:
            page.evaluate('window.__copiedResult = null')
            panels.nth(index).get_by_role('button', name='复制完整结果', exact=True).click()
            page.wait_for_function('(expected) => window.__copiedResult === expected', arg=expected)
        assert typed_run['steps'][1]['result']['result'] is False
        page.evaluate("() => { navigator.clipboard.writeText = async () => { throw new Error('unavailable') } }")
        panels.nth(0).get_by_role('button', name='复制完整结果', exact=True).click()
        expect(page.get_by_text('复制失败，可选中下方结果手动复制', exact=True)).to_be_visible()
        result = {'passed': True, 'checks': [
            'typed result field picker writes real result binding', 'incompatible file results absent for text',
            'real text cleaning and format template', 'data previews render only after opening',
            'zero false empty and long data remain distinct', 'preview is limited while copy uses full value',
            'clipboard payload and failure feedback checked with browser-local stub', 'invalid JSON rules block queue instead of running old rules',
            'JSON query path uses text input', '980x760 result picker and light/dark data views']}
        (report_dir / 'workflow-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    finally:
        page.evaluate('delete navigator.clipboard')
