<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

import FileSelector from '../../shared/FileSelector.vue'
import ResultTable from '../../shared/ResultTable.vue'

const props = defineProps({
  supportedFormats: {
    type: Object,
    required: true
  }
})

const PRESETS = [
  {
    value: 'one-inch',
    label: '1 寸',
    detail: '295 × 413 px',
    width: 295,
    height: 413,
    dpi: 300
  },
  {
    value: 'two-inch',
    label: '2 寸',
    detail: '413 × 579 px',
    width: 413,
    height: 579,
    dpi: 300
  },
  {
    value: 'square',
    label: '正方形',
    detail: '1:1 · 保持像素',
    ratioWidth: 1,
    ratioHeight: 1
  }
]

const RATIO_OPTIONS = [
  { label: '1:1', value: '1:1' },
  { label: '4:3', value: '4:3' },
  { label: '3:4', value: '3:4' },
  { label: '3:2', value: '3:2' },
  { label: '2:3', value: '2:3' },
  { label: '16:9', value: '16:9' },
  { label: '9:16', value: '9:16' },
  { label: '自定义', value: 'custom' }
]

const previewHostRef = ref(null)
const loading = ref(false)
const previewLoading = ref(false)

const form = reactive({
  file: null,
  previewUrl: '',
  imageWidth: 0,
  imageHeight: 0,
  mode: 'preset',
  preset: 'one-inch',
  exactWidth: 800,
  exactHeight: 600,
  ratioPreset: '1:1',
  ratioWidth: 5,
  ratioHeight: 4,
  x: 0,
  y: 0,
  width: 0,
  height: 0,
  outputDir: '',
  generatedDir: '',
  result: '',
  resultWidth: 0,
  resultHeight: 0
})

const interaction = reactive({
  active: false,
  action: '',
  handle: '',
  pointerId: null,
  anchorX: 0,
  anchorY: 0,
  offsetX: 0,
  offsetY: 0,
  moved: false,
  startRect: null
})

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))
const toPositiveNumber = (value, fallback = 1) => {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : fallback
}

const selectedFiles = computed(() => (form.file ? [form.file] : []))
const hasImage = computed(() => Boolean(form.previewUrl) && form.imageWidth > 0 && form.imageHeight > 0)
const hasSelection = computed(() => hasImage.value && form.width > 0 && form.height > 0)
const activePreset = computed(() => PRESETS.find((item) => item.value === form.preset) || PRESETS[0])

const activeRatio = computed(() => {
  if (form.mode === 'free') return null

  let width = 1
  let height = 1
  if (form.mode === 'preset') {
    width = activePreset.value.ratioWidth || activePreset.value.width
    height = activePreset.value.ratioHeight || activePreset.value.height
  } else if (form.mode === 'size') {
    width = form.exactWidth
    height = form.exactHeight
  } else if (form.ratioPreset === 'custom') {
    width = form.ratioWidth
    height = form.ratioHeight
  } else {
    const parts = String(form.ratioPreset).split(':')
    width = parts[0]
    height = parts[1]
  }

  const ratio = toPositiveNumber(width) / toPositiveNumber(height)
  return Number.isFinite(ratio) && ratio > 0 ? ratio : null
})

const outputSize = computed(() => {
  if (form.mode === 'size') {
    return {
      width: Math.round(toPositiveNumber(form.exactWidth)),
      height: Math.round(toPositiveNumber(form.exactHeight)),
      dpi: null
    }
  }
  if (form.mode === 'preset' && activePreset.value.width && activePreset.value.height) {
    return {
      width: activePreset.value.width,
      height: activePreset.value.height,
      dpi: activePreset.value.dpi || null
    }
  }
  return null
})

const selectionStyle = computed(() => {
  if (!hasSelection.value) return {}
  return {
    left: String((form.x / form.imageWidth) * 100) + '%',
    top: String((form.y / form.imageHeight) * 100) + '%',
    width: String((form.width / form.imageWidth) * 100) + '%',
    height: String((form.height / form.imageHeight) * 100) + '%'
  }
})

const selectionSizeLabel = computed(() => Math.round(form.width) + ' × ' + Math.round(form.height) + ' px')

const outputLabel = computed(() => {
  if (!hasSelection.value) return '请先在图片上设置裁剪区域'
  if (outputSize.value) {
    return selectionSizeLabel.value + ' → 输出 ' + outputSize.value.width + ' × ' + outputSize.value.height + ' px'
  }
  return selectionSizeLabel.value + ' · 保持裁剪区域像素'
})

