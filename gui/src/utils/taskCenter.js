import { computed, ref } from 'vue'

const STORAGE_KEY = 'ppx-v25-tasks'
const LEGACY_STORAGE_KEYS = ['ppx-v24-tasks', 'ppx-v23-tasks', 'ppx-v2-tasks']
const MAX_TASKS = 200
const SENSITIVE_KEY = /(password|passwd|secret|token|cookie|authorization|api[_-]?key)/i

// 仅将真正产生结果、改变文件或执行较重分析的调用送入持久任务队列。
export const TASK_METHODS = {
  image_format_convert: ['image', 'convert', '图片格式转换'],
  image_batch_compress: ['image', 'compress', '批量压缩图片'],
  image_crop: ['image', 'crop', '裁剪图片'],
  image_add_watermark: ['image', 'watermark', '添加图片水印'],
  image_rotate_flip: ['image', 'rotate', '旋转与翻转图片'],
  image_concat: ['image', 'concat', '拼接图片'],
  image_batch_rename: ['image', 'rename', '图片批量命名'],
  image_to_pdf: ['image', 'pdf', '图片合成 PDF'],
  ocr_image: ['image', 'ocr', '图片 OCR'],
  pdf_convert_to_images: ['pdf', 'image', 'PDF 转图片'],
  pdf_convert_to_scan: ['pdf', 'scan', '生成扫描版 PDF'],
  pdf_compress: ['pdf', 'compress', '压缩 PDF'],
  pdf_merge: ['pdf', 'merge', '合并 PDF'],
  pdf_split: ['pdf', 'split', '拆分 PDF'],
  pdf_cut: ['pdf', 'cut', '切割 PDF'],
  pdf_multi_cut: ['pdf', 'cut', '批量切割 PDF'],
  pdf_extract_text: ['pdf', 'text', '提取 PDF 文本'],
  ocr_pdf: ['pdf', 'ocr', '扫描 PDF OCR'],
  pdf_to_word: ['pdf', 'word', 'PDF 转 Word'],
  pdf_extract_images: ['pdf', 'images', '提取 PDF 图片'],
  pdf_page_workbench: ['pdf', 'pages', '整理 PDF 页面'],
  pdf_secure: ['pdf', 'security', '保护 PDF'],
  word_split: ['word', 'split', '拆分 Word'],
  word_cut: ['word', 'cut', '切割 Word'],
  word_merge: ['word', 'merge', '合并 Word'],
  excel_column_profile: ['excel', 'profile', 'Excel 数据质检'],
  excel_process: ['excel', 'process', '处理 Excel 数据'],
  excel_split_by_column: ['excel', 'split', '按列拆分 Excel'],
  excel_merge_tables: ['excel', 'merge', '合并 Excel 表格'],
  excel_quality_report: ['excel', 'profile', '导出 Excel 质检报告'],
  text_format_json: ['text', 'json', '格式化 JSON'],
  text_case_transform: ['text', 'transform', '转换文本'],
  text_deduplicate_sort: ['text', 'dedup', '文本去重排序'],
  text_batch_replace: ['text', 'replace', '批量替换文本'],
  video_format_convert: ['video', 'convert', '转换视频格式'],
  video_compress: ['video', 'compress', '压缩视频'],
  video_cut: ['video', 'cut', '截取视频'],
  video_extract_audio: ['video', 'audio', '提取视频音频'],
  video_concat: ['video', 'concat', '合并视频'],
  file_search: ['file', 'search', '搜索文件'],
  file_auto_classify: ['file', 'classify', '自动分类文件'],
  file_batch_copy: ['file', 'copy', '批量复制文件'],
  file_batch_delete: ['file', 'delete', '批量删除文件'],
  file_batch_rename: ['file', 'rename', '批量重命名'],
  file_batch_rename_undo: ['file', 'rename', '撤销批量重命名'],
  file_deduplicate: ['file', 'dedup', '查找重复文件'],
  file_compress: ['file', 'archive', '压缩文件'],
  file_decompress: ['file', 'archive', '解压文件'],
  file_recycle_restore: ['file', 'recycle', '恢复回收文件'],
  file_recycle_purge: ['file', 'recycle', '清理回收文件'],
  seal_generate: ['seal', 'design', '生成印章图片'],
  ocr_table: ['document', 'table', '表格 OCR'],
  document_index_build: ['document', 'index', '建立文档索引'],
  workflow_run: ['workflow', 'history', '运行工作流']
}

const sanitizeValue = (value, key = '', depth = 0) => {
  if (key && SENSITIVE_KEY.test(key)) return { value: '[REDACTED]', retryable: false }
  if (depth > 10) return { value: '[DEPTH_LIMIT]', retryable: false }
  if (value === null || ['boolean', 'number'].includes(typeof value)) return { value, retryable: true }
  if (typeof value === 'string') return value.length <= 200000 ? { value, retryable: true } : { value: `${value.slice(0, 200000)}\n[TRUNCATED]`, retryable: false }
  if (Array.isArray(value)) {
    let retryable = true
    const output = value.map((item) => {
      const safe = sanitizeValue(item, '', depth + 1)
      retryable = retryable && safe.retryable
      return safe.value
    })
    return { value: output, retryable }
  }
  if (value && typeof value === 'object') {
    let retryable = true
    const output = {}
    Object.entries(value).forEach(([itemKey, item]) => {
      const safe = sanitizeValue(item, itemKey, depth + 1)
      output[itemKey] = safe.value
      retryable = retryable && safe.retryable
    })
    return { value: output, retryable }
  }
  return { value: String(value), retryable: false }
}

