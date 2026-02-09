<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import FileSelector from '../shared/FileSelector.vue'
import ResultTable from '../shared/ResultTable.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const imageFilter = ['图片 (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tiff)']

const state = reactive({
  loading: false,
  activeTab: 'convert',
  format: {
    files: [],
    targetFormat: 'png',
    quality: 90,
    keepName: true,
    outputDir: '',
    generatedDir: '',
    result: []
  },
  compress: {
    files: [],
    mode: 'quality',
    quality: 80,
    targetSizeKB: 512,
    outputDir: '',
    generatedDir: '',
    result: []
  },
  watermark: {
    files: [],
    watermarkType: 'text',
    text: '',
    fontSize: 32,
    color: '#ffffff',
    opacity: 60,
    position: 'bottom-right',
    tile: false,
    tileSpacing: 80,
    rotation: 0,
    watermarkImage: null,
    scalePercent: 30,
    outputDir: '',
    generatedDir: '',
    result: []
  },
  crop: {
    file: null,
    mode: 'custom',
    x: 0,
    y: 0,
    width: 800,
    height: 600,
    ratio: '16:9',
    previewUrl: '',
    imageWidth: 0,
    imageHeight: 0,
    displayWidth: 0,
    displayHeight: 0,
    outputDir: '',
    generatedDir: '',
    result: ''
  },
  rotate: {
    files: [],
    operation: 'rotate90',
    angle: 0,
    flipHorizontal: false,
    flipVertical: false,
    outputDir: '',
    generatedDir: '',
    result: []
  },
  pdf: {
    files: [],
    pageSize: 'a4',
    customWidth: 2480,
    customHeight: 3508,
    perPage: 1,
    margin: 40,
    outputName: '',
    outputDir: '',
    generatedDir: '',
    result: ''
  },
  concat: {
    files: [],
    direction: 'horizontal',
    columns: 2,
    spacing: 24,
    align: 'center',
    background: '#ffffff',
    outputFormat: 'png',
    quality: 90,
    outputDir: '',
    result: ''
  },
  rename: {
    files: [],
    mode: 'sequence',
    prefix: 'img_',
    suffix: '',
    pattern: '{name}_{index}',
    digits: 4,
    startIndex: 1,
    keepExtension: true,
    copyMode: false,
    outputDir: '',
    dryRun: true,
    operations: [],
    skipped: []
  },
  exif: {
    file: null,
    data: [],
    gps: {}
  }
})

const toFileUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('file://')) {
    return path
  }
  const normalized = path.replace(/\\/g, '/')
  if (/^[a-zA-Z]:\//.test(normalized)) {
    return `file:///${normalized}`
  }
  return normalized
}

const cropPreviewRef = ref(null)

const cropInteraction = reactive({
  dragging: false,
  startX: 0,
  startY: 0,
  // 用于记录是否通过“控制手柄”调整已有裁剪框
  handle: ''
})

const hasCropImage = computed(
  () => state.crop.imageWidth > 0 && state.crop.imageHeight > 0 && state.crop.displayWidth > 0 && state.crop.displayHeight > 0
)

const hasCropRect = computed(
  () => hasCropImage.value && state.crop.width > 0 && state.crop.height > 0
)

const rotatePreviewUrl = computed(() => {
  const first = state.rotate.files[0]
  if (!first) return ''
  const path = first.path || first
  if (!path) return ''
  return getFileUrl(path)
})

const rotatePreviewStyle = computed(() => {
  const transforms = []
  const op = state.rotate.operation
  if (op === 'rotate90') {
    transforms.push('rotate(90deg)')
  } else if (op === 'rotate180') {
    transforms.push('rotate(180deg)')
  } else if (op === 'rotate270') {
    transforms.push('rotate(270deg)')
  } else if (op === 'mirror') {
    transforms.push('scaleX(-1)')
  } else if (op === 'flip') {
    transforms.push('scaleY(-1)')
  } else if (op === 'custom') {
    if (state.rotate.angle) {
      transforms.push(`rotate(${state.rotate.angle}deg)`)
    }
    if (state.rotate.flipHorizontal) {
      transforms.push('scaleX(-1)')
    }
    if (state.rotate.flipVertical) {
      transforms.push('scaleY(-1)')
    }
  }
  if (!transforms.length) return {}
  return {
    transform: transforms.join(' '),
    transformOrigin: '50% 50%',
    transition: 'transform 0.2s ease-out'
  }
})

const getCropDisplayRect = () => {
  if (!hasCropRect.value) {
    return null
  }
  const scaleX = state.crop.displayWidth / state.crop.imageWidth
  const scaleY = state.crop.displayHeight / state.crop.imageHeight
  const left = state.crop.x * scaleX
  const top = state.crop.y * scaleY
  const width = state.crop.width * scaleX
  const height = state.crop.height * scaleY
  return {
    left,
    top,
    width,
    height,
    right: left + width,
    bottom: top + height
  }
}

const cropRectStyle = computed(() => {
  if (!hasCropRect.value) return {}
  const scaleX = state.crop.displayWidth / state.crop.imageWidth
  const scaleY = state.crop.displayHeight / state.crop.imageHeight
  const left = state.crop.x * scaleX
  const top = state.crop.y * scaleY
  const width = state.crop.width * scaleX
  const height = state.crop.height * scaleY
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  }
})

