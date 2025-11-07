const hasWindow = typeof window !== 'undefined'

export const hasNativeBridge = () => {
  return Boolean(hasWindow && window.pywebview && window.pywebview.api)
}

export const callBridge = async (method, ...args) => {
  if (!hasNativeBridge()) {
    throw new Error('pywebview bridge 不可用')
  }
  const handler = window.pywebview.api[method]
  if (typeof handler !== 'function') {
    throw new Error(`pywebview 未实现 ${method}`)
  }
  return handler(...args)
}