const readTasks = () => {
  try {
    const current = localStorage.getItem(STORAGE_KEY)
    const legacy = LEGACY_STORAGE_KEYS.map((key) => localStorage.getItem(key)).find(Boolean)
    const list = JSON.parse(current || legacy || '[]')
    if (!Array.isArray(list)) return []
    return list.map((item) => (item.status === 'running' ? { ...item, status: 'interrupted', message: '应用在任务完成前退出' } : item))
  } catch {
    return []
  }
}

export const tasks = ref(readTasks())
export const queuePaused = ref(false)
export const runningTasks = computed(() => tasks.value.filter((item) => ['queued', 'running'].includes(item.status)))
export const recentTasks = computed(() => tasks.value.slice(0, 6))

const persist = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks.value.slice(0, MAX_TASKS)))
  } catch {
    // 任务记录是增强能力，写入失败不应影响实际文件处理。
  }
}

const OUTPUT_KEYS = ['output', 'outputPath', 'outputDir', 'path', 'archive', 'file']
const OUTPUT_LIST_KEYS = ['outputs', 'files', 'created', 'items']

const isPathLike = (value) => {
  if (typeof value !== 'string') return false
  const raw = value.trim()
  return Boolean(raw && raw.length <= 4096 && !/[\r\n]/.test(raw) && (/^(?:[a-z]:[\\/]|[\\/])/i.test(raw) || raw.includes('/') || raw.includes('\\')))
}

export const extractOutputs = (data) => {
  if (!data || typeof data !== 'object') return []
  const paths = []
  const add = (value) => {
    if (isPathLike(value)) {
      paths.push(value.trim())
      return
    }
    if (Array.isArray(value)) {
      value.slice(0, 200).forEach(add)
      return
    }
    if (value && typeof value === 'object') OUTPUT_KEYS.forEach((key) => key in value && add(value[key]))
  }
  const candidateKeys = [...OUTPUT_KEYS, ...OUTPUT_LIST_KEYS]
  candidateKeys.forEach((key) => key in data && add(data[key]))
  return [...new Set(paths)].map((path) => {
    const normalized = path.replace(/[\\/]+$/, '')
    const name = normalized.split(/[\\/]/).pop() || path
    return { path, name, kind: path.endsWith('/') || path.endsWith('\\') ? 'directory' : 'file', exists: null, size: null }
  })
}

const toMilliseconds = (value) => {
  if (!value) return null
  return Number(value) < 10_000_000_000 ? Number(value) * 1000 : Number(value)
}

export const isTaskMethod = (method) => Boolean(TASK_METHODS[method])

export const beginApiTask = (method, args = [], id = '') => {
  const meta = TASK_METHODS[method]
  if (!meta || args[0]?.dryRun) return null
  const [tool, feature, label] = meta
  const safe = sanitizeValue(args)
  const task = {
    id: id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    schemaVersion: 2,
    method,
    args: safe.value,
    retryable: safe.retryable,
    tool,
    feature,
    label,
    status: 'queued',
    progress: 0,
    startedAt: Date.now(),
    endedAt: null,
    message: '等待执行',
    output: '',
    outputs: []
  }
  tasks.value = [task, ...tasks.value.filter((item) => item.id !== task.id)].slice(0, MAX_TASKS)
  persist()
  return task.id
}

export const updateApiTask = (id, patch = {}) => {
  if (!id) return
  tasks.value = tasks.value.map((item) => (item.id === id ? { ...item, ...patch } : item))
  persist()
}

export const settleApiTask = (id, result, error) => {
  if (!id) return
  const current = tasks.value.find((item) => item.id === id)
  if (!current) return
  const ok = !error && result?.ok
  const outputs = ok ? extractOutputs(result?.data) : []
  updateApiTask(id, {
    status: ok ? 'success' : 'failed',
    progress: 100,
    endedAt: Date.now(),
    message: error?.message || result?.message || (ok ? '处理完成' : '处理失败'),
    output: outputs[0]?.path || '',
    outputs
  })
}

export const hydrateBackendTasks = (backendTasks = [], paused = false) => {
  if (!Array.isArray(backendTasks)) return
  queuePaused.value = Boolean(paused)
  const mapped = backendTasks.map((task) => {
    const meta = TASK_METHODS[task.method] || ['advanced', '', task.method]
    const [tool, feature, label] = meta
    const outputs = Array.isArray(task.outputs) && task.outputs.length ? task.outputs : extractOutputs(task.result)
    return {
      ...task,
      tool,
      feature,
      label,
      startedAt: toMilliseconds(task.startedAt || task.createdAt),
      endedAt: toMilliseconds(task.endedAt),
      output: outputs[0]?.path || '',
      outputs,
      progress: Number(task.progress || 0)
    }
  })
  const backendIds = new Set(mapped.map((item) => item.id))
  tasks.value = [...mapped, ...tasks.value.filter((item) => !backendIds.has(item.id))].slice(0, MAX_TASKS)
  persist()
}

export const clearFinishedTasks = () => {
  tasks.value = tasks.value.filter((item) => ['queued', 'running'].includes(item.status))
  persist()
}

export const removeTasksByIds = (ids = []) => {
  const removed = new Set(ids)
  tasks.value = tasks.value.filter((item) => !removed.has(item.id))
  persist()
}