const updateCropRectByRatio = () => {
  if (!hasCropImage.value) return
  const ratioStr = state.crop.ratio || '1:1'
  const [wStr, hStr] = ratioStr.split(':')
  let ratioW = parseInt(wStr || '1', 10)
  let ratioH = parseInt(hStr || '1', 10)
  if (!Number.isFinite(ratioW) || ratioW <= 0) ratioW = 1
  if (!Number.isFinite(ratioH) || ratioH <= 0) ratioH = 1

  const baseW = state.crop.imageWidth
  const baseH = state.crop.imageHeight
  let targetW = baseW
  let targetH = Math.round((targetW * ratioH) / ratioW)
  if (targetH > baseH) {
    targetH = baseH
    targetW = Math.round((targetH * ratioW) / ratioH)
  }
  const x = Math.max(0, Math.round((baseW - targetW) / 2))
  const y = Math.max(0, Math.round((baseH - targetH) / 2))
  state.crop.x = x
  state.crop.y = y
  state.crop.width = targetW
  state.crop.height = targetH
}

const updateCropRectFromDisplay = (startX, startY, currentX, currentY) => {
  if (!hasCropImage.value) return
  if (startX === currentX && startY === currentY) return
  const minX = Math.max(0, Math.min(startX, currentX))
  const minY = Math.max(0, Math.min(startY, currentY))
  const maxX = Math.min(state.crop.displayWidth, Math.max(startX, currentX))
  const maxY = Math.min(state.crop.displayHeight, Math.max(startY, currentY))
  const widthDisplay = Math.max(1, maxX - minX)
  const heightDisplay = Math.max(1, maxY - minY)
  const scaleX = state.crop.imageWidth / state.crop.displayWidth
  const scaleY = state.crop.imageHeight / state.crop.displayHeight
  state.crop.x = Math.round(minX * scaleX)
  state.crop.y = Math.round(minY * scaleY)
  state.crop.width = Math.round(widthDisplay * scaleX)
  state.crop.height = Math.round(heightDisplay * scaleY)
}

const onCropImageLoaded = (event) => {
  const img = event?.target
  if (!img) return
  const rect = img.getBoundingClientRect()

  // ���ȶ�ȡԭʼͼƬ���ߴ磬���ɵ���� py ���ص�����Ϊ׼
  if (!state.crop.imageWidth || !state.crop.imageHeight) {
    state.crop.imageWidth = img.naturalWidth || rect.width || img.width || 0
    state.crop.imageHeight = img.naturalHeight || rect.height || img.height || 0
  }

  // ��¼��ǰ DOM ��ʾ�ߴ磬��ͼƬ�ߴ渺һ�����ڿռ������
  state.crop.displayWidth = rect.width || img.clientWidth || img.width || 0
  state.crop.displayHeight = rect.height || img.clientHeight || img.height || 0
  if (!state.crop.imageWidth || !state.crop.imageHeight) return

  if (state.crop.mode === 'ratio') {
    updateCropRectByRatio()
  } else if (!state.crop.width || !state.crop.height) {
    state.crop.x = 0
    state.crop.y = 0
    state.crop.width = state.crop.imageWidth
    state.crop.height = state.crop.imageHeight
  }
}

const onCropMouseDown = (event) => {
  if (event.button !== 0) return
  if (!hasCropImage.value || !cropPreviewRef.value) return
  const rect = cropPreviewRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  cropInteraction.dragging = true
  cropInteraction.startX = x
  cropInteraction.startY = y
  updateCropRectFromDisplay(x, y, x, y)
}

const onCropMouseMove = (event) => {
  if (!cropInteraction.dragging || !hasCropImage.value || !cropPreviewRef.value) return
  const rect = cropPreviewRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  updateCropRectFromDisplay(cropInteraction.startX, cropInteraction.startY, x, y)
}

const onCropMouseUp = () => {
  cropInteraction.dragging = false
  cropInteraction.handle = ''
}

const onCropHandleMouseDown = (position, event) => {
  if (event.button !== 0) return
  if (!hasCropImage.value || !cropPreviewRef.value || !hasCropRect.value) return
  const displayRect = getCropDisplayRect()
  if (!displayRect) return
  const hostRect = cropPreviewRef.value.getBoundingClientRect()
  const pointerX = event.clientX - hostRect.left
  const pointerY = event.clientY - hostRect.top

  // 以裁剪框对角作为锚点，当前指针为另一角，从而重用 updateCropRectFromDisplay 的逻辑
  let anchorX = displayRect.left
  let anchorY = displayRect.top
  if (position === 'nw') {
    anchorX = displayRect.right
    anchorY = displayRect.bottom
  } else if (position === 'ne') {
    anchorX = displayRect.left
    anchorY = displayRect.bottom
  } else if (position === 'sw') {
    anchorX = displayRect.right
    anchorY = displayRect.top
  } else if (position === 'se') {
    anchorX = displayRect.left
    anchorY = displayRect.top
  } else if (position === 'n') {
    anchorX = displayRect.left
    anchorY = displayRect.bottom
  } else if (position === 's') {
    anchorX = displayRect.left
    anchorY = displayRect.top
  } else if (position === 'w') {
    anchorX = displayRect.right
    anchorY = displayRect.top
  } else if (position === 'e') {
    anchorX = displayRect.left
    anchorY = displayRect.top
  }

  cropInteraction.dragging = true
  cropInteraction.startX = anchorX
  cropInteraction.startY = anchorY
  cropInteraction.handle = position
  updateCropRectFromDisplay(anchorX, anchorY, pointerX, pointerY)
}

watch(
  () => [state.crop.mode, state.crop.ratio],
  () => {
    if (!hasCropImage.value) return
    if (state.crop.mode === 'ratio') {
      updateCropRectByRatio()
    }
  }
)

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectImages = async (target) => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(imageFilter)
  if (files?.length) {
    state[target].files = files
  }
}

