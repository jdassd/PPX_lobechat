<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const props = defineProps({
  supportedFormats: {
    type: Object,
    required: true
  }
})

const loading = ref(false)

const form = reactive({
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
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

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
  () => form.imageWidth > 0 && form.imageHeight > 0 && form.displayWidth > 0 && form.displayHeight > 0
)

const hasCropRect = computed(
  () => hasCropImage.value && form.width > 0 && form.height > 0
)

const getCropDisplayRect = () => {
  if (!hasCropRect.value) {
    return null
  }
  const scaleX = form.displayWidth / form.imageWidth
  const scaleY = form.displayHeight / form.imageHeight
  const left = form.x * scaleX
  const top = form.y * scaleY
  const width = form.width * scaleX
  const height = form.height * scaleY
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
  const scaleX = form.displayWidth / form.imageWidth
  const scaleY = form.displayHeight / form.imageHeight
  const left = form.x * scaleX
  const top = form.y * scaleY
  const width = form.width * scaleX
  const height = form.height * scaleY
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  }
})

const updateCropRectByRatio = () => {
  if (!hasCropImage.value) return
  const ratioStr = form.ratio || '1:1'
  const [wStr, hStr] = ratioStr.split(':')
  let ratioW = parseInt(wStr || '1', 10)
  let ratioH = parseInt(hStr || '1', 10)
  if (!Number.isFinite(ratioW) || ratioW <= 0) ratioW = 1
  if (!Number.isFinite(ratioH) || ratioH <= 0) ratioH = 1

  const baseW = form.imageWidth
  const baseH = form.imageHeight
  let targetW = baseW
  let targetH = Math.round((targetW * ratioH) / ratioW)
  if (targetH > baseH) {
    targetH = baseH
    targetW = Math.round((targetH * ratioW) / ratioH)
  }
  const x = Math.max(0, Math.round((baseW - targetW) / 2))
  const y = Math.max(0, Math.round((baseH - targetH) / 2))
  form.x = x
  form.y = y
  form.width = targetW
  form.height = targetH
}

const updateCropRectFromDisplay = (startX, startY, currentX, currentY) => {
  if (!hasCropImage.value) return
  if (startX === currentX && startY === currentY) return
  const minX = Math.max(0, Math.min(startX, currentX))
  const minY = Math.max(0, Math.min(startY, currentY))
  const maxX = Math.min(form.displayWidth, Math.max(startX, currentX))
  const maxY = Math.min(form.displayHeight, Math.max(startY, currentY))
  const widthDisplay = Math.max(1, maxX - minX)
  const heightDisplay = Math.max(1, maxY - minY)
  const scaleX = form.imageWidth / form.displayWidth
  const scaleY = form.imageHeight / form.displayHeight
  form.x = Math.round(minX * scaleX)
  form.y = Math.round(minY * scaleY)
  form.width = Math.round(widthDisplay * scaleX)
  form.height = Math.round(heightDisplay * scaleY)
}

const onCropImageLoaded = (event) => {
  const img = event?.target
  if (!img) return
  const rect = img.getBoundingClientRect()

  // ���ȶ�ȡԭʼͼƬ���ߴ磬���ɵ���� py ���ص�����Ϊ׼
  if (!form.imageWidth || !form.imageHeight) {
    form.imageWidth = img.naturalWidth || rect.width || img.width || 0
    form.imageHeight = img.naturalHeight || rect.height || img.height || 0
  }

  // ��¼��ǰ DOM ��ʾ�ߴ磬��ͼƬ�ߴ渺һ�����ڿռ������
  form.displayWidth = rect.width || img.clientWidth || img.width || 0
  form.displayHeight = rect.height || img.clientHeight || img.height || 0
  if (!form.imageWidth || !form.imageHeight) return

  if (form.mode === 'ratio') {
    updateCropRectByRatio()
  } else if (!form.width || !form.height) {
    form.x = 0
    form.y = 0
    form.width = form.imageWidth
    form.height = form.imageHeight
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
  () => [form.mode, form.ratio],
  () => {
    if (!hasCropImage.value) return
    if (form.mode === 'ratio') {
      updateCropRectByRatio()
    }
  }
)

const selectCropImage = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (!files?.length) return

  const file = files[0]
  form.file = file

  // 重置裁剪状态
  form.previewUrl = ''
  form.imageWidth = 0
  form.imageHeight = 0
  form.displayWidth = 0
  form.displayHeight = 0
  form.x = 0
  form.y = 0
  form.width = 0
  form.height = 0

  try {
    const { ok, data: res } = await pyCall('image_preview', {
      file: file.path || file.filename
    })
    if (ok && res.preview) {
      form.previewUrl = res.preview
      form.imageWidth = res.width || 0
      form.imageHeight = res.height || 0
    } else {
      ElMessage.error(res?.msg || '图片预览失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '图片预览失败')
  }
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) {
    form.outputDir = dir
  }
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const runCrop = async () => {
  if (!ensurePyReady()) return
  if (!form.file) {
    ElMessage.warning('请选择需要裁剪的图片')
    return
  }
  loading.value = true
  try {
    const payload = {
      file: form.file.path || form.file,
      mode: form.mode,
      x: form.x,
      y: form.y,
      width: form.width,
      height: form.height,
      ratio: form.ratio,
      outputDir: form.outputDir
    }
    const { ok, data: res, message } = await pyCall('image_crop', payload)
    if (ok) {
      form.result = res.file || ''
      form.generatedDir = res.outputDir || form.outputDir
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
</script>

<template>
  <section class="panel">
    <header>
      <h4>快速裁剪</h4>
      <p>支持自定义坐标或按比例裁剪</p>
    </header>
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="源图片">
        <div class="field-row">
          <el-input :model-value="form.file?.path || ''" placeholder="请选择图片" readonly />
          <el-button @click="selectCropImage">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button label="custom">自定义</el-radio-button>
          <el-radio-button label="ratio">按比例</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <template v-if="form.mode === 'custom'">
        <div class="field-row field-row--wrap">
          <el-form-item label="X">
            <el-input-number v-model="form.x" :min="0" />
          </el-form-item>
          <el-form-item label="Y">
            <el-input-number v-model="form.y" :min="0" />
          </el-form-item>
          <el-form-item label="宽度">
            <el-input-number v-model="form.width" :min="10" />
          </el-form-item>
          <el-form-item label="高度">
            <el-input-number v-model="form.height" :min="10" />
          </el-form-item>
        </div>
      </template>
      <el-form-item v-else label="比例">
        <el-select v-model="form.ratio" style="width: 220px">
          <el-option label="1:1 (方形)" value="1:1" />
          <el-option label="4:3" value="4:3" />
          <el-option label="3:2" value="3:2" />
          <el-option label="16:9" value="16:9" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.file" label="预览裁剪">
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
              v-if="form.previewUrl"
              :src="form.previewUrl"
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
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runCrop">开始裁剪</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="form.result"
      type="success"
      :closable="false"
      show-icon
    >
      <template #title>
        已输出：
        <a class="link" @click.prevent="openPath(form.result)">{{ form.result }}</a>
      </template>
    </el-alert>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
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
</style>
