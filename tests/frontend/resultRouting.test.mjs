import assert from 'node:assert/strict'
import test from 'node:test'
import { RESULT_ROUTES, getResultRoutes, planResultHandoff } from '../../gui/src/utils/resultRouting.mjs'

const asset = (path, extra = {}) => ({ path, ...extra })

test('mixed assets report accepted and skipped counts without mutating input', () => {
  const input = [asset('C:\\out\\one.pdf'), asset('C:\\out\\two.pdf'), asset('C:\\out\\note.txt'), asset('C:\\out\\gone.pdf', { exists: false }), asset('C:\\out\\folder', { kind: 'directory' })]
  const snapshot = structuredClone(input)
  const plan = planResultHandoff(input, 'pdf/merge')
  assert.equal(plan.acceptedCount, 2)
  assert.equal(plan.skippedCount, 3)
  assert.deepEqual(input, snapshot)
})

test('Windows path duplicates collapse while Linux paths retain case', () => {
  const windows = planResultHandoff([asset('C:\\A\\One.PDF'), asset('c:/a/one.pdf')], 'pdf/compress')
  assert.equal(windows.acceptedCount, 1)
  assert.equal(windows.skipped[0].reason, '与已选结果路径重复')
  const linux = planResultHandoff([asset('/tmp/One.pdf'), asset('/tmp/one.pdf')], 'pdf/merge')
  assert.equal(linux.acceptedCount, 2)
})

test('invalid route and invalid-only input have explicit outcomes', () => {
  const invalidRoute = planResultHandoff([asset('/tmp/a.pdf')], 'missing/action')
  assert.equal(invalidRoute.route, null)
  assert.equal(invalidRoute.skipped[0].reason, '未找到可用的接力操作')
  assert.deepEqual(getResultRoutes([asset('/tmp/a', { kind: 'directory' }), asset('', { exists: false })]), [])
})

test('unknown formats only suggest the universal archive receiver', () => {
  const routes = getResultRoutes([asset('/tmp/render.unknown')])
  assert.deepEqual(routes.map((plan) => plan.route.id), ['file/archive'])
})

test('path extension wins over same-name metadata and supports doc/docx contracts', () => {
  const planned = planResultHandoff([asset('/tmp/a.doc', { name: 'pretend.docx' }), asset('/tmp/b.docx')], 'word/merge')
  assert.equal(planned.acceptedCount, 1)
  assert.equal(planned.assets[0].path, '/tmp/b.docx')
  assert.ok(planResultHandoff([asset('/tmp/a.doc'), asset('/tmp/b.docx')], 'conversion/universal').acceptedCount === 2)
})

test('same named files at different paths are preserved and multi-file routes never drop files', () => {
  const files = [asset('/a/report.pdf', { name: 'report.pdf' }), asset('/b/report.pdf', { name: 'report.pdf' })]
  const plan = planResultHandoff(files, 'pdf/merge')
  assert.equal(plan.acceptedCount, 2)
  assert.equal(plan.skippedCount, 0)
  assert.ok(getResultRoutes(files).some((item) => item.route.id === 'pdf/merge' && item.acceptedCount === 2))
})

test('route ids are unique and results remain stably ordered', () => {
  assert.equal(new Set(RESULT_ROUTES.map((route) => route.id)).size, RESULT_ROUTES.length)
  const input = [asset('/tmp/a.pdf'), asset('/tmp/b.pdf')]
  assert.deepEqual(getResultRoutes(input).map((item) => item.route.id), getResultRoutes(input).map((item) => item.route.id))
})

test('single-file receivers reject multiple files rather than consuming the first', () => {
  for (const [route, extension] of [['pdf/compress', 'pdf'], ['pdf/ocr', 'pdf'], ['video/compress', 'mp4'], ['video/cut', 'mp4']]) {
    const input = [asset('/tmp/a.' + extension), asset('/tmp/b.' + extension)]
    assert.equal(planResultHandoff(input, route).acceptedCount, 0)
    assert.ok(!getResultRoutes(input).some((item) => item.route.id === route))
    assert.ok(getResultRoutes(input.slice(0, 1)).some((item) => item.route.id === route))
  }
})

test('merge receivers require multiple compatible files in suggestions', () => {
  assert.ok(!getResultRoutes([asset('/tmp/a.pdf')]).some((item) => item.route.id.endsWith('/merge') || item.route.id.endsWith('/merge-pdf')))
  assert.ok(getResultRoutes([asset('/tmp/a.docx'), asset('/tmp/b.docx')]).some((item) => item.route.id === 'word/merge'))
})

test('image-to-PDF matches its converter instead of general image support', () => {
  assert.equal(planResultHandoff([asset('/tmp/a.heic'), asset('/tmp/b.cr3')], 'conversion/images-pdf').acceptedCount, 2)
  assert.equal(planResultHandoff([asset('/tmp/a.jp2')], 'conversion/images-pdf').acceptedCount, 0)
  assert.equal(planResultHandoff([asset('/tmp/a.jp2')], 'image/compress').acceptedCount, 1)
})

test('invalid asset shapes and extensionless files do not crash suggestions', () => {
  assert.deepEqual(getResultRoutes([null, false, 3, {}, asset(42), asset('  ')]), [])
  assert.deepEqual(getResultRoutes([asset('/tmp/README')]).map((item) => item.route.id), ['file/archive'])
})
