import { ref } from 'vue'

// 收藏项既支持工具 id，也支持 `tool:feature` 形式的具体动作。
const KEY = 'ppx-favorite-tools'

export function getFavorites() {
  try {
    const ids = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(ids) ? ids.filter((id) => typeof id === 'string') : []
  } catch {
    return []
  }
}

export const favoriteIds = ref(getFavorites())

export function isFavorite(id) {
  return favoriteIds.value.includes(id)
}

export function toggleFavorite(toolId) {
  const ids = favoriteIds.value
  const next = ids.includes(toolId) ? ids.filter((id) => id !== toolId) : [toolId, ...ids]
  favoriteIds.value = next
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    /* localStorage 不可用时仍保持当前页面可操作 */
  }
  return next
}

export function clearFavorites() {
  favoriteIds.value = []
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* 收藏是增强能力，清理失败不影响使用 */
  }
}