const resultItems = computed(() => {
  if (!form.result) return []
  return [
    {
      path: form.result,
      size: form.resultWidth && form.resultHeight ? form.resultWidth + ' × ' + form.resultHeight + ' px' : ''
    }
  ]
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const pickPath = (file) => file?.path || file

const setCropRect = ({ x, y, width, height }) => {
  if (!form.imageWidth || !form.imageHeight) return
  const safeWidth = clamp(Number(width) || 1, 1, form.imageWidth)
  const safeHeight = clamp(Number(height) || 1, 1, form.imageHeight)
  form.width = safeWidth
  form.height = safeHeight
  form.x = clamp(Number(x) || 0, 0, form.imageWidth - safeWidth)
  form.y = clamp(Number(y) || 0, 0, form.imageHeight - safeHeight)
}

const initializeCrop = () => {
  if (!form.imageWidth || !form.imageHeight) return
  const maxWidth = form.imageWidth * 0.88
  const maxHeight = form.imageHeight * 0.88
  let width = maxWidth
  let height = maxHeight

  if (activeRatio.value) {
    height = width / activeRatio.value
    if (height > maxHeight) {
      height = maxHeight
      width = height * activeRatio.value
    }
  }

  setCropRect({
    x: (form.imageWidth - width) / 2,
    y: (form.imageHeight - height) / 2,
    width,
    height
  })
}

const fitCropToRatio = () => {
  if (!hasImage.value || !activeRatio.value) return
  if (!hasSelection.value) {
    initializeCrop()
    return
  }

  const centerX = form.x + form.width / 2
  const centerY = form.y + form.height / 2
  const area = Math.max(1, form.width * form.height)
  let width = Math.sqrt(area * activeRatio.value)
  let height = width / activeRatio.value
  const scale = Math.min(1, form.imageWidth / width, form.imageHeight / height)
  width *= scale
  height *= scale

  setCropRect({
    x: centerX - width / 2,
    y: centerY - height / 2,
    width,
    height
  })
}

const normalizeManualRect = (changedField = '') => {
  if (!hasImage.value) return
  let width = Math.max(1, Math.round(toPositiveNumber(form.width)))
  let height = Math.max(1, Math.round(toPositiveNumber(form.height)))

  if (activeRatio.value) {
    if (changedField === 'height') {
      width = Math.max(1, Math.round(height * activeRatio.value))
    } else {
      height = Math.max(1, Math.round(width / activeRatio.value))
    }
  }

  const scale = Math.min(1, form.imageWidth / width, form.imageHeight / height)
  width = Math.max(1, Math.floor(width * scale))
  height = Math.max(1, Math.floor(height * scale))
  const x = clamp(Math.round(Number(form.x) || 0), 0, form.imageWidth - width)
  const y = clamp(Math.round(Number(form.y) || 0), 0, form.imageHeight - height)
  setCropRect({ x, y, width, height })
}

const clearImage = () => {
  form.file = null
  form.previewUrl = ''
  form.imageWidth = 0
  form.imageHeight = 0
  form.x = 0
  form.y = 0
  form.width = 0
  form.height = 0
  form.result = ''
  form.resultWidth = 0
  form.resultHeight = 0
}

const selectImage = async () => {
  if (!ensurePyReady()) return
  try {
    const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
    if (!files?.length) return

    form.file = files[0]
    form.previewUrl = ''
    form.imageWidth = 0
    form.imageHeight = 0
    form.result = ''
    previewLoading.value = true

    const {
      ok,
      data: res,
      message
    } = await pyCall('image_preview', {
      file: pickPath(form.file),
      maxSize: 2048
    })
    if (!ok) {
      clearImage()
      ElMessage.error(message || '图片预览加载失败')
      return
    }
    form.imageWidth = Number(res.width) || 0
    form.imageHeight = Number(res.height) || 0
    form.previewUrl = res.preview || ''
  } catch (error) {
    clearImage()
    ElMessage.error(error?.message || '图片预览加载失败')
  } finally {
    previewLoading.value = false
  }
}

const onPreviewLoaded = (event) => {
  if (!form.imageWidth || !form.imageHeight) {
    form.imageWidth = event.target?.naturalWidth || 0
    form.imageHeight = event.target?.naturalHeight || 0
  }
  initializeCrop()
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) form.outputDir = dir
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const openDir = () => {
  const path = form.generatedDir || form.outputDir || form.result
  if (path) openPath(path)
}

const getPointFromEvent = (event) => {
  const host = previewHostRef.value
  if (!host) return null
  const bounds = host.getBoundingClientRect()
  if (!bounds.width || !bounds.height) return null
  return {
    x: clamp(((event.clientX - bounds.left) / bounds.width) * form.imageWidth, 0, form.imageWidth),
    y: clamp(((event.clientY - bounds.top) / bounds.height) * form.imageHeight, 0, form.imageHeight)
  }
}

const minCropSize = () => Math.max(1, Math.min(10, Math.floor(Math.min(form.imageWidth, form.imageHeight) / 100)))

const getDirection = (pointValue, anchorValue, total) => {
  if (pointValue > anchorValue) return 1
  if (pointValue < anchorValue) return -1
  return anchorValue > total / 2 ? -1 : 1
}

const rectFromCorner = (anchor, point, ratio = null) => {
  const directionX = getDirection(point.x, anchor.x, form.imageWidth)
  const directionY = getDirection(point.y, anchor.y, form.imageHeight)
  const maxWidth = directionX > 0 ? form.imageWidth - anchor.x : anchor.x
  const maxHeight = directionY > 0 ? form.imageHeight - anchor.y : anchor.y
  const minimum = minCropSize()
  let width = Math.abs(point.x - anchor.x)
  let height = Math.abs(point.y - anchor.y)

  if (ratio) {
    const pointerWidth = width / Math.max(height, 0.0001) > ratio ? width : height * ratio
    const allowedWidth = Math.max(1, Math.min(maxWidth, maxHeight * ratio))
    width = clamp(pointerWidth, Math.min(minimum, allowedWidth), allowedWidth)
    height = width / ratio
  } else {
    width = clamp(width, Math.min(minimum, maxWidth), Math.max(1, maxWidth))
    height = clamp(height, Math.min(minimum, maxHeight), Math.max(1, maxHeight))
  }

  return {
    x: directionX > 0 ? anchor.x : anchor.x - width,
    y: directionY > 0 ? anchor.y : anchor.y - height,
    width,
    height
  }
}

const resizeCrop = (handle, point) => {
  const start = interaction.startRect
  if (!start) return
  const ratio = activeRatio.value

  if (handle.length === 2) {
    const anchor = {
      x: handle.includes('w') ? start.x + start.width : start.x,
      y: handle.includes('n') ? start.y + start.height : start.y
    }
    setCropRect(rectFromCorner(anchor, point, ratio))
    return
  }

  const minimum = minCropSize()
  if (!ratio) {
    let left = start.x
    let top = start.y
    let right = start.x + start.width
    let bottom = start.y + start.height
    if (handle === 'w') left = clamp(point.x, 0, right - minimum)
    if (handle === 'e') right = clamp(point.x, left + minimum, form.imageWidth)
    if (handle === 'n') top = clamp(point.y, 0, bottom - minimum)
    if (handle === 's') bottom = clamp(point.y, top + minimum, form.imageHeight)
    setCropRect({
      x: left,
      y: top,
      width: right - left,
      height: bottom - top
    })
    return
  }

  if (handle === 'e' || handle === 'w') {
    const anchorX = handle === 'w' ? start.x + start.width : start.x
    const centerY = start.y + start.height / 2
    const horizontalLimit = handle === 'w' ? anchorX : form.imageWidth - anchorX
    const verticalLimit = 2 * Math.min(centerY, form.imageHeight - centerY) * ratio
    const allowedWidth = Math.max(1, Math.min(horizontalLimit, verticalLimit))
    const width = clamp(Math.abs(point.x - anchorX), Math.min(minimum, allowedWidth), allowedWidth)
    const height = width / ratio
    setCropRect({
      x: handle === 'w' ? anchorX - width : anchorX,
      y: centerY - height / 2,
      width,
      height
    })
    return
  }

  const anchorY = handle === 'n' ? start.y + start.height : start.y
  const centerX = start.x + start.width / 2
  const verticalLimit = handle === 'n' ? anchorY : form.imageHeight - anchorY
  const horizontalLimit = (2 * Math.min(centerX, form.imageWidth - centerX)) / ratio
  const allowedHeight = Math.max(1, Math.min(verticalLimit, horizontalLimit))
  const height = clamp(Math.abs(point.y - anchorY), Math.min(minimum, allowedHeight), allowedHeight)
  const width = height * ratio
  setCropRect({
    x: centerX - width / 2,
    y: handle === 'n' ? anchorY - height : anchorY,
    width,
    height
  })
}

const onStagePointerDown = (event) => {
  if (!hasImage.value || (event.pointerType === 'mouse' && event.button !== 0)) return
  const point = getPointFromEvent(event)
  if (!point) return
  event.preventDefault()

  const handleElement = event.target.closest?.('[data-crop-handle]')
  const selectionElement = event.target.closest?.('.crop-selection')
  interaction.active = true
  interaction.pointerId = event.pointerId
  interaction.moved = false
  interaction.startRect = {
    x: form.x,
    y: form.y,
    width: form.width,
    height: form.height
  }

  if (handleElement) {
    interaction.action = 'resize'
    interaction.handle = handleElement.dataset.cropHandle
  } else if (selectionElement && hasSelection.value) {
    interaction.action = 'move'
    interaction.offsetX = point.x - form.x
    interaction.offsetY = point.y - form.y
  } else {
    interaction.action = 'draw'
    interaction.anchorX = point.x
    interaction.anchorY = point.y
  }

  previewHostRef.value?.setPointerCapture?.(event.pointerId)
}

const onStagePointerMove = (event) => {
  if (!interaction.active || interaction.pointerId !== event.pointerId) return
  const point = getPointFromEvent(event)
  if (!point) return
  event.preventDefault()
  interaction.moved = true

  if (interaction.action === 'move' && interaction.startRect) {
    setCropRect({
      x: clamp(point.x - interaction.offsetX, 0, form.imageWidth - interaction.startRect.width),
      y: clamp(point.y - interaction.offsetY, 0, form.imageHeight - interaction.startRect.height),
      width: interaction.startRect.width,
      height: interaction.startRect.height
    })
  } else if (interaction.action === 'resize') {
    resizeCrop(interaction.handle, point)
  } else if (interaction.action === 'draw') {
    setCropRect(rectFromCorner({ x: interaction.anchorX, y: interaction.anchorY }, point, activeRatio.value))
  }
}

const finishPointerInteraction = (event) => {
  if (!interaction.active || interaction.pointerId !== event.pointerId) return
  previewHostRef.value?.releasePointerCapture?.(event.pointerId)
  if (interaction.moved) normalizeManualRect('width')
  interaction.active = false
  interaction.action = ''
  interaction.handle = ''
  interaction.pointerId = null
  interaction.startRect = null
}

const onSelectionKeydown = (event) => {
  if (!hasSelection.value || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
    return
  }
  event.preventDefault()
  const step = event.shiftKey ? 10 : 1
  const deltaX = event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0
  const deltaY = event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0
  setCropRect({
    x: form.x + deltaX,
    y: form.y + deltaY,
    width: form.width,
    height: form.height
  })
  normalizeManualRect()
}

const runCrop = async () => {
  if (!ensurePyReady()) return
  if (!form.file || !hasSelection.value) {
    ElMessage.warning('请先选择图片并设置裁剪区域')
    return
  }

  normalizeManualRect('width')
  loading.value = true
  try {
    const cropX = clamp(Math.round(form.x), 0, form.imageWidth - 1)
    const cropY = clamp(Math.round(form.y), 0, form.imageHeight - 1)
    const cropWidth = clamp(Math.round(form.width), 1, form.imageWidth - cropX)
    const cropHeight = clamp(Math.round(form.height), 1, form.imageHeight - cropY)
    const payload = {
      file: pickPath(form.file),
      mode: 'custom',
      x: cropX,
      y: cropY,
      width: cropWidth,
      height: cropHeight,
      outputDir: form.outputDir
    }
    if (outputSize.value) {
      payload.outputWidth = outputSize.value.width
      payload.outputHeight = outputSize.value.height
      if (outputSize.value.dpi) payload.outputDpi = outputSize.value.dpi
    }

    const { ok, data: res, message } = await pyCall('image_crop', payload)
    if (ok) {
      form.result = res.file || ''
      form.generatedDir = res.outputDir || form.outputDir
      form.resultWidth = Number(res.width) || outputSize.value?.width || cropWidth
      form.resultHeight = Number(res.height) || outputSize.value?.height || cropHeight
      ElMessage.success(message || '裁剪完成')
    } else {
      ElMessage.error(message || '裁剪失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '裁剪失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [form.mode, form.preset, form.exactWidth, form.exactHeight, form.ratioPreset, form.ratioWidth, form.ratioHeight],
  () => {
    if (hasImage.value && activeRatio.value) fitCropToRatio()
  }
)
</script>

<template>
  <section class="panel crop-panel">
    <header>
      <h4>图片裁剪</h4>
      <p>拖动选区调整位置与大小，支持证件照、固定尺寸和比例预设</p>
    </header>

    <FileSelector label="源图片" description="每次处理一张图片，支持当前环境可读取的图片格式" :files="selectedFiles" :removable="true" button-text="选择图片" @select="selectImage" @remove="clearImage" />

    <div class="mode-panel">
      <div class="mode-heading">
        <span>裁剪方式</span>
        <small>{{ outputLabel }}</small>
      </div>
      <el-radio-group v-model="form.mode" size="small">
        <el-radio-button label="preset">常用预设</el-radio-button>
        <el-radio-button label="size">具体尺寸</el-radio-button>
        <el-radio-button label="ratio">宽高比例</el-radio-button>
        <el-radio-button label="free">自由裁剪</el-radio-button>
      </el-radio-group>

      <div v-if="form.mode === 'preset'" class="preset-grid">
        <button v-for="item in PRESETS" :key="item.value" type="button" class="preset-card" :class="{ active: form.preset === item.value }" @click="form.preset = item.value">
          <strong>{{ item.label }}</strong>
          <span>{{ item.detail }}</span>
        </button>
      </div>

      <div v-else-if="form.mode === 'size'" class="dimension-row">
        <span class="inline-label">输出尺寸</span>
        <el-input-number v-model="form.exactWidth" :min="1" :max="20000" controls-position="right" />
        <span class="multiply">×</span>
        <el-input-number v-model="form.exactHeight" :min="1" :max="20000" controls-position="right" />
        <span class="unit">px</span>
      </div>

      <div v-else-if="form.mode === 'ratio'" class="ratio-row">
        <span class="inline-label">选区比例</span>
        <el-select v-model="form.ratioPreset" style="width: 140px">
          <el-option v-for="item in RATIO_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <template v-if="form.ratioPreset === 'custom'">
          <el-input-number v-model="form.ratioWidth" :min="1" :max="1000" controls-position="right" />
          <span class="multiply">:</span>
          <el-input-number v-model="form.ratioHeight" :min="1" :max="1000" controls-position="right" />
        </template>
      </div>

      <p v-else class="free-hint">选区宽高互不锁定，可以从任意方向自由调整。</p>
    </div>

    <div v-loading="previewLoading" class="editor-card">
      <div class="editor-toolbar">
        <div>
          <strong>裁剪预览</strong>
          <span v-if="hasImage">{{ form.imageWidth }} × {{ form.imageHeight }} px</span>
        </div>
        <el-button size="small" :disabled="!hasImage" @click="initializeCrop"> 重新居中 </el-button>
      </div>

      <div v-if="!form.previewUrl" class="empty-editor">
        <div class="empty-icon">▧</div>
        <p>选择图片后即可拖动编辑裁剪区域</p>
      </div>

      <div v-else class="stage-shell">
        <div ref="previewHostRef" class="crop-stage" @pointerdown="onStagePointerDown" @pointermove="onStagePointerMove" @pointerup="finishPointerInteraction" @pointercancel="finishPointerInteraction">
          <img :src="form.previewUrl" class="preview-image" alt="待裁剪图片预览" draggable="false" @load="onPreviewLoaded" />
          <div v-if="hasSelection" class="crop-selection" :style="selectionStyle" tabindex="0" aria-label="裁剪区域，可拖动位置或使用方向键微调" @keydown="onSelectionKeydown">
            <i class="grid-line vertical first" />
            <i class="grid-line vertical second" />
            <i class="grid-line horizontal first" />
            <i class="grid-line horizontal second" />
            <span class="selection-badge">{{ selectionSizeLabel }}</span>
            <span v-for="handle in ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w']" :key="handle" class="crop-handle" :class="'handle-' + handle" :data-crop-handle="handle" :aria-label="'调整裁剪区域 ' + handle" />
          </div>
        </div>
      </div>

      <p class="editor-hint">拖动框移动选区，拖动八个控制点缩放；在选区外拖动可重新绘制。方向键可微调，Shift + 方向键每次移动 10 px。</p>
    </div>

    <div class="precision-panel">
      <div class="precision-heading">
        <div>
          <strong>精确调整选区</strong>
          <span>坐标均以原图像素计算</span>
        </div>
      </div>
      <div class="coordinate-grid">
        <label>
          <span>X</span>
          <el-input-number v-model="form.x" :min="0" :max="Math.max(0, form.imageWidth - 1)" :disabled="!hasImage" controls-position="right" @change="normalizeManualRect('x')" />
        </label>
        <label>
          <span>Y</span>
          <el-input-number v-model="form.y" :min="0" :max="Math.max(0, form.imageHeight - 1)" :disabled="!hasImage" controls-position="right" @change="normalizeManualRect('y')" />
        </label>
        <label>
          <span>宽</span>
          <el-input-number v-model="form.width" :min="1" :max="Math.max(1, form.imageWidth)" :disabled="!hasImage" controls-position="right" @change="normalizeManualRect('width')" />
        </label>
        <label>
          <span>高</span>
          <el-input-number v-model="form.height" :min="1" :max="Math.max(1, form.imageHeight)" :disabled="!hasImage" controls-position="right" @change="normalizeManualRect('height')" />
        </label>
      </div>
    </div>

    <el-form :model="form" label-width="92px" class="output-form">
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" :disabled="!hasSelection" @click="runCrop"> 导出裁剪图片 </el-button>
      </el-form-item>
    </el-form>

    <ResultTable
      v-if="resultItems.length"
      title="裁剪输出"
      :items="resultItems"
      :columns="[
        { label: '文件路径', prop: 'path' },
        { label: '图片尺寸', prop: 'size', width: 150 }
      ]"
    >
      <template #actions>
        <el-button text type="primary" @click="openPath(form.result)">打开文件</el-button>
        <el-button text type="primary" @click="openDir">打开目录</el-button>
      </template>
    </ResultTable>
  </section>
</template>

<style scoped>
.crop-panel {
  padding: 22px;
}

.mode-panel,
.editor-card,
.precision-panel {
  margin-top: 18px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-base);
}

.mode-panel {
  padding: 16px;
}

.mode-heading,
.editor-toolbar,
.precision-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.mode-heading {
  margin-bottom: 12px;
}

.mode-heading > span,
.editor-toolbar strong,
.precision-heading strong {
  color: var(--ppx-text-primary);
  font-size: 14px;
  font-weight: 600;
}

.mode-heading small {
  color: var(--ppx-text-muted);
  font-size: 12px;
  text-align: right;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.preset-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  min-width: 0;
  padding: 11px 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-sm);
  background: var(--ppx-bg-surface);
  color: var(--ppx-text-primary);
  cursor: pointer;
  text-align: left;
  transition: all var(--ppx-transition-fast);
}

.preset-card:hover {
  border-color: rgba(43, 111, 255, 0.45);
  background: var(--ppx-bg-hover);
}

.preset-card.active {
  border-color: #2b6fff;
  background: rgba(43, 111, 255, 0.1);
  box-shadow: 0 0 0 1px rgba(43, 111, 255, 0.12);
}

.preset-card strong {
  font-size: 13px;
}

.preset-card span {
  color: var(--ppx-text-muted);
  font-size: 11px;
}

.dimension-row,
.ratio-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.dimension-row :deep(.el-input-number),
.ratio-row :deep(.el-input-number) {
  width: 132px;
}

.inline-label {
  min-width: 64px;
  color: var(--ppx-text-secondary);
  font-size: 13px;
}

.multiply,
.unit {
  color: var(--ppx-text-muted);
  font-size: 13px;
}

.free-hint {
  margin: 12px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.editor-card {
  overflow: hidden;
}

.editor-toolbar {
  padding: 12px 14px;
  border-bottom: 1px solid var(--ppx-glass-border);
}

.editor-toolbar > div {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.editor-toolbar span,
.precision-heading span {
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.empty-editor {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--ppx-text-muted);
  background: linear-gradient(45deg, rgba(128, 128, 128, 0.05) 25%, transparent 25%), linear-gradient(-45deg, rgba(128, 128, 128, 0.05) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, rgba(128, 128, 128, 0.05) 75%), linear-gradient(-45deg, transparent 75%, rgba(128, 128, 128, 0.05) 75%);
  background-position:
    0 0,
    0 8px,
    8px -8px,
    -8px 0;
  background-size: 16px 16px;
}

.empty-editor p {
  margin: 0;
  font-size: 13px;
}

.empty-icon {
  font-size: 34px;
  opacity: 0.55;
}

.stage-shell {
  display: flex;
  min-height: 280px;
  align-items: center;
  justify-content: center;
  padding: 18px;
  overflow: hidden;
  background: #151922;
}

.crop-stage {
  position: relative;
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  line-height: 0;
  touch-action: none;
  user-select: none;
  cursor: crosshair;
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.3);
}

.preview-image {
  display: block;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 520px;
  pointer-events: none;
}

.crop-selection {
  position: absolute;
  box-sizing: border-box;
  border: 2px solid #ffffff;
  outline: 1px solid rgba(43, 111, 255, 0.95);
  box-shadow: 0 0 0 9999px rgba(5, 9, 18, 0.58);
  cursor: move;
  line-height: normal;
}

.crop-selection:focus-visible {
  outline: 2px solid #7ba5ff;
  outline-offset: 2px;
}

.grid-line {
  position: absolute;
  z-index: 1;
  display: block;
  background: rgba(255, 255, 255, 0.48);
  pointer-events: none;
}

.grid-line.vertical {
  top: 0;
  bottom: 0;
  width: 1px;
}

.grid-line.horizontal {
  right: 0;
  left: 0;
  height: 1px;
}

.grid-line.first.vertical {
  left: 33.333%;
}

.grid-line.second.vertical {
  left: 66.666%;
}

.grid-line.first.horizontal {
  top: 33.333%;
}

.grid-line.second.horizontal {
  top: 66.666%;
}

.selection-badge {
  position: absolute;
  z-index: 2;
  right: 5px;
  bottom: 5px;
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(8, 12, 20, 0.76);
  color: #fff;
  font-size: 11px;
  line-height: 1.25;
  pointer-events: none;
  white-space: nowrap;
}

.crop-handle {
  position: absolute;
  z-index: 3;
  width: 12px;
  height: 12px;
  border: 2px solid #fff;
  border-radius: 2px;
  background: #2b6fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
}

.handle-nw {
  top: 0;
  left: 0;
  cursor: nwse-resize;
  transform: translate(-50%, -50%);
}

.handle-n {
  top: 0;
  left: 50%;
  cursor: ns-resize;
  transform: translate(-50%, -50%);
}

.handle-ne {
  top: 0;
  right: 0;
  cursor: nesw-resize;
  transform: translate(50%, -50%);
}

.handle-e {
  top: 50%;
  right: 0;
  cursor: ew-resize;
  transform: translate(50%, -50%);
}

.handle-se {
  right: 0;
  bottom: 0;
  cursor: nwse-resize;
  transform: translate(50%, 50%);
}

.handle-s {
  bottom: 0;
  left: 50%;
  cursor: ns-resize;
  transform: translate(-50%, 50%);
}

.handle-sw {
  bottom: 0;
  left: 0;
  cursor: nesw-resize;
  transform: translate(-50%, 50%);
}

.handle-w {
  top: 50%;
  left: 0;
  cursor: ew-resize;
  transform: translate(-50%, -50%);
}

.editor-hint {
  margin: 0;
  padding: 10px 14px;
  border-top: 1px solid var(--ppx-glass-border);
  color: var(--ppx-text-muted);
  font-size: 12px;
  line-height: 1.55;
}

.precision-panel {
  padding: 14px;
}

.precision-heading > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.coordinate-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.coordinate-grid label {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;
}

.coordinate-grid label > span {
  color: var(--ppx-text-secondary);
  font-size: 12px;
}

.coordinate-grid :deep(.el-input-number) {
  width: 100%;
}

.output-form {
  margin-top: 18px;
}

@media (max-width: 760px) {
  .crop-panel {
    padding: 16px;
  }

  .mode-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .mode-heading small {
    text-align: left;
  }

  .preset-grid {
    grid-template-columns: 1fr;
  }

  .coordinate-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stage-shell {
    min-height: 220px;
    padding: 10px;
  }

  .preview-image {
    max-height: 420px;
  }
}

@media (max-width: 480px) {
  .coordinate-grid {
    grid-template-columns: 1fr;
  }

  .dimension-row :deep(.el-input-number),
  .ratio-row :deep(.el-input-number) {
    width: 112px;
  }

  .selection-badge {
    display: none;
  }
}
</style>
