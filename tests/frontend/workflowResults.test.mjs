import test from 'node:test'
import assert from 'node:assert/strict'
import { compatibleResult, dataResultEntries, previewResult, readResultPath, referenceOptions, resultFieldsForStep } from '../../gui/src/utils/workflowResults.mjs'

const descriptor = {
  fields: [{ name: 'operation', default: 'format' }],
  resultFields: [
    { path: 'result', label: '处理结果', type: 'text', when: { field: 'operation', values: ['format', 'compress'] } },
    { path: 'result', label: '处理结果', type: 'boolean', when: { field: 'operation', values: ['validate'] } },
    { path: 'result', label: '处理结果', type: 'any', when: { field: 'operation', values: ['query'] } }
  ]
}

test('configured JSON operation advertises its actual result type and deduplicates dynamic variants', () => {
  assert.equal(resultFieldsForStep({ args: {} }, descriptor)[0].type, 'text')
  assert.equal(resultFieldsForStep({ argsText: '{"operation":"validate"}' }, descriptor)[0].type, 'boolean')
  const dynamic = resultFieldsForStep({ args: { operation: '{{input.mode}}' } }, descriptor)
  assert.equal(dynamic.length, 1)
  assert.equal(dynamic[0].type, 'any')
  assert.deepEqual(resultFieldsForStep({ argsText: 'null' }, descriptor), [])
  assert.deepEqual(resultFieldsForStep({ argsText: '{bad' }, descriptor), [])
})

test('reference options match result types and preserve exact field paths', () => {
  const prior = [{ id: 'clean step', name: '清理', resultFields: [
    { path: 'result', label: '处理结果', type: 'text' },
    { path: 'stats.uniqueCount', label: '去重后行数', type: 'number' },
    { path: 'outputPaths', label: '结果文件列表', type: 'files' },
    { path: 'outputPaths.0', label: '第一份结果文件', type: 'file' }
  ] }]
  assert.deepEqual(referenceOptions(prior, { type: 'textarea' }).map((item) => item.value), ['{{steps.clean-step.result}}'])
  assert.equal(referenceOptions(prior, { type: 'number' })[0].value, '{{steps.clean-step.stats.uniqueCount}}')
  assert.equal(referenceOptions(prior, { type: 'file' })[0].value, '{{steps.clean-step.outputPaths.0}}')
  assert.equal(referenceOptions(prior, { type: 'paths' })[0].value, '{{steps.clean-step.outputPaths}}')
  assert.equal(referenceOptions(prior, { type: 'boolean' }).length, 0)
  assert.deepEqual(referenceOptions([{ ...prior[0], id: '!!!' }], { type: 'text' }), [])
})

test('dynamic values are explicitly labeled and array-only JSON excludes objects', () => {
  assert.equal(compatibleResult({ type: 'json', jsonType: 'array' }, { type: 'object' }), false)
  assert.equal(compatibleResult({ type: 'json', jsonType: 'array' }, { type: 'list' }), true)
  assert.equal(compatibleResult({ type: 'mapping' }, { type: 'object' }), true)
  const options = referenceOptions([{ id: 'query', name: '查询', resultFields: [{ path: 'result', label: '处理结果', type: 'any' }] }], { type: 'number' })
  assert.match(options[0].label, /动态类型/)
})

test('data results retain zero false empty text and null, while excluding absent and file fields', () => {
  const values = { zero: 0, flag: false, empty: '', nullable: null, paths: ['a'], nested: [{ count: 2 }] }
  const fields = ['zero', 'flag', 'empty', 'nullable', 'missing', 'nested.0.count'].map((path) => ({ path, label: path, type: 'any' }))
  const entries = dataResultEntries(values, [...fields, fields[0], { path: 'paths', type: 'files' }])
  assert.deepEqual(entries.map((item) => item.value), [0, false, '', null, 2])
  assert.deepEqual(readResultPath(values, '__proto__.constructor'), { found: false })
  assert.deepEqual(readResultPath(values, 'nested.2.count'), { found: false })
})

test('preview is bounded without losing the full copy or cutting a surrogate pair', () => {
  assert.equal(previewResult(false).text, 'false')
  assert.equal(previewResult(0).text, '0')
  assert.equal(previewResult('').empty, true)
  const preview = previewResult('a🙂b', 2)
  assert.equal(preview.text, 'a')
  assert.equal(preview.fullText, 'a🙂b')
  assert.equal(preview.truncated, true)
  assert.equal(previewResult({ count: 0 }).fullText, '{\n  "count": 0\n}')
})
