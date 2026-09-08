// Result handoff rules mirror the file pickers in the receiving panels.
// Keeping this module free of UI/runtime imports makes suggestions testable.

const IMAGE_EXTENSIONS = ['png', 'apng', 'jpg', 'jpeg', 'jpe', 'jfif', 'webp', 'bmp', 'dib', 'tif', 'tiff', 'gif', 'avif', 'avifs', 'ico', 'icns', 'tga', 'icb', 'vda', 'vst', 'qoi', 'ppm', 'pnm', 'pbm', 'pgm', 'pfm', 'jp2', 'j2k', 'j2c', 'jpc', 'jpf', 'jpx']
const CONVERSION_EXTENSIONS = [
  'jpg',
  'jpeg',
  'png',
  'webp',
  'gif',
  'avif',
  'tif',
  'tiff',
  'bmp',
  'heic',
  'heif',
  'ico',
  'tga',
  'cr2',
  'cr3',
  'nef',
  'arw',
  'dng',
  'txt',
  'md',
  'html',
  'json',
  'csv',
  'xml',
  'yaml',
  'epub',
  'mobi',
  'doc',
  'docx',
  'odt',
  'rtf',
  'wps',
  'wpt',
  'wpd',
  'ofd',
  'xls',
  'xlsx',
  'xlsm',
  'ods',
  'tsv',
  'et',
  'ett',
  'ppt',
  'pptx',
  'odp',
  'dps',
  'dpt',
  'pdf',
  'mp3',
  'wav',
  'flac',
  'm4a',
  'aac',
  'ogg',
  'opus',
  'wma',
  'mp4',
  'mov',
  'mkv',
  'webm',
  'avi',
  'm4v',
  'wmv',
  'flv',
  'zip'
]
const VIDEO_EXTENSIONS = ['mp4', 'mov', 'avi', 'mkv', 'webm']
const PDF_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'avif', 'tif', 'tiff', 'bmp', 'heic', 'heif', 'ico', 'tga', 'cr2', 'cr3', 'crw', 'nef', 'arw', 'dng', 'raf', 'rw2', 'orf', 'pef', 'srw', '3fr', 'erf', 'fff', 'iiq', 'kdc', 'mef', 'mrw', 'x3f']

export const RESULT_ROUTES = [
  { id: 'image/compress', tool: 'image', feature: 'compress', label: '压缩图片', description: '批量压缩图片，保留原文件。', extensions: IMAGE_EXTENSIONS },
  { id: 'image/watermark', tool: 'image', feature: 'watermark', label: '添加图片水印', description: '批量为图片添加文字或图片水印。', extensions: IMAGE_EXTENSIONS },
  { id: 'image/rotate', tool: 'image', feature: 'rotate', label: '旋转图片', description: '批量旋转或翻转图片。', extensions: IMAGE_EXTENSIONS },
  { id: 'conversion/images-pdf', tool: 'conversion', feature: 'images-pdf', label: '图片合成 PDF', description: '按当前顺序将图片装订为 PDF。', extensions: PDF_IMAGE_EXTENSIONS, dependency: 'flyingmouse' },
  { id: 'conversion/merge-pdf', tool: 'conversion', feature: 'merge-pdf', label: '转换引擎合并 PDF', description: '使用转换中心合并完整 PDF 文件。', extensions: ['pdf'], capability: { minimumAssets: 2 }, dependency: 'flyingmouse' },
  { id: 'pdf/compress', tool: 'pdf', feature: 'compress', label: '压缩 PDF', description: '压缩单份 PDF 文件体积。', extensions: ['pdf'], capability: { maximumAssets: 1 } },
  { id: 'pdf/ocr', tool: 'pdf', feature: 'ocr', label: 'PDF OCR', description: '识别单份扫描件中的文字。', extensions: ['pdf'], capability: { maximumAssets: 1 }, dependency: 'ocr' },
  { id: 'pdf/merge', tool: 'pdf', feature: 'merge', label: '合并 PDF', description: '按当前顺序合并多份 PDF。', extensions: ['pdf'], capability: { minimumAssets: 2 } },
  { id: 'word/merge', tool: 'word', feature: 'merge', label: '合并 Word', description: '按当前顺序合并 DOCX 文档。', extensions: ['docx'], capability: { minimumAssets: 2 } },
  { id: 'excel/merge', tool: 'excel', feature: 'merge', label: '合并 Excel', description: '将多个 Excel 数据表合并为主表。', extensions: ['xlsx', 'xlsm', 'xltx', 'xltm'], capability: { minimumAssets: 2 } },
  { id: 'document/index', tool: 'document', feature: 'index', label: '建立文档索引', description: '加入本地全文检索索引。', extensions: ['pdf', 'docx', 'xlsx', 'xlsm', 'txt', 'md', 'markdown', 'csv', 'json', 'log'] },
  { id: 'conversion/universal', tool: 'conversion', feature: 'universal', label: '转换格式', description: '由本地转换引擎分析可用目标格式。', extensions: CONVERSION_EXTENSIONS, dependency: 'flyingmouse' },
  { id: 'video/compress', tool: 'video', feature: 'compress', label: '压缩视频', description: '压缩单个视频，降低文件体积。', extensions: VIDEO_EXTENSIONS, capability: { maximumAssets: 1 }, dependency: 'ffmpeg' },
  { id: 'video/cut', tool: 'video', feature: 'cut', label: '截取视频', description: '截取单个视频的指定时间段。', extensions: VIDEO_EXTENSIONS, capability: { maximumAssets: 1 }, dependency: 'ffmpeg' },
  { id: 'file/archive', tool: 'file', feature: 'archive', label: '打包归档', description: '将文件统一打包为 ZIP 或 7Z。', extensions: null }
]

