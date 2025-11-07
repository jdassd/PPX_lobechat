import { callBridge, hasNativeBridge } from './nativeBridge'

const LOCAL_PREFIX = 'ppx-toolkit::'
const hasLocalStorage = typeof window !== 'undefined' && window.localStorage

const serialize = (value) => {
  if (value === undefined) {
    return ''
  }
  return typeof value === 'string' ? value : JSON.stringify(value)
}

const parse = (value, fallback) => {
  if (!value) {
    return fallback
  }
  try {
    return JSON.parse(value)
  } catch (err) {
    console.warn('[storage] parse fail =>', err)
    return fallback
  }
}

export const readStorage = async (key, fallback = null) => {
  if (hasNativeBridge()) {
    try {
      const raw = await callBridge('storage_get', key)
      return parse(raw, fallback)
    } catch (err) {
      console.warn('[storage] native read fail =>', err)
    }
  }
  if (hasLocalStorage) {
    const raw = window.localStorage.getItem(LOCAL_PREFIX + key)
    return parse(raw, fallback)
  }
  return fallback
}

export const writeStorage = async (key, value) => {
  const payload = serialize(value)
  if (hasNativeBridge()) {
    try {
      await callBridge('storage_set', key, payload)
      return
    } catch (err) {
      console.warn('[storage] native write fail =>', err)
    }
  }
  if (hasLocalStorage) {
    window.localStorage.setItem(LOCAL_PREFIX + key, payload)
  }
}
