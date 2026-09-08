const SENSITIVE_KEY = /(password|passwd|secret|token|cookie|authorization|api[_-]?key)/i

const isEmptySecret = (value) => value === null || value === '' || value === false || (Array.isArray(value) ? !value.length : value && typeof value === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(value)) && !Object.keys(value).length)

export const sanitizeTaskValue = (value, key = '', depth = 0) => {
  if (key && SENSITIVE_KEY.test(key) && !isEmptySecret(value)) return { value: '[REDACTED]', retryable: false }
  if (depth > 10) return { value: '[DEPTH_LIMIT]', retryable: false }
  if (value === null || ['boolean', 'number'].includes(typeof value)) return { value, retryable: true }
  if (typeof value === 'string') return value.length <= 200000 ? { value, retryable: true } : { value: `${value.slice(0, 200000)}\n[TRUNCATED]`, retryable: false }
  if (Array.isArray(value)) {
    let retryable = true
    const output = value.map((item) => {
      const safe = sanitizeTaskValue(item, '', depth + 1)
      retryable = retryable && safe.retryable
      return safe.value
    })
    return { value: output, retryable }
  }
  if (value && typeof value === 'object') {
    let retryable = true
    const output = {}
    Object.entries(value).forEach(([itemKey, item]) => {
      const safe = sanitizeTaskValue(item, itemKey, depth + 1)
      output[itemKey] = safe.value
      retryable = retryable && safe.retryable
    })
    return { value: output, retryable }
  }
  return { value: String(value), retryable: false }
}
