import { computed, ref } from 'vue'

import { GROUPS, TOOLS } from '@/config/tools'

const STORAGE_KEY = 'ppx-v2-modules'

const detectPlatform = () => {
  if (typeof navigator === 'undefined') return 'unknown'
  const value = `${navigator.userAgent || ''} ${navigator.platform || ''}`.toLowerCase()
  if (value.includes('win')) return 'windows'
  if (value.includes('mac')) return 'macos'
  if (value.includes('linux')) return 'linux'
  return 'unknown'
}

const readPreferences = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    return raw && typeof raw === 'object' ? raw : {}
  } catch {
    return {}
  }
}

const preferences = ref(readPreferences())
const platform = detectPlatform()

const persist = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences.value))
  } catch {
    // localStorage 不可写时仅维持当前会话状态。
  }
}

export const isPlatformSupported = (tool) => !tool.platforms?.length || tool.platforms.includes(platform)

export const isToolEnabled = (tool) => {
  if (!isPlatformSupported(tool)) return false
  if (tool.locked) return true
  const saved = preferences.value[tool.id]
  return typeof saved === 'boolean' ? saved : tool.defaultEnabled !== false
}

export function useToolRegistry() {
  const enabledTools = computed(() => TOOLS.filter((tool) => isToolEnabled(tool)))
  const groupedTools = computed(() => GROUPS.map((group) => ({ ...group, tools: enabledTools.value.filter((tool) => tool.group === group.id) })).filter((group) => group.tools.length))

  const setToolEnabled = (id, enabled) => {
    const tool = TOOLS.find((item) => item.id === id)
    if (!tool || tool.locked || !isPlatformSupported(tool)) return
    preferences.value = { ...preferences.value, [id]: !!enabled }
    persist()
  }

  const resetToolPreferences = () => {
    preferences.value = {}
    persist()
  }

  return {
    allTools: TOOLS,
    enabledTools,
    groupedTools,
    platform,
    preferences,
    isPlatformSupported,
    isToolEnabled,
    setToolEnabled,
    resetToolPreferences
  }
}