const selectSingleImage = async (target, field = 'file') => {
  if (target === 'crop' && field === 'file') {
    await selectCropImage()
    return
  }
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(imageFilter)
  if (files?.length) {
    const file = files[0]
    state[target][field] = file
    if (target === 'crop' && field === 'file') {
      state.crop.previewUrl = toFileUrl(file.path || file.filename || '')
      // 重置预览参数，在图片加载完成时重新计算
      state.crop.imageWidth = 0
      state.crop.imageHeight = 0
      state.crop.displayWidth = 0
      state.crop.displayHeight = 0
      state.crop.x = 0
      state.crop.y = 0
      state.crop.width = 0
      state.crop.height = 0
    }
  }
}

const selectCropImage = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(imageFilter)
  if (!files?.length) return

  const file = files[0]
  state.crop.file = file

  // 重置裁剪状态
  state.crop.previewUrl = ''
  state.crop.imageWidth = 0
  state.crop.imageHeight = 0
  state.crop.displayWidth = 0
  state.crop.displayHeight = 0
  state.crop.x = 0
  state.crop.y = 0
  state.crop.width = 0
  state.crop.height = 0

  try {
    const res = await window.pywebview.api.image_preview({
      file: file.path || file.filename
    })
    if (res?.code === 0 && res.preview) {
      state.crop.previewUrl = res.preview
      state.crop.imageWidth = res.width || 0
      state.crop.imageHeight = res.height || 0
    } else {
      ElMessage.error(res?.msg || '图片预览失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '图片预览失败')
  }
}

const selectWatermarkImage = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(imageFilter)
  if (files?.length) {
    state.watermark.watermarkImage = files[0]
  }
}

const clearWatermarkImage = () => {
  state.watermark.watermarkImage = null
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const currentDir = state[target].outputDir
  const dir = await window.pywebview.api.system_pySelectDirDialog(currentDir)
  if (dir) {
    state[target].outputDir = dir
  }
}

const ensureFilesReady = (target) => {
  if (!state[target].files.length) {
    ElMessage.warning('请先选择文件')
    return false
  }
  return true
}

const ensureSingleFile = (target) => {
  if (!state[target].file) {
    ElMessage.warning('请先选择文件')
    return false
  }
  return true
}

const pickPaths = (files = []) => files.map((item) => item?.path || item)

