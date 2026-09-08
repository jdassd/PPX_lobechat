import test from 'node:test'
import assert from 'node:assert/strict'
import { getInputOrigins } from '../../gui/src/utils/inputOrigins.mjs'

const received = (path, task = 'source-task') => ({ path, origin: { sourceTaskId: task, sourceAssetPath: path } })

test('only explicitly selected file objects carry origins; plain picker paths stay ordinary', () => {
  const file = received('/tmp/result.xlsx')
  const original = structuredClone(file)
  assert.deepEqual(getInputOrigins([file]), [{ inputPath: file.path, sourceTaskId: 'source-task', sourceAssetPath: file.path }])
  assert.deepEqual(getInputOrigins([{ path: file.path }, file.path]), [])
  assert.deepEqual(getInputOrigins([]), [])
  assert.deepEqual(file, original)
})

test('replacing the selected path discards its old origin and invalid shapes are ignored', () => {
  const file = received('/tmp/old.xlsx')
  file.path = '/tmp/new.xlsx'
  assert.deepEqual(getInputOrigins([file, null, {}, { path: '/tmp/x', origin: { sourceTaskId: [] } }]), [])
  assert.deepEqual(getInputOrigins({}), [])
})

test('multiple sources remain distinct and duplicate Windows path spellings collapse', () => {
  const file = received('C:\\Work\\result.png', 'A')
  const same = { path: 'c:/work/RESULT.png', origin: { ...file.origin } }
  const other = received('/tmp/other.png', 'B')
  assert.deepEqual(getInputOrigins([file, same, other]).map((item) => item.sourceTaskId), ['A', 'B'])
  assert.equal(getInputOrigins([received('/tmp/A.png'), received('/tmp/a.png')]).length, 2)
})

test('snapshot contains only provenance fields and keeps a bounded overflow signal', () => {
  const file = received('/tmp/result.pdf')
  file.origin.password = 'never-send'
  const origins = getInputOrigins([file])
  file.origin.sourceTaskId = 'changed-after-submit'
  assert.equal(origins[0].sourceTaskId, 'source-task')
  assert.deepEqual(Object.keys(origins[0]), ['inputPath', 'sourceTaskId', 'sourceAssetPath'])
  assert.equal(getInputOrigins(Array.from({ length: 1000 }, (_, i) => received('/tmp/' + i))).length, 201)
})