const ROUTE_BY_ID = new Map(RESULT_ROUTES.map((route) => [route.id, route]))
const extensionOfPath = (path) => {
  const filename = path.split(/[\\/]/).pop() || ''
  const match = filename.toLowerCase().match(/\.([^.]+)$/)
  return match ? match[1] : ''
}
const isWindowsPath = (path) => /^[a-z]:[\\/]|^\\\\/i.test(path)
const pathIdentity = (path) => (isWindowsPath(path) ? path.replace(/\\/g, '/').toLowerCase() : path)
const reasonForInvalid = (asset) => {
  if (!asset || typeof asset !== 'object') return '结果项无效'
  if (asset.kind === 'directory') return '文件夹不能作为此处的结果文件'
  if (asset.exists === false) return '文件已移动或删除'
  if (typeof asset.path !== 'string' || !asset.path.trim()) return '缺少可用的文件路径'
  return ''
}

/** Return the route and only the assets that its receiver can safely accept. */
export function planResultHandoff(assets, routeId) {
  const route = ROUTE_BY_ID.get(routeId) || null
  const values = Array.isArray(assets) ? assets : []
  if (!route) {
    return {
      route: null,
      assets: [],
      skipped: values.map((asset) => ({ asset, reason: '未找到可用的接力操作' })),
      acceptedCount: 0,
      skippedCount: values.length
    }
  }
  const accepted = []
  const skipped = []
  const seen = new Set()
  const allowed = route.extensions ? new Set(route.extensions) : null
  for (const asset of values) {
    const invalid = reasonForInvalid(asset)
    if (invalid) {
      skipped.push({ asset, reason: invalid })
      continue
    }
    const identity = pathIdentity(asset.path)
    if (seen.has(identity)) {
      skipped.push({ asset, reason: '与已选结果路径重复' })
      continue
    }
    const extension = extensionOfPath(asset.path)
    if (allowed && !allowed.has(extension)) {
      skipped.push({ asset, reason: extension ? `不支持 .${extension} 文件` : '文件没有可识别的扩展名' })
      continue
    }
    seen.add(identity)
    accepted.push(asset)
  }
  if (route.capability?.maximumAssets && accepted.length > route.capability.maximumAssets) {
    skipped.push(...accepted.splice(0).map((asset) => ({ asset, reason: '该操作一次只能接收一个文件，请先只选择一项' })))
  }
  return { route, assets: accepted, skipped, acceptedCount: accepted.length, skippedCount: skipped.length }
}

const routeRank = (route) => {
  if (route.id === 'file/archive') return 100
  if (route.extensions === null) return 90
  return route.extensions.length
}

/** Suggest usable routes in a stable, type-specific-first order. */
export function getResultRoutes(assets) {
  const plans = RESULT_ROUTES.map((route) => planResultHandoff(assets, route.id)).filter((plan) => plan.acceptedCount > 0)
  return plans
    .filter((plan) => !plan.route.capability?.minimumAssets || plan.acceptedCount >= plan.route.capability.minimumAssets)
    .filter((plan) => !(plan.route.capability?.maximumAssets && plan.acceptedCount !== validUniqueCount(assets)))
    .sort((left, right) => {
      const complete = Number(left.skippedCount === 0) - Number(right.skippedCount === 0)
      if (complete) return -complete
      const specificity = routeRank(left.route) - routeRank(right.route)
      if (specificity) return specificity
      return left.route.id.localeCompare(right.route.id)
    })
}

function validUniqueCount(assets) {
  const seen = new Set()
  for (const asset of Array.isArray(assets) ? assets : []) {
    if (reasonForInvalid(asset)) continue
    const identity = pathIdentity(asset.path)
    if (seen.has(identity)) continue
    seen.add(identity)
  }
  return seen.size
}