const runFormatConvert = async () => {
  if (!ensurePyReady() || !ensureFilesReady('format')) return
  state.loading = true
  try {
    const payload = {
      files: pickPaths(state.format.files),
      targetFormat: state.format.targetFormat,
      quality: state.format.quality,
      keepName: state.format.keepName,
      outputDir: state.format.outputDir
    }
    const res = await window.pywebview.api.image_format_convert(payload)
    if (res?.code === 0) {
      state.format.result = res.files || []
      state.format.generatedDir = res.outputDir || state.format.outputDir
      ElMessage.success(res.msg || '转换完成')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const runCompress = async () => {
  if (!ensurePyReady() || !ensureFilesReady('compress')) return
  state.loading = true
  try {
    const payload = {
      files: pickPaths(state.compress.files),
      mode: state.compress.mode,
      quality: state.compress.quality,
      targetSizeKB: state.compress.targetSizeKB,
      outputDir: state.compress.outputDir
    }
    const res = await window.pywebview.api.image_batch_compress(payload)
    if (res?.code === 0) {
      state.compress.result = res.items || []
      state.compress.generatedDir = res.outputDir || state.compress.outputDir
      ElMessage.success(res.msg || '压缩完成')
    } else {
      ElMessage.error(res?.msg || '压缩失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '压缩失败')
  } finally {
    state.loading = false
  }
}

const runConcat = async () => {
  if (!ensurePyReady() || !ensureFilesReady('concat')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.image_concat({
      files: pickPaths(state.concat.files),
      direction: state.concat.direction,
      columns: state.concat.columns,
      spacing: state.concat.spacing,
      align: state.concat.align,
      background: state.concat.background,
      outputFormat: state.concat.outputFormat,
      quality: state.concat.quality,
      outputDir: state.concat.outputDir
    })
    if (res?.code === 0) {
      state.concat.result = res.file || ''
      state.concat.outputDir = res.outputDir || state.concat.outputDir
      ElMessage.success(res.msg || '拼接完成')
    } else {
      ElMessage.error(res?.msg || '拼接失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '拼接失败')
  } finally {
    state.loading = false
  }
}

const runRename = async () => {
  if (!ensurePyReady() || !ensureFilesReady('rename')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.image_batch_rename({
      files: pickPaths(state.rename.files),
      mode: state.rename.mode,
      prefix: state.rename.prefix,
      suffix: state.rename.suffix,
      pattern: state.rename.pattern,
      digits: state.rename.digits,
      startIndex: state.rename.startIndex,
      keepExtension: state.rename.keepExtension,
      copyMode: state.rename.copyMode,
      outputDir: state.rename.outputDir,
      dryRun: state.rename.dryRun
    })
    if (res?.code === 0 || res?.success) {
      state.rename.operations = res.operations || []
      state.rename.skipped = res.skipped || []
      if (res.outputDir) {
        state.rename.outputDir = res.outputDir
      }
      state.rename.dryRun = !!res.dryRun
      ElMessage.success(res.msg || (state.rename.dryRun ? '预览生成' : '重命名完成'))
    } else {
      ElMessage.error(res?.msg || '重命名失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '重命名失败')
  } finally {
    state.loading = false
  }
}

const runExif = async () => {
  if (!ensurePyReady() || !ensureSingleFile('exif')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.image_get_exif({
      file: state.exif.file.path
    })
    if (res?.code === 0 || res?.success) {
      state.exif.data = res.exif || []
      state.exif.gps = res.gps || {}
      ElMessage.success(res.msg || '读取完成')
    } else {
      ElMessage.error(res?.msg || '读取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '读取失败')
  } finally {
    state.loading = false
  }
}

const runWatermark = async () => {
  if (!ensurePyReady() || !ensureFilesReady('watermark')) return
  if (state.watermark.watermarkType === 'text' && !state.watermark.text.trim()) {
    ElMessage.warning('请输入水印文字')
    return
  }
  if (state.watermark.watermarkType === 'image' && !state.watermark.watermarkImage) {
    ElMessage.warning('请选择水印图片')
    return
  }
  state.loading = true
  try {
    const payload = {
      files: pickPaths(state.watermark.files),
      watermarkType: state.watermark.watermarkType,
      text: state.watermark.text,
      fontSize: state.watermark.fontSize,
      color: state.watermark.color,
      opacity: state.watermark.opacity,
      position: state.watermark.position,
      tile: state.watermark.tile,
      tileSpacing: state.watermark.tileSpacing,
      rotation: state.watermark.rotation,
      watermarkImage: state.watermark.watermarkImage?.path,
      scalePercent: state.watermark.scalePercent,
      outputDir: state.watermark.outputDir
    }
    const res = await window.pywebview.api.image_add_watermark(payload)
    if (res?.code === 0) {
      state.watermark.result = res.files || []
      state.watermark.generatedDir = res.outputDir || state.watermark.outputDir
      ElMessage.success(res.msg || '水印已添加')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    state.loading = false
  }
}

const runCrop = async () => {
  if (!ensurePyReady()) return
  if (!state.crop.file) {
    ElMessage.warning('请选择需要裁剪的图片')
    return
  }
  state.loading = true
  try {
    const payload = {
      file: state.crop.file.path || state.crop.file,
      mode: state.crop.mode,
      x: state.crop.x,
      y: state.crop.y,
      width: state.crop.width,
      height: state.crop.height,
      ratio: state.crop.ratio,
      outputDir: state.crop.outputDir
    }
    const res = await window.pywebview.api.image_crop(payload)
    if (res?.code === 0) {
      state.crop.result = res.file || ''
      state.crop.generatedDir = res.outputDir || state.crop.outputDir
      ElMessage.success(res.msg || '裁剪完成')
    } else {
      ElMessage.error(res?.msg || '裁剪失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '裁剪失败')
  } finally {
    state.loading = false
  }
}

const runRotate = async () => {
  if (!ensurePyReady() || !ensureFilesReady('rotate')) return
  state.loading = true
  try {
    const payload = {
      files: pickPaths(state.rotate.files),
      operation: state.rotate.operation,
      angle: state.rotate.angle,
      flipHorizontal: state.rotate.flipHorizontal,
      flipVertical: state.rotate.flipVertical,
      outputDir: state.rotate.outputDir
    }
    const res = await window.pywebview.api.image_rotate_flip(payload)
    if (res?.code === 0) {
      state.rotate.result = res.files || []
      state.rotate.generatedDir = res.outputDir || state.rotate.outputDir
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    state.loading = false
  }
}

const runImagePdf = async () => {
  if (!ensurePyReady() || !ensureFilesReady('pdf')) return
  state.loading = true
  try {
    const payload = {
      files: pickPaths(state.pdf.files),
      pageSize: state.pdf.pageSize,
      customWidth: state.pdf.customWidth,
      customHeight: state.pdf.customHeight,
      perPage: state.pdf.perPage,
      margin: state.pdf.margin,
      outputName: state.pdf.outputName,
      outputDir: state.pdf.outputDir
    }
    const res = await window.pywebview.api.image_to_pdf(payload)
    if (res?.code === 0) {
      state.pdf.result = res.file || ''
      state.pdf.generatedDir = res.outputDir || state.pdf.outputDir
      ElMessage.success(res.msg || 'PDF 已生成')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  window.pywebview.api.system_pyOpenFile(path)
}

const openDir = (target) => {
  const dir = state[target].outputDir || state[target].generatedDir
  if (dir) {
    openPath(dir)
    return
  }
  const fallback = state[target].result?.[0]
  if (fallback) {
    openPath(fallback)
  }
}

const removeFile = (target, file) => {
  state[target].files = state[target].files.filter((item) => item !== file)
}
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="80%"
    append-to-body
    custom-class="image-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">IMAGE TOOLKIT</p>
          <h3>图片处理工具</h3>
          <p class="sub">格式转换、压缩、水印及 PDF 合成</p>
        </div>
      </div>
    </template>
    <div class="image-tool">
      <el-tabs v-model="state.activeTab" class="image-tabs">
        <el-tab-pane label="格式转换" name="convert">
          <section class="panel">
            <header>
              <h4>批量格式转换</h4>
              <p>支持 PNG / JPG / WEBP / TIFF / BMP 互转</p>
            </header>
            <FileSelector
              label="源文件"
              :files="state.format.files"
              :removable="true"
              @select="selectImages('format')"
              @remove="(file) => removeFile('format', file)"
            />
            <el-form :model="state.format" label-width="110px" class="form-block">
              <el-form-item label="目标格式">
                <el-select v-model="state.format.targetFormat" style="width: 200px">
                  <el-option label="PNG" value="png" />
                  <el-option label="JPG" value="jpg" />
                  <el-option label="GIF" value="gif" />
                  <el-option label="SVG" value="svg" />
                  <el-option label="WEBP" value="webp" />
                  <el-option label="TIFF" value="tiff" />
                </el-select>
              </el-form-item>
              <el-form-item label="画质 / 质量">
                <el-slider v-model="state.format.quality" :min="40" :max="100" show-input />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.format.outputDir" placeholder="留空自动创建" readonly />
                  <el-button @click="selectDir('format')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.format.keepName">保留原文件名</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runFormatConvert">开始转换</el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.format.result.length"
              title="转换输出"
              :items="state.format.result.map((path) => ({ path }))"
              :columns="[{ label: '文件路径', prop: 'path' }]"
            >
              <template #actions>
                <el-button text type="primary" @click="openDir('format')">
                  打开目录
                </el-button>
              </template>
            </ResultTable>
          </section>
        </el-tab-pane>

        <el-tab-pane label="批量压缩" name="compress">
          <section class="panel">
            <header>
              <h4>体积压缩</h4>
              <p>质量或目标大小两种模式，适合分享或归档</p>
            </header>
            <FileSelector
              label="图片列表"
              :files="state.compress.files"
              :removable="true"
              @select="selectImages('compress')"
              @remove="(file) => removeFile('compress', file)"
            />
            <el-form :model="state.compress" label-width="120px" class="form-block">
              <el-form-item label="压缩模式">
                <el-radio-group v-model="state.compress.mode">
                  <el-radio-button label="quality">按质量</el-radio-button>
                  <el-radio-button label="size">目标体积</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.compress.mode === 'quality'" label="质量">
                <el-slider v-model="state.compress.quality" :min="40" :max="95" show-input />
              </el-form-item>
              <el-form-item v-else label="目标大小 (KB)">
                <el-input-number v-model="state.compress.targetSizeKB" :min="32" :max="8192" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.compress.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('compress')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCompress">开始压缩</el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.compress.result.length"
              title="压缩结果"
              :items="state.compress.result"
              :columns="[
                { label: '原文件', prop: 'source' },
                { label: '输出文件', prop: 'output' },
                { label: '原大小', prop: 'originalSize', width: 120 },
                { label: '新大小', prop: 'compressedSize', width: 120 }
              ]"
            >
              <template #actions>
                <el-button text type="primary" @click="openDir('compress')">打开目录</el-button>
              </template>
            </ResultTable>
          </section>
        </el-tab-pane>

        <el-tab-pane label="批量水印" name="watermark">
          <section class="panel">
            <header>
              <h4>批量添加水印</h4>
              <p>支持文字与图片水印，九宫格定位与透明度控制</p>
            </header>
            <FileSelector
              label="待处理图片"
              :files="state.watermark.files"
              :removable="true"
              @select="selectImages('watermark')"
              @remove="(file) => removeFile('watermark', file)"
            />
            <el-form :model="state.watermark" label-width="110px" class="form-block">
              <el-form-item label="水印类型">
                <el-radio-group v-model="state.watermark.watermarkType">
                  <el-radio-button label="text">文字</el-radio-button>
                  <el-radio-button label="image">图片</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <template v-if="state.watermark.watermarkType === 'text'">
                <el-form-item label="文字内容">
                  <el-input
                    v-model="state.watermark.text"
                    placeholder="输入水印文字，可换行"
                    type="textarea"
                    :rows="3"
                  />
                </el-form-item>
                <div class="watermark-config">
                  <el-form-item label="字号">
                    <el-input-number v-model="state.watermark.fontSize" :min="8" :max="200" />
                  </el-form-item>
                  <el-form-item label="颜色">
                    <el-color-picker v-model="state.watermark.color" show-alpha />
                  </el-form-item>
                  <el-form-item label="透明度 (%)">
                    <el-slider v-model="state.watermark.opacity" :min="5" :max="100" show-input />
                  </el-form-item>
                </div>
              </template>
              <template v-else>
                <el-form-item label="水印图片">
                  <div class="field-row">
                    <el-input :model-value="state.watermark.watermarkImage?.path || ''" placeholder="点击选择图片" readonly />
                    <el-button @click="selectWatermarkImage">选择</el-button>
                    <el-button text type="danger" @click="clearWatermarkImage">清除</el-button>
                  </div>
                </el-form-item>
                <el-form-item label="尺寸比例 (%)">
                  <el-slider v-model="state.watermark.scalePercent" :min="5" :max="80" show-input />
                </el-form-item>
                <el-form-item label="透明度 (%)">
                  <el-slider v-model="state.watermark.opacity" :min="5" :max="100" show-input />
                </el-form-item>
              </template>
              <el-form-item label="平铺 / 间距">
                <div class="field-row field-row--wrap">
                  <el-switch
                    v-model="state.watermark.tile"
                    active-text="按间距平铺"
                    inactive-text="单个水印"
                  />
                  <el-input-number
                    v-model="state.watermark.tileSpacing"
                    :min="20"
                    :max="600"
                    :step="10"
                    :disabled="!state.watermark.tile"
                  />
                  <span>px</span>
                </div>
              </el-form-item>
              <el-form-item label="旋转角度">
                <el-slider
                  v-model="state.watermark.rotation"
                  :min="-90"
                  :max="90"
                  :step="1"
                  show-input
                />
              </el-form-item>              <el-form-item label="位置">
                <el-select v-model="state.watermark.position" style="width: 220px">
                  <el-option label="左上角" value="top-left" />
                  <el-option label="右上角" value="top-right" />
                  <el-option label="居中" value="center" />
                  <el-option label="左下角" value="bottom-left" />
                  <el-option label="右下角" value="bottom-right" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.watermark.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('watermark')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runWatermark">开始处理</el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.watermark.result.length"
              title="输出文件"
              :items="state.watermark.result.map((path) => ({ path }))"
              :columns="[{ label: '文件路径', prop: 'path' }]"
            >
              <template #actions>
                <el-button text type="primary" @click="openDir('watermark')">打开目录</el-button>
              </template>
            </ResultTable>
          </section>
        </el-tab-pane>

        <el-tab-pane label="裁剪工具" name="crop">
          <section class="panel">
            <header>
              <h4>快速裁剪</h4>
              <p>支持自定义坐标或按比例裁剪</p>
            </header>
            <el-form :model="state.crop" label-width="120px" class="form-block">
              <el-form-item label="源图片">
                <div class="field-row">
                  <el-input :model-value="state.crop.file?.path || ''" placeholder="请选择图片" readonly />
                  <el-button @click="selectSingleImage('crop')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="模式">
                <el-radio-group v-model="state.crop.mode">
                  <el-radio-button label="custom">自定义</el-radio-button>
                  <el-radio-button label="ratio">按比例</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <template v-if="state.crop.mode === 'custom'">
                <div class="field-row field-row--wrap">
                  <el-form-item label="X">
                    <el-input-number v-model="state.crop.x" :min="0" />
                  </el-form-item>
                  <el-form-item label="Y">
                    <el-input-number v-model="state.crop.y" :min="0" />
                  </el-form-item>
                  <el-form-item label="宽度">
                    <el-input-number v-model="state.crop.width" :min="10" />
                  </el-form-item>
                  <el-form-item label="高度">
                    <el-input-number v-model="state.crop.height" :min="10" />
                  </el-form-item>
                </div>
              </template>
              <el-form-item v-else label="比例">
                <el-select v-model="state.crop.ratio" style="width: 220px">
                  <el-option label="1:1 (方形)" value="1:1" />
                  <el-option label="4:3" value="4:3" />
                  <el-option label="3:2" value="3:2" />
                  <el-option label="16:9" value="16:9" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.crop.file" label="预览裁剪">
                <div class="crop-preview">
                  <div
                    ref="cropPreviewRef"
                    class="crop-preview-inner"
                    @mousedown.prevent="onCropMouseDown"
                    @mousemove.prevent="onCropMouseMove"
                    @mouseup.prevent="onCropMouseUp"
                    @mouseleave="onCropMouseUp"
                  >
                    <img
                      v-if="state.crop.previewUrl"
                      :src="state.crop.previewUrl"
                      alt="预览图片"
                      class="crop-preview-image"
                      @load="onCropImageLoaded"
                    />
                    <div
                      v-if="hasCropRect"
                      class="crop-preview-rect"
                      :style="cropRectStyle"
                    >
                      <div
                        class="crop-handle crop-handle-nw"
                        @mousedown.stop.prevent="onCropHandleMouseDown('nw', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-ne"
                        @mousedown.stop.prevent="onCropHandleMouseDown('ne', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-sw"
                        @mousedown.stop.prevent="onCropHandleMouseDown('sw', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-se"
                        @mousedown.stop.prevent="onCropHandleMouseDown('se', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-n"
                        @mousedown.stop.prevent="onCropHandleMouseDown('n', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-s"
                        @mousedown.stop.prevent="onCropHandleMouseDown('s', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-w"
                        @mousedown.stop.prevent="onCropHandleMouseDown('w', $event)"
                      />
                      <div
                        class="crop-handle crop-handle-e"
                        @mousedown.stop.prevent="onCropHandleMouseDown('e', $event)"
                      />
                    </div>
                  </div>
                  <p class="crop-preview-hint">在图片上拖动绘制裁剪区域，坐标会自动填入上方字段</p>
                </div>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.crop.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('crop')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCrop">开始裁剪</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.crop.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已输出：
                <a class="link" @click.prevent="openPath(state.crop.result)">{{ state.crop.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="旋转 / 翻转" name="rotate">
          <section class="panel">
            <header>
              <h4>方向调整</h4>
              <p>旋转 90/180/270°，或镜像 / 垂直翻转</p>
            </header>
            <FileSelector
              label="图片列表"
              :files="state.rotate.files"
              :removable="true"
              @select="selectImages('rotate')"
              @remove="(file) => removeFile('rotate', file)"
            />
            <el-form :model="state.rotate" label-width="120px" class="form-block">
              <el-form-item label="操作">
                <el-select v-model="state.rotate.operation" style="width: 240px">
                  <el-option label="旋转 90°" value="rotate90" />
                  <el-option label="旋转 180°" value="rotate180" />
                  <el-option label="旋转 270°" value="rotate270" />
                  <el-option label="水平镜像" value="mirror" />
                  <el-option label="垂直翻转" value="flip" />
                  <el-option label="自定义角度 / 翻转" value="custom" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.rotate.operation === 'custom'" label="旋转角度">
                <el-slider v-model="state.rotate.angle" :min="-180" :max="180" show-input />
              </el-form-item>
              <el-form-item v-if="state.rotate.operation === 'custom'" label="翻转">
                <el-checkbox v-model="state.rotate.flipHorizontal">水平</el-checkbox>
                <el-checkbox v-model="state.rotate.flipVertical">垂直</el-checkbox>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.rotate.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('rotate')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runRotate">开始处理</el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.rotate.result.length"
              title="处理结果"
              :items="state.rotate.result.map((path) => ({ path }))"
              :columns="[{ label: '文件路径', prop: 'path' }]"
            >
              <template #actions>
                <el-button text type="primary" @click="openDir('rotate')">打开目录</el-button>
              </template>
            </ResultTable>
          </section>
        </el-tab-pane>

        <el-tab-pane label="图片转 PDF" name="pdf">
          <section class="panel">
            <header>
              <h4>合成 PDF</h4>
              <p>拖入多张图片，设置纸张与排版后输出 PDF</p>
            </header>
            <FileSelector
              label="图片列表"
              :files="state.pdf.files"
              :removable="true"
              @select="selectImages('pdf')"
              @remove="(file) => removeFile('pdf', file)"
            />
            <el-form :model="state.pdf" label-width="120px" class="form-block">
              <el-form-item label="页面尺寸">
                <el-select v-model="state.pdf.pageSize" style="width: 220px">
                  <el-option label="A4" value="a4" />
                  <el-option label="A5" value="a5" />
                  <el-option label="Letter" value="letter" />
                  <el-option label="自定义" value="custom" />
                </el-select>
              </el-form-item>
              <div v-if="state.pdf.pageSize === 'custom'" class="field-row">
                <el-form-item label="宽 (px)">
                  <el-input-number v-model="state.pdf.customWidth" :min="600" :max="6000" />
                </el-form-item>
                <el-form-item label="高 (px)">
                  <el-input-number v-model="state.pdf.customHeight" :min="600" :max="6000" />
                </el-form-item>
              </div>
              <el-form-item label="每页布局">
                <el-radio-group v-model="state.pdf.perPage">
                  <el-radio-button :label="1">1 / 页</el-radio-button>
                  <el-radio-button :label="2">2 / 页</el-radio-button>
                  <el-radio-button :label="4">4 / 页</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="边距 (px)">
                <el-input-number v-model="state.pdf.margin" :min="10" :max="300" />
              </el-form-item>
              <el-form-item label="输出名称">
                <el-input v-model="state.pdf.outputName" placeholder="可选，例如 merge.pdf" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.pdf.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('pdf')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runImagePdf">生成 PDF</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.pdf.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已输出：
                <a class="link" @click.prevent="openPath(state.pdf.result)">{{ state.pdf.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>
        <el-tab-pane label="高级批量" name="advanced">
          <section class="panel advanced-grid">
            <div class="advanced-card">
              <header>
                <h4>图片拼接</h4>
                <p>批量横向 / 纵向 / 网格拼接，支持自定义背景与间距</p>
              </header>
              <el-form :model="state.concat" label-width="110px">
                <el-form-item label="待处理">
                  <div class="field-row">
                    <el-button @click="selectImages('concat')">添加图片</el-button>
                    <el-tag v-if="state.concat.files.length" type="info" effect="plain">
                      已选 {{ state.concat.files.length }} 个文件
                    </el-tag>
                    <el-tag v-else type="warning" effect="plain">尚未选择</el-tag>
                  </div>
                </el-form-item>
                <el-form-item label="排列方式">
                  <el-radio-group v-model="state.concat.direction">
                    <el-radio-button label="horizontal">横向</el-radio-button>
                    <el-radio-button label="vertical">纵向</el-radio-button>
                    <el-radio-button label="grid">网格</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-if="state.concat.direction === 'grid'" label="列数">
                  <el-input-number v-model="state.concat.columns" :min="1" :max="6" />
                </el-form-item>
                <el-form-item label="对齐 / 间距">
                  <div class="field-row field-row--wrap">
                    <el-select v-model="state.concat.align" style="width: 140px">
                      <el-option label="顶部" value="top" />
                      <el-option label="居中" value="center" />
                      <el-option label="底部" value="bottom" />
                    </el-select>
                    <el-input-number v-model="state.concat.spacing" :min="0" :max="200" />
                  </div>
                </el-form-item>
                <el-form-item label="背景颜色">
                  <el-color-picker v-model="state.concat.background" />
                </el-form-item>
                <el-form-item label="输出格式">
                  <div class="field-row">
                    <el-select v-model="state.concat.outputFormat" style="width: 120px">
                      <el-option label="PNG" value="png" />
                      <el-option label="JPG" value="jpg" />
                      <el-option label="WEBP" value="webp" />
                    </el-select>
                    <el-input-number v-model="state.concat.quality" :min="30" :max="100" />
                  </div>
                </el-form-item>
                <el-form-item label="输出目录">
                  <div class="field-row">
                    <el-input v-model="state.concat.outputDir" placeholder="留空自动创建" readonly />
                    <el-button @click="selectDir('concat')">选择目录</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="state.loading" @click="runConcat">
                    执行拼接
                  </el-button>
                </el-form-item>
              </el-form>
              <div v-if="state.concat.result" class="result-block">
                <p class="result-title">输出文件</p>
                <el-tag type="info" effect="plain" @click="openPath(state.concat.result)">
                  {{ state.concat.result }}
                </el-tag>
              </div>
            </div>
            <div class="advanced-card">
              <header>
                <h4>批量重命名</h4>
                <p>支持序号 / 时间戳 / 自定义模板，可预览再执行</p>
              </header>
              <el-form :model="state.rename" label-width="110px">
                <el-form-item label="待处理">
                  <div class="field-row">
                    <el-button @click="selectImages('rename')">添加图片</el-button>
                    <el-tag v-if="state.rename.files.length" effect="plain" type="info">
                      已选 {{ state.rename.files.length }} 个
                    </el-tag>
                    <el-tag v-else effect="plain" type="warning">尚未选择</el-tag>
                  </div>
                </el-form-item>
                <el-form-item label="模式">
                  <el-radio-group v-model="state.rename.mode" size="small">
                    <el-radio-button label="sequence">序号</el-radio-button>
                    <el-radio-button label="timestamp">时间戳</el-radio-button>
                    <el-radio-button label="custom">自定义</el-radio-button>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-if="state.rename.mode === 'custom'" label="模板">
                  <el-input
                    v-model="state.rename.pattern"
                    placeholder="可使用 {name} {index} {timestamp}"
                  />
                </el-form-item>
                <el-form-item v-else label="前后缀">
                  <div class="field-row field-row--wrap">
                    <el-input v-model="state.rename.prefix" placeholder="前缀" />
                    <el-input v-model="state.rename.suffix" placeholder="后缀" />
                  </div>
                </el-form-item>
                <el-form-item label="序号配置">
                  <div class="field-row field-row--wrap">
                    <el-input-number v-model="state.rename.startIndex" :min="1" />
                    <el-input-number v-model="state.rename.digits" :min="2" :max="6" />
                  </div>
                </el-form-item>
                <el-form-item label="选项">
                  <div class="toggle-row">
                    <el-checkbox v-model="state.rename.keepExtension">保留原扩展名</el-checkbox>
                    <el-checkbox v-model="state.rename.copyMode">复制到新目录</el-checkbox>
                    <el-checkbox v-model="state.rename.dryRun">仅预览</el-checkbox>
                  </div>
                </el-form-item>
                <el-form-item label="输出目录">
                  <div class="field-row">
                    <el-input v-model="state.rename.outputDir" placeholder="可选" readonly />
                    <el-button @click="selectDir('rename')">选择目录</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="state.loading" @click="runRename">
                    {{ state.rename.dryRun ? '生成预览' : '开始重命名' }}
                  </el-button>
                </el-form-item>
              </el-form>
              <div v-if="state.rename.operations.length" class="result-block">
                <p class="result-title">
                  {{ state.rename.dryRun ? '预览结果' : '重命名记录' }}（仅展示前 8 条）
                </p>
                <el-table :data="state.rename.operations.slice(0, 8)" size="small" border>
                  <el-table-column prop="from" label="原文件" show-overflow-tooltip />
                  <el-table-column prop="to" label="新文件" show-overflow-tooltip />
                </el-table>
              </div>
            </div>
          </section>
          <section class="panel">
            <header>
              <h4>EXIF 信息查看</h4>
              <p>读取拍摄时间、相机型号、GPS 信息等元数据</p>
            </header>
            <el-form :model="state.exif" label-width="110px">
              <el-form-item label="图片文件">
                <div class="field-row">
                  <el-button @click="selectSingleImage('exif')">选择图片</el-button>
                  <el-tag v-if="state.exif.file" effect="plain" type="info">
                    {{ state.exif.file.filename }}
                  </el-tag>
                  <el-tag v-else effect="plain" type="warning">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runExif">
                  读取 EXIF
                </el-button>
              </el-form-item>
            </el-form>
            <el-table
              v-if="state.exif.data.length"
              :data="state.exif.data"
              border
              height="240"
              size="small"
            >
              <el-table-column prop="tag" label="属性" width="200" />
              <el-table-column prop="value" label="内容" show-overflow-tooltip />
            </el-table>
            <el-descriptions
              v-if="Object.keys(state.exif.gps).length"
              title="GPS 信息"
              size="small"
              border
              :column="2"
            >
              <el-descriptions-item v-for="(value, key) in state.exif.gps" :key="key" :label="key">
                {{ value }}
              </el-descriptions-item>
            </el-descriptions>
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 使用全局深空玻璃主题样式 */


.form-block {
  margin-top: 18px;
}

.watermark-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

/* 裁剪预览 */
.crop-preview {
  margin-top: 8px;
}

.crop-preview-inner {
  position: relative;
  display: inline-block;
  max-width: 100%;
  border-radius: var(--ppx-radius-sm);
  overflow: hidden;
  background: var(--ppx-bg-ink);
}

.crop-preview-image {
  display: block;
  max-width: 100%;
}

.crop-preview-rect {
  position: absolute;
  border: 2px solid var(--ppx-neon-blue);
  box-shadow: 0 0 0 1px rgba(14, 165, 164, 0.35);
  pointer-events: auto;
}

.crop-handle {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--ppx-bg-surface);
  border: 1px solid var(--ppx-neon-blue);
  box-shadow: 0 0 0 1px rgba(14, 165, 164, 0.3);
}

.crop-handle-nw {
  top: -4px;
  left: -4px;
  cursor: nwse-resize;
}

.crop-handle-ne {
  top: -4px;
  right: -4px;
  cursor: nesw-resize;
}

.crop-handle-sw {
  bottom: -4px;
  left: -4px;
  cursor: nesw-resize;
}

.crop-handle-se {
  bottom: -4px;
  right: -4px;
  cursor: nwse-resize;
}

.crop-handle-n {
  top: -4px;
  left: 50%;
  margin-left: -4px;
  cursor: ns-resize;
}

.crop-handle-s {
  bottom: -4px;
  left: 50%;
  margin-left: -4px;
  cursor: ns-resize;
}

.crop-handle-w {
  left: -4px;
  top: 50%;
  margin-top: -4px;
  cursor: ew-resize;
}

.crop-handle-e {
  right: -4px;
  top: 50%;
  margin-top: -4px;
  cursor: ew-resize;
}

.crop-preview-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}

.toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* 高级批量处理 */
.advanced-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.advanced-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  padding: 16px;
  background: var(--ppx-glass-bg);
}

.advanced-card:hover {
  border-color: var(--ppx-glass-border-hover);
  background: var(--ppx-glass-bg-hover);
}
</style>
