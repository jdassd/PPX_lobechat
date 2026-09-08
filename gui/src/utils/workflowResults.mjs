const aliases = { textarea: 'text', string: 'text', password: 'text', select: 'text', paths: 'files' }
const fileTypes = new Set(['file', 'files', 'directory', 'directories'])

export const compatibleResult = (field, result) => {
  const target = aliases[field.type] || field.type
  const source = aliases[result.type] || result.type
  if (source === 'any') return true
  if (field.acceptStructured) return ['text', 'object', 'list', 'files', 'directories', 'number', 'boolean'].includes(source)
  if (target === 'json') return field.jsonType === 'array' ? ['list', 'files', 'directories'].includes(source) : ['object', 'list', 'files', 'directories'].includes(source)
  if (['mapping', 'mapping-number'].includes(target)) return source === 'object'
  return target === source
}

export const resultFieldsForStep = (step, descriptor) => {
  if (!descriptor) return []
  let supplied
  try {
    supplied = step.argsText === undefined ? step.args || {} : JSON.parse(step.argsText || '{}')
  } catch {
    return []
  }
  if (!supplied || Array.isArray(supplied) || typeof supplied !== 'object') return []
  const args = { ...Object.fromEntries((descriptor.fields || []).map((field) => [field.name, field.default])), ...supplied }
  const fields = new Map()
  for (const field of descriptor.resultFields || []) {
    const value = field.when && args[field.when.field]
    const uncertain = typeof value === 'string' && value.includes('{{')
    if (field.when && !uncertain && !field.when.values.includes(value)) continue
    const prior = fields.get(field.path)
    fields.set(field.path, prior && prior.type !== field.type ? { ...field, type: 'any', description: '类型由前一步运行参数决定，执行后核对' } : { ...field })
  }
  return [...fields.values()]
}

export const referenceOptions = (previous, target) =>
  previous.flatMap((step) => {
    const id = String(step.id || '')
      .replace(/[^a-zA-Z0-9_-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80)
    if (!id) return []
    return (step.resultFields || [])
      .filter((field) => compatibleResult(target, field))
      .map((field) => ({
        value: `{{steps.${id}.${field.path}}}`,
        label: `${step.name || step.id} · ${field.label}${field.type === 'any' ? '（动态类型）' : ''}`,
        description: field.description || (field.optional ? '该结果可能不存在，实际执行时核对' : ''),
        path: field.path,
        sourceStepId: id
      }))
  })

export const readResultPath = (result, path) => {
  let value = result
  for (const part of String(path).split('.')) {
    if (value === null || typeof value !== 'object' || !Object.hasOwn(value, part)) return { found: false }
    value = value[part]
  }
  return value === undefined ? { found: false } : { found: true, value }
}

export const dataResultEntries = (result, fields) => {
  const entries = new Map()
  for (const field of fields || []) {
    if (fileTypes.has(field.type) || entries.has(field.path)) continue
    const found = readResultPath(result, field.path)
    if (found.found) entries.set(field.path, { ...field, value: found.value })
  }
  return [...entries.values()]
}

export const previewResult = (value, limit = 12000) => {
  const fullText = typeof value === 'string' ? value : (JSON.stringify(value, null, 2) ?? '')
  let text = fullText.slice(0, limit)
  if (fullText.length > limit && /[\uD800-\uDBFF]$/.test(text)) text = text.slice(0, -1)
  return { fullText, text, truncated: text.length < fullText.length, empty: fullText === '' }
}
