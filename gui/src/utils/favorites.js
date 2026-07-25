// 首页工具收藏：仅保存工具 id，保持配置数据单一来源。
const KEY = 'ppx-favorite-tools'

export function getFavorites() {
  try {
    const ids = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(ids) ? ids.filter((id) => typeof id === 'string') : []
  } catch {
    return []
  }
}

export function toggleFavorite(toolId) {
  const ids = getFavorites()
  const next = ids.includes(toolId) ? ids.filter((id) => id !== toolId) : [toolId, ...ids]
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    /* localStorage 不可用时仍保持当前页面可操作 */
  }
  return next
}
