import { computed, ref } from 'vue'

const STORAGE_KEY = 'ppx-v2-tasks'
const MAX_TASKS = 80

// 仅记录真正产生结果或改变文件的调用；状态查询、预览和文件对话框不会污染任务中心。
const TASK_METHODS = {
  image_format_convert: ['image', 'convert', '图片格式转换'],
  image_batch_compress: ['image', 'compress', '批量压缩图片'],
  image_crop: ['image', 'crop', '裁剪图片'],
  image_add_watermark: ['image', 'watermark', '添加图片水印'],
  image_to_pdf: ['image', 'pdf', '图片合成 PDF'],
  ocr_image: ['image', 'ocr', '图片 OCR'],
  pdf_convert_to_images: ['pdf', 'image', 'PDF 转图片'],
  pdf_convert_to_scan: ['pdf', 'scan', '生成扫描版 PDF'],
  pdf_compress: ['pdf', 'compress', '压缩 PDF'],
  pdf_merge: ['pdf', 'merge', '合并 PDF'],
  pdf_split: ['pdf', 'split', '拆分 PDF'],
  pdf_cut: ['pdf', 'cut', '切割 PDF'],
  pdf_extract_text: ['pdf', 'text', '提取 PDF 文本'],
  ocr_pdf: ['pdf', 'ocr', '扫描 PDF OCR'],
  pdf_to_word: ['pdf', 'word', 'PDF 转 Word'],
  pdf_extract_images: ['pdf', 'images', '提取 PDF 图片'],
  word_split: ['word', 'split', '拆分 Word'],
  word_cut: ['word', 'cut', '切割 Word'],
  word_merge: ['word', 'merge', '合并 Word'],
  excel_process: ['excel', 'process', '处理 Excel 数据'],
  excel_merge_tables: ['excel', 'merge', '合并 Excel 表格'],
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
  file_deduplicate: ['file', 'dedup', '查找重复文件'],
  file_compress: ['file', 'archive', '压缩文件'],
  file_decompress: ['file', 'archive', '解压文件'],
  seal_generate: ['seal', 'design', '生成印章图片']
}

const readTasks = () => {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    if (!Array.isArray(list)) return []
    return list.map((item) => (item.status === 'running' ? { ...item, status: 'interrupted', message: '应用在任务完成前退出' } : item))
  } catch {
    return []
  }
}

export const tasks = ref(readTasks())
export const runningTasks = computed(() => tasks.value.filter((item) => item.status === 'running'))
export const recentTasks = computed(() => tasks.value.slice(0, 6))

const persist = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks.value.slice(0, MAX_TASKS)))
  } catch {
    // 任务记录是增强能力，写入失败不应影响实际文件处理。
  }
}

const extractOutput = (data) => {
  if (!data || typeof data !== 'object') return ''
  const direct = data.output || data.outputPath || data.outputDir || data.path || data.archive
  if (direct) return String(direct)
  const outputs = data.outputs || data.files || data.created
  return Array.isArray(outputs) && outputs.length ? String(outputs[0]?.path || outputs[0]) : ''
}

export const beginApiTask = (method, args = []) => {
  const meta = TASK_METHODS[method]
  if (!meta) return null
  if (args[0]?.dryRun) return null
  const [tool, feature, label] = meta
  const task = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    method,
    tool,
    feature,
    label,
    status: 'running',
    startedAt: Date.now(),
    endedAt: null,
    message: '正在处理',
    output: ''
  }
  tasks.value = [task, ...tasks.value].slice(0, MAX_TASKS)
  persist()
  return task.id
}

export const settleApiTask = (id, result, error) => {
  if (!id) return
  const index = tasks.value.findIndex((item) => item.id === id)
  if (index < 0) return
  const current = tasks.value[index]
  const ok = !error && result?.ok
  const next = {
    ...current,
    status: ok ? 'success' : 'failed',
    endedAt: Date.now(),
    message: error?.message || result?.message || (ok ? '处理完成' : '处理失败'),
    output: ok ? extractOutput(result?.data) : ''
  }
  tasks.value = tasks.value.map((item, itemIndex) => (itemIndex === index ? next : item))
  persist()
}

export const clearFinishedTasks = () => {
  tasks.value = tasks.value.filter((item) => item.status === 'running')
  persist()
}
