import { computed, reactive, ref, watch } from 'vue'

const drafts = new Map()
export const draftKeys = ref([])
export const incomingAssets = ref([])
export const workspaceTool = ref('home')
const incomingTool = ref('')
export const currentIncomingAssets = computed(() => (incomingTool.value === workspaceTool.value ? incomingAssets.value : []))
export function clearIncomingFiles() {
  incomingAssets.value = []
  incomingTool.value = ''
}
export function fileIdentity(path) {
  const value = String(path || '')
  return /^[a-z]:[\\/]|^\\\\/i.test(value) ? value.replace(/\\/g, '/').toLowerCase() : value
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

export function consumeIncomingFiles() {
  const files = currentIncomingAssets.value.map((asset) => {
    const filename = asset.path.split(/[\\/]/).pop()
    return { path: asset.path, filename, ext: '.' + filename.split('.').pop(), dir: asset.path.slice(0, -filename.length) }
  })
  if (files.length) clearIncomingFiles()
  return files
}
const CONFIG_PREFIX = 'ppx-workspace-v1:'
const PRIVATE_OR_RUNTIME = /password|passwd|secret|token|cookie|authorization|api.?key|^files?$|filePath|^source$|^input$|^text$|content|preview|result|output$|outputs$|generated|loading|busy|logs|schema$|sheets|groups|summary|profiles|operations|skipped|history|dataUrl|base64|^left$|^right$/i

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
export function handoffAssets(assets, tool) {
  incomingAssets.value = assets.filter((item) => item.kind !== 'directory' && item.exists !== false)
  incomingTool.value = tool
  window.dispatchEvent(new CustomEvent('ppx-navigate', { detail: { tool } }))
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
