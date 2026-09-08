"""Real search → reviewed handoff and search → relative-path archive flows."""
import json
import zipfile

from playwright.sync_api import expect


def verify_search_archive(api, page, root, report_dir):
    source = root / 'search-fixtures'
    output = source / 'delivery'
    for name, content in [('alpha/Report[1].txt', 'alpha'), ('beta/Report[1].txt', 'beta'), ('Report1.txt', 'other')]:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    navigation = page.get_by_role('navigation', name='工具', exact=True)
    navigation.get_by_role('button', name='文件批处理', exact=True).click()
    page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='文件搜索', exact=True).click()
    panel = page.locator('.search-panel')
    page.evaluate('path => { window.__searchOriginalPicker = window.pywebview.api.system_pySelectDirDialog; window.pywebview.api.system_pySelectDirDialog = async () => path }', str(source))
    try:
        panel.get_by_role('button', name='选择目录', exact=True).click()
        keyword = panel.locator('.el-form-item').filter(has_text='文件名包含').locator('input')
        extensions = panel.locator('.el-form-item').filter(has_text='扩展名').locator('input')
        keyword.fill('[1]')
        extensions.fill('TXT')
        before = {task['id'] for task in api.task_list()['tasks']}
        run_search = panel.get_by_role('button', name='开始搜索', exact=True)
        run_search.click()
        expect(panel.locator('.search-summary')).to_contain_text('搜索完整 · 已找到 2 个文件')
        expect(panel.locator('.el-table__body tr')).to_have_count(2)
        assert {task['id'] for task in api.task_list()['tasks']} == before
        panel.locator('.el-checkbox').filter(has_text='包含子目录').click()
        expect(panel.get_by_role('checkbox', name='包含子目录', exact=True)).not_to_be_checked()
        expect(panel.locator('.search-summary')).to_have_count(0)
        run_search.click()
        expect(panel.get_by_text('未找到匹配文件，可调整关键词或扩展名', exact=True)).to_be_visible()
        panel.locator('.el-checkbox').filter(has_text='包含子目录').click()
        expect(panel.get_by_role('checkbox', name='包含子目录', exact=True)).to_be_checked()
        run_search.click()
        expect(panel.locator('.search-summary')).to_contain_text('已找到 2 个文件')
        page.set_viewport_size({'width': 980, 'height': 760})
        panel.locator('.result-table').evaluate("node => node.scrollIntoView({block: 'center'})")
        for theme in ('light', 'dark'):
            page.evaluate("theme => { document.documentElement.dataset.theme = theme; document.documentElement.classList.toggle('dark', theme === 'dark') }", theme)
            page.wait_for_timeout(200)
            assert panel.evaluate('(node) => node.scrollWidth <= node.clientWidth')
            page.screenshot(path=str(report_dir / f'search-results-{theme}.png'))
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.evaluate("document.documentElement.dataset.theme = 'light'; document.documentElement.classList.remove('dark')")

        # Review and receive a search result without silently starting a job.
        page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='压缩 / 解压', exact=True).click()
        archive = page.locator('.archive-card').first
        while archive.get_by_role('button', name='移除', exact=True).count():
            archive.get_by_role('button', name='移除', exact=True).first.click()
        page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='文件搜索', exact=True).click()
        panel.get_by_role('button', name='检查结果 / 继续处理（2）', exact=True).click()
        dialog = page.get_by_role('dialog', name='处理结果', exact=True)
        dialog.locator('.route-select').click()
        page.get_by_role('option', name='打包归档 · 2 个文件', exact=False).click()
        dialog.get_by_role('button', name='交给下一工具', exact=True).click()
        archive.get_by_role('button', name='添加文件', exact=True).click()
        expect(archive.locator('.el-table__body tr')).to_have_count(2)
        assert {task['id'] for task in api.task_list()['tasks']} == before
        archive.get_by_role('button', name='选择根目录', exact=True).click()
        expect(archive.locator('.el-form-item').filter(has_text='保留目录结构').locator('input')).to_have_value(str(source))
        manual_output = root / 'manual-search-archive'
        page.evaluate('path => { window.pywebview.api.system_pySelectDirDialog = async () => path }', str(manual_output))
        archive.locator('.el-form-item').filter(has_text='输出目录').get_by_role('button', name='目录', exact=True).click()
        archive.locator('.el-radio-button').filter(has_text='7Z').click()
        archive.locator('.el-form-item').filter(has_text='密码').locator('input').fill('test-only-unused-secret')
        archive.locator('.el-radio-button').filter(has_text='ZIP').click()
        archive.get_by_role('button', name='开始压缩', exact=True).click()
        completed_task = None
        for _ in range(400):
            completed_task = next((task for task in api.task_list()['tasks'] if task['id'] not in before and task['method'] == 'file_compress'), None)
            if completed_task and completed_task['status'] not in ('running', 'queued', 'canceling'):
                break
            page.wait_for_timeout(100)
        assert completed_task and completed_task['status'] == 'success', completed_task
        expect(archive.get_by_role('button', name='开始压缩', exact=True)).to_be_enabled()
        with zipfile.ZipFile(completed_task['result']['file']) as package:
            assert set(package.namelist()) == {'alpha/Report[1].txt', 'beta/Report[1].txt'}
            assert all(not item.flag_bits & 1 for item in package.infolist())

        # The reusable template uses the same real sources and retains both names.
        navigation.get_by_role('button', name='自动化工作流', exact=True).click()
        page.get_by_role('tab', name='工作流', exact=True).click()
        page.locator('.template-card').filter(has_text='搜索文档 → 保留目录归档').get_by_role('button', name='使用模板', exact=True).click()
        editor = page.locator('.workflow-editor')
        run = editor.get_by_role('button', name='立即运行', exact=True)
        expect(run).to_be_enabled()
        inputs = editor.locator('.run-setup')
        inputs.locator('[data-field-name="directory"] input').fill(str(source))
        inputs.locator('[data-field-name="outputDir"] input').fill(str(output))
        inputs.locator('[data-field-name="keyword"] input').fill('[1]')
        inputs.locator('[data-field-name="extensions"] textarea').fill('txt')
        inputs.locator('[data-field-name="archiveName"] input').fill('browser-documents')
        workflow = next(item for item in api.workflow_list()['workflows'] if item['name'].startswith('搜索文档'))

        def wait_run(expected, previous=None):
            result = None
            for _ in range(400):
                result = next((item for item in api.workflow_list()['runs'] if item['workflowId'] == workflow['id'] and item['id'] != previous), None)
                if result and result['status'] != 'running':
                    break
                page.wait_for_timeout(100)
            assert result and result['status'] == expected, result
            expect(page.get_by_role('tab', name='运行记录', exact=True)).to_have_attribute('aria-selected', 'true')
            return result

        run.click()
        complete = wait_run('success')
        with zipfile.ZipFile(complete['steps'][1]['result']['file']) as package:
            assert set(package.namelist()) == {'alpha/Report[1].txt', 'beta/Report[1].txt'}
            assert package.read('alpha/Report[1].txt') == b'alpha'
            assert package.read('beta/Report[1].txt') == b'beta'

        # The explicit cap is enforced and cannot silently produce a partial ZIP.
        for index in range(51):
            (source / f'many-{index}.txt').write_text(str(index), encoding='utf-8')
        page.get_by_role('tab', name='工作流', exact=True).click()
        inputs.locator('[data-field-name="keyword"] input').fill('many-')
        limit = inputs.locator('[data-field-name="limit"] input')
        limit.fill('50')
        limit.press('Tab')
        existing_archives = set(output.iterdir())
        run.click()
        partial = wait_run('partial', complete['id'])
        assert len(partial['steps']) == 1
        assert partial['steps'][0]['result']['matchedCount'] == 50
        assert partial['steps'][0]['result']['truncated'] is True
        assert set(output.iterdir()) == existing_archives
        record = page.locator('.run-list .el-collapse-item').filter(has_text=workflow['name']).first
        record.locator('.el-collapse-item__header').click()
        expect(record).to_contain_text('超过 50 条结果上限')
        page.set_viewport_size({'width': 980, 'height': 760})
        record.scroll_into_view_if_needed()
        expect(page.locator('.el-message')).to_have_count(0)
        page.screenshot(path=str(report_dir / 'search-archive-stopped.png'))
        page.set_viewport_size({'width': 1440, 'height': 1000})

        # The standalone search also explains its cap and clears stale results.
        navigation.get_by_role('button', name='文件批处理', exact=True).click()
        page.get_by_role('navigation', name='子功能', exact=True).get_by_role('button', name='文件搜索', exact=True).click()
        keyword.fill('many-')
        standalone_limit = panel.locator('.el-form-item').filter(has_text='最多结果').locator('input')
        standalone_limit.fill('50')
        standalone_limit.press('Tab')
        run_search.click()
        expect(panel.locator('.search-summary')).to_contain_text('结果不完整 · 已找到 50 个文件')
        expect(panel.locator('.el-alert')).to_contain_text('超过 50 条结果上限')
        keyword.fill('missing-')
        expect(panel.locator('.search-summary')).to_have_count(0)
        run_search.click()
        expect(panel.get_by_text('未找到匹配文件，可调整关键词或扩展名', exact=True)).to_be_visible()
        result = {'passed': True, 'checks': [
            'literal keyword and case-insensitive extension with real files', 'nonrecursive empty result',
            'search and reviewed file handoff never auto-execute', 'manual archive retains layout and ignores hidden 7Z password in ZIP mode',
            'real search template ZIP preserves both same-named files and bytes',
            '51 matches with limit 50 stop before archive', 'standalone truncation warning and stale result clearing',
            '980x760 light/dark search results and workflow stop evidence']}
        (report_dir / 'search-archive.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    finally:
        page.evaluate('window.pywebview.api.system_pySelectDirDialog = window.__searchOriginalPicker')
