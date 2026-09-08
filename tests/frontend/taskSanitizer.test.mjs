import assert from 'node:assert/strict'
import test from 'node:test'
import { sanitizeTaskValue } from '../../gui/src/utils/taskSanitizer.mjs'

test('empty optional secrets keep ordinary task arguments retryable', () => {
  for (const value of ['', null, false, [], {}]) {
    const args = { items: ['C:/in/file.txt'], password: value, format: 'zip' }
    assert.deepEqual(sanitizeTaskValue(args), { value: args, retryable: true })
  }
})

test('present secrets including whitespace and zero never enter history', () => {
  for (const value of ['private', ' ', 0, 123, [''], { token: '' }]) {
    assert.deepEqual(sanitizeTaskValue({ apiKey: value }), { value: { apiKey: '[REDACTED]' }, retryable: false })
  }
})

test('nested empty defaults do not hide another real secret', () => {
  const args = [{ password: '', input: { token: 'private' }, enabled: false }]
  assert.deepEqual(sanitizeTaskValue(args), { value: [{ password: '', input: { token: '[REDACTED]' }, enabled: false }], retryable: false })
  assert.equal(args[0].input.token, 'private')
})

test('size and depth limits still block incomplete retries', () => {
  const long = sanitizeTaskValue('x'.repeat(200001))
  assert.equal(long.retryable, false)
  assert.ok(long.value.endsWith('[TRUNCATED]'))
  let nested = 'plain'
  for (let i = 0; i < 12; i++) nested = { input: nested }
  const result = sanitizeTaskValue(nested)
  assert.equal(result.retryable, false)
  assert.ok(JSON.stringify(result.value).includes('[DEPTH_LIMIT]'))
})
