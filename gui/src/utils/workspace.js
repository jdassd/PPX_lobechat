import { computed, reactive, ref, watch } from 'vue'
import { planResultHandoff } from './resultRouting.mjs'
import { fileIdentity } from './inputOrigins.mjs'

export { fileIdentity } from './inputOrigins.mjs'

const drafts = new Map()
export const draftKeys = ref([])
export const incomingAssets = ref([])
export const workspaceTool = ref('home')
const incomingRoute = ref('')
export const incomingRouteId = computed(() => incomingRoute.value)
export const currentIncomingAssets = computed(() => (incomingRoute.value.split('/')[0] === workspaceTool.value ? incomingAssets.value : []))
export function clearIncomingFiles() {
  incomingAssets.value = []
  incomingRoute.value = ''
}
export function mergeFileQueue(current, incoming) {
  const result = [...current]
  const seen = new Set(current.map((file) => fileIdentity(typeof file === 'string' ? file : file.path)))
  for (const file of incoming) {
    const identity = fileIdentity(typeof file === 'string' ? file : file.path)
    if (!seen.has(identity)) {
      result.push(file)
      seen.add(identity)
    }
  }
  return result
}

export function consumeIncomingFiles(routeId) {
  // A handoff is intentionally consumed only by its declared primary input.
  // This prevents hidden/kept-alive panels and auxiliary pickers from stealing it.
  if (!routeId || routeId !== incomingRoute.value || routeId.split('/')[0] !== workspaceTool.value) return []
  const files = currentIncomingAssets.value.map((asset) => {
    const filename = asset.path.split(/[\\/]/).pop()
    return { path: asset.path, filename, ext: filename.includes('.') ? '.' + filename.split('.').pop() : '', dir: asset.path.slice(0, -filename.length), ...(asset.origin ? { origin: { ...asset.origin } } : {}) }
  })
  if (files.length) clearIncomingFiles()
  return files
}
const CONFIG_PREFIX = 'ppx-workspace-v1:'
const PRIVATE_OR_RUNTIME = /password|passwd|secret|token|cookie|authorization|api.?key|^files?$|filePath|^source$|^input$|^text$|^origin$|^inputOrigins$|^inputOriginWarnings$|^sourceTaskId$|content|preview|result|output$|outputs$|generated|loading|busy|logs|schema$|sheets|groups|summary|profiles|operations|skipped|history|dataUrl|base64|^left$|^right$/i

export function safeConfiguration(value, depth = 0) {
  if (depth > 5 || !value || typeof value !== 'object') return {}
  const output = {}
  Object.entries(value || {}).forEach(([key, item]) => {
    if (PRIVATE_OR_RUNTIME.test(key) || /file(Path|s|List)$|^archiveFile$/i.test(key) || ['__proto__', 'constructor', 'prototype', 'targetsByFile'].includes(key)) return
    if (['string', 'number', 'boolean'].includes(typeof item) && String(item).length < 4096 && !String(item).startsWith('data:')) output[key] = item
    else if (Array.isArray(item) && item.length <= 128 && item.every((entry) => ['string', 'number', 'boolean'].includes(typeof entry) && String(entry).length < 4096)) output[key] = [...item]
    else if (item && typeof item === 'object' && !Array.isArray(item)) output[key] = safeConfiguration(item, depth + 1)
  })
  return output
}

export function applyConfiguration(target, saved) {
  Object.entries(safeConfiguration(saved)).forEach(([key, value]) => {
    if (Array.isArray(value)) target[key] = [...value]
    else if (value && typeof value === 'object') {
      if (!target[key] || typeof target[key] !== 'object' || Array.isArray(target[key])) target[key] = {}
      applyConfiguration(target[key], value)
    } else if (!(key in target) || typeof target[key] === typeof value) target[key] = value
  })
  return target
}

export function useDraft(key, defaults) {
  if (drafts.has(key)) return drafts.get(key)
  let saved = {}
  try {
    saved = JSON.parse(localStorage.getItem(CONFIG_PREFIX + key) || '{}')
  } catch {
    /* A corrupt preference must not block a tool. */
  }
  const valid = Object.fromEntries(Object.entries(safeConfiguration(saved)).filter(([name, value]) => name in defaults && typeof defaults[name] === typeof value))
  const draft = reactive(applyConfiguration({ ...defaults }, valid))
  drafts.set(key, draft)
  draftKeys.value = [...drafts.keys()]
  watch(
    draft,
    () => {
      try {
        localStorage.setItem(CONFIG_PREFIX + key, JSON.stringify(safeConfiguration(draft)))
      } catch {
        /* The in-memory draft remains available. */
      }
    },
    { deep: true }
  )
  return draft
}

export const getDraft = (key) => drafts.get(key)
export const draftsForTool = (tool) => computed(() => draftKeys.value.filter((key) => key.startsWith(`${tool}/`)))
export function handoffAssets(assets, routeId, sourceTaskId = '') {
  const plan = planResultHandoff(assets, routeId)
  if (!plan.acceptedCount || plan.acceptedCount < (plan.route.capability?.minimumAssets || 1)) return false
  incomingAssets.value = plan.assets.map((asset) => ({ ...asset, origin: sourceTaskId ? { sourceTaskId, sourceAssetPath: asset.path } : undefined }))
  incomingRoute.value = routeId
  const [tool, feature = ''] = routeId.split('/')
  window.dispatchEvent(new CustomEvent('ppx-navigate', { detail: { tool, feature } }))
  return true
}

// Retired navigation records are removed; this never accesses users' documents.
for (const key of ['ppx-favorite-tools', 'ppx-recents', 'ppx-favorites', 'ppx-recent', 'ppx-v2-favorites', 'ppx-v2-recent']) {
  try {
    const items = JSON.parse(localStorage.getItem(key) || 'null')
    if (Array.isArray(items)) localStorage.setItem(key, JSON.stringify(items.filter((item) => !(typeof item === 'string' ? item : item?.tool || item?.id || '').startsWith('mindmap'))))
  } catch {
    /* Preserve malformed legacy records for recovery. */
  }
}
