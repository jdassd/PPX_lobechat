"""Read-only draft checks, recovery presentation and real manual execution."""
import json
import zipfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect


def verify_workflow_preflight(api, page, root, chosen, report_dir):
    fixtures = root / 'preflight-fixtures'
    fixtures.mkdir()
    sources = [fixtures / 'first.png', fixtures / 'second.png']
    for index, path in enumerate(sources):
        Image.new('RGB', (32, 24), ('navy', 'green')[index]).save(path)
    output = fixtures / 'outputs'
    workflow = api.workflow_create_from_template({'templateId': 'builtin-image-archive'})['workflow']
    workflow.update(name='执行前检查示例', inputExample={'files': [], 'outputDir': str(output), 'archiveName': 'checked'})
    workflow = api.workflow_save(workflow)['workflow']
    alternate = api.workflow_save({**workflow, 'id': 'preflight-alternate', 'name': '切换配置示例'})['workflow']
    navigation = page.get_by_role('navigation', name='工具', exact=True)
    navigation.get_by_role('button', name='自动化工作流', exact=True).click()
    page.get_by_role('tab', name='运行记录', exact=True).click()
    page.locator('.workflow-tool').get_by_role('button', name='刷新', exact=True).click()
    expect(page.locator('.workflow-tool > .el-loading-mask')).not_to_be_visible()
    page.get_by_role('tab', name='工作流', exact=True).click()
    page.locator('.workflow-list-item').filter(has_text=workflow['name']).click()
    editor = page.locator('.workflow-editor')
    run_setup = editor.locator('.run-setup')
    report = editor.get_by_test_id('preflight-report')
    check = editor.get_by_role('button', name='检查配置', exact=True)
    run = editor.get_by_role('button', name='立即运行', exact=True)

    def saved():
        return next(item for item in api.workflow_list()['workflows'] if item['id'] == workflow['id'])

    before = saved()
    before_tasks = {item['id'] for item in api.task_list()['tasks']}
    before_runs = len(api.workflow_list()['runs'])
    check.click()
    expect(report).to_contain_text('不能为空')
    expect(run).to_be_enabled()
    assert saved() == before
    assert not output.exists()
    run.click()
    expect(report).to_contain_text('不能为空')
    expect(run).to_be_enabled()
    assert saved() == before
    assert len(api.workflow_list()['runs']) == before_runs
    assert {item['id'] for item in api.task_list()['tasks']} == before_tasks
    report.get_by_role('button', name='定位', exact=True).first.click()
    expect(run_setup.locator('[data-field-name="files"] textarea')).to_be_focused()

    chosen[:] = sources
    run_setup.locator('[data-field-name="files"]').get_by_role('button', name='选择', exact=True).click()
    expect(run_setup.locator('[data-field-name="files"] .item-count')).to_have_text('2 项')
    expect(report).to_have_count(0)
    archive = editor.locator('[data-step-index="1"]')
    archive.locator('.form-mode .el-switch').click()
    archive.locator('textarea:visible').fill(json.dumps({**workflow['steps'][1]['args'], 'items': '{{steps.archive.outputPaths}}'}))
    check.click()
    expect(report).to_contain_text('只能引用前序步骤')
    expect(run).to_be_enabled()
    assert saved() == before
    archive.locator('textarea:visible').fill(json.dumps(workflow['steps'][1]['args']))
    check.click()
    expect(report).to_contain_text('配置检查通过')
    expect(report).to_contain_text('1 处前序步骤输出将在执行后核对')
    expect(run).to_be_enabled()
    assert saved() == before and not output.exists()

    # A response that arrives after an already queued input event must not describe
    # the new draft. This uses DOM events, without accessing Vue internals.
    page.evaluate("""() => {
      window.__realPreflight = window.pywebview.api.workflow_preflight;
      window.pywebview.api.workflow_preflight = () => new Promise(resolve => {
        window.__finishPreflight = () => resolve({code: 0, valid: true, errors: [], deferred: [], steps: []});
      });
    }""")
    try:
        check.click()
        expect(run).to_be_disabled()
        editor.locator('.two-columns .el-input__inner').first.evaluate("node => { node.value = 'changed-during-check'; node.dispatchEvent(new Event('input', {bubbles: true})) }")
        page.evaluate('window.__finishPreflight()')
        expect(run).to_be_enabled()
        expect(report).to_have_count(0)
        page.evaluate("window.pywebview.api.workflow_preflight = async () => ({code: -1, msg: '检查服务暂不可用'})")
        run.click()
        expect(report).to_contain_text('检查服务暂不可用')
        expect(run).to_be_enabled()
        assert {item['id'] for item in api.task_list()['tasks']} == before_tasks
    finally:
        page.evaluate('window.pywebview.api.workflow_preflight = window.__realPreflight')

    # Null JSON is invalid configuration, not a rendering exception. Loading a
    # second workflow with identical step keys clears the old form error.
    archive.locator('textarea:visible').fill('null')
    expect(archive.get_by_text('参数必须是对象', exact=True)).to_be_visible()
    check.click()
    expect(report).to_contain_text('步骤 2 参数必须是 JSON 对象')
    expect(run).to_be_enabled()
    page.locator('.workflow-list-item').filter(has_text=alternate['name']).click()
    expect(editor.locator('.step-card .el-alert')).to_have_count(0)
    page.locator('.workflow-list-item').filter(has_text=workflow['name']).click()
    run_setup.locator('[data-field-name="files"]').get_by_role('button', name='选择', exact=True).click()
    check.click()
    expect(report).to_contain_text('配置检查通过')
    expect(run).to_be_enabled()

    page.set_viewport_size({'width': 980, 'height': 760})
    for theme in ('light', 'dark'):
        page.evaluate("theme => { document.documentElement.dataset.theme = theme; document.documentElement.classList.toggle('dark', theme === 'dark') }", theme)
        report.scroll_into_view_if_needed()
        page.wait_for_timeout(250)
        assert editor.evaluate('(node) => node.scrollWidth <= node.clientWidth')
        bounds = check.bounding_box()
        assert bounds and 0 <= bounds['y'] < 760
        page.screenshot(path=str(report_dir / f'preflight-{theme}.png'))
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.evaluate("document.documentElement.dataset.theme = 'light'; document.documentElement.classList.remove('dark')")
    run.click()
    expect(page.get_by_text('工作流执行完成', exact=True)).to_be_visible(timeout=60000)
    actual = next(item for item in api.workflow_list()['runs'] if item['workflowId'] == workflow['id'])
    assert actual['status'] == 'success', actual
    with zipfile.ZipFile(actual['steps'][1]['result']['file']) as package:
        assert len(package.namelist()) == 2
    assert all(path.is_file() for path in sources)

    # A new draft can now check, save and execute directly from the form.
    page.get_by_role('tab', name='工作流', exact=True).click()
    page.locator('.workflow-list').get_by_role('button', name='新建', exact=True).click()
    editor.locator('.two-columns .el-input__inner').first.fill('新建直接运行')
    first_step = editor.locator('.step-card').first
    first_step.locator('.step-row .el-select').first.click()
    label = next(item['label'] for item in api.operations_list()['operations'] if item['id'] == 'text_case_transform')
    page.get_by_role('option', name=label, exact=True).click()
    first_step.locator('.form-mode .el-switch').click()
    first_step.locator('textarea:visible').fill(json.dumps({'content': 'new draft', 'mode': 'upper'}))
    run.click()
    latest = None
    for _ in range(300):
        latest = next((item for item in api.workflow_list()['runs'] if item['workflowName'] == '新建直接运行'), None)
        if latest and latest['status'] != 'running':
            break
        page.wait_for_timeout(100)
    assert latest is not None, 'New workflow did not create a run'
    assert latest['status'] == 'success', latest
    assert latest['steps'][0]['result']['result'] == 'NEW DRAFT'
    # The task can finish before the browser receives its completion snapshot.
    # Finish this user flow before the next scenario switches back to editing.
    expect(page.get_by_role('tab', name='运行记录', exact=True)).to_have_attribute('aria-selected', 'true')
    expect(page.locator('.workflow-tool > .el-loading-mask')).not_to_be_visible()
    result = {'passed': True, 'checks': [
        'read-only checks never save or queue', 'invalid input and self-reference block run',
        'error location focuses runtime input', 'known inputs and deferred prior output',
        'stale response discarded after queued input event', 'API errors never queue',
        'null JSON does not crash and switching clears stale form error',
        'file counts and 980x760 light/dark layout', 'real two-file ZIP after successful check',
        'new workflow checks saves and runs in one action']}
    (report_dir / 'preflight.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
