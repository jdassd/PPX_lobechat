"""Exercise the real collector and queue against intercepted local browser fixtures."""
import time

from api.webauto import WebAutoTool


def verify_web_collection(api, browser_context):
    requests = {'one': 0, 'two': 0}

    def serve(route):
        url = route.request.url
        if url.endswith('/list'):
            route.fulfill(status=200, content_type='text/html', body='''
                <div class="row"><a href="/one">One</a></div>
                <div class="row"><a href="/two">Two</a></div>
            ''')
        elif url.endswith('/login'):
            route.fulfill(status=200, content_type='text/html', body='<form>Please sign in again<input name="username"></form>')
        else:
            name = url.rsplit('/', 1)[-1]
            if name not in requests:
                route.fulfill(status=404, body='')
                return
            requests[name] += 1
            status = 500 if name == 'two' and requests[name] == 1 else 200
            route.fulfill(status=status, content_type='text/html', body=f'<h1>{name} detail</h1>')

    browser_context.route('http://ppx.test/**', serve)
    page = browser_context.new_page()
    page.goto('http://ppx.test/list')
    web = api._services[WebAutoTool]
    web._wa_ensure()
    web._wa_pick.update(active=True, url=page.url, container='.row',
                        fields=[{'id': 'link', 'name': 'link', 'selector': 'a', 'attr': 'href'}],
                        detailFields=[{'id': 'title', 'name': 'title', 'selector': 'h1', 'attr': ''}],
                        detailLinkField='link')

    def service_task(identity):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            with web._wa_lock:
                request = web._wa_collect_req
                web._wa_collect_req = None
            if request:
                # Browser methods run on their creator thread, as in the pick session.
                web._wa_collect_in_session(page, browser_context, request)
            task = api.task_get(identity)['task']
            if task['status'] not in {'queued', 'running', 'canceling'}:
                return task
            page.wait_for_timeout(100)
        raise AssertionError('Collection task did not finish')

    first = api.task_submit({'method': 'webauto_collect', 'args': [{'detail': {'enabled': True, 'linkField': 'link'}}]})
    partial = service_task(first['taskId'])
    assert partial['status'] == 'partial', partial
    assert partial['result']['total'] == 2
    retry = service_task(api.task_retry(partial['id'])['taskId'])
    assert retry['status'] == 'success', retry
    assert retry['result']['total'] == 2, 'Retry duplicated list records'
    assert requests == {'one': 1, 'two': 2}, requests
    assert retry['result']['rows'][1]['title'] == 'two detail'
    assert retry['result']['resultId'] != partial['result']['resultId']
    page.goto('http://ppx.test/login')
    expired = service_task(api.task_submit({'method': 'webauto_collect', 'args': [{}]})['taskId'])
    assert expired['status'] == 'failed' and '登录' in expired['message'], expired
    web._wa_pick['active'] = False
    closed = service_task(api.task_submit({'method': 'webauto_collect', 'args': [{}]})['taskId'])
    assert closed['status'] == 'failed' and '浏览器会话未打开' in closed['message'], closed
    page.close()
    browser_context.unroute('http://ppx.test/**', serve)
    print('PASS: browser collection, partial details, retry only failed requests, no duplicate rows, expired login and closed session feedback')
