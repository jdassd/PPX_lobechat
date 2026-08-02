import { ref } from 'vue'

// 首页「最近活动」: 记录最近打开的工具和具体动作（本地存储）。
const KEY = 'ppx-recents'
const MAX = 6

export function getRecents() {
  try {
    const list = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

export const recentActions = ref(getRecents())

export function pushRecent(toolId, featureId = '') {
  if (!toolId || toolId === 'home') return
  const key = `${toolId}:${featureId || ''}`
  let list = getRecents().filter((r) => `${r.tool}:${r.feature || ''}` !== key)
  list.unshift({ tool: toolId, feature: featureId || '', ts: Date.now() })
  list = list.slice(0, MAX)
  recentActions.value = list
  try {
    localStorage.setItem(KEY, JSON.stringify(list))
  } catch {
    /* 忽略写入失败 */
  }
}

export function clearRecents() {
  recentActions.value = []
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* 忽略写入失败 */
  }
}

export function relativeTime(ts, now = Date.now()) {
  const s = Math.max(0, Math.floor((now - ts) / 1000))
  if (s < 60) return '刚刚'
  if (s < 3600) return `${Math.floor(s / 60)} 分钟前`
  if (s < 86400) return `${Math.floor(s / 3600)} 小时前`
  return `${Math.floor(s / 86400)} 天前`
}
