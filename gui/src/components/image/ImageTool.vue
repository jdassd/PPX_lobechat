<script setup>
import { computed, reactive, ref, watch } from 'vue'

import FormatPanel from './parts/FormatPanel.vue'
import CompressPanel from './parts/CompressPanel.vue'
import WatermarkPanel from './parts/WatermarkPanel.vue'
import CropPanel from './parts/CropPanel.vue'
import RotatePanel from './parts/RotatePanel.vue'
import PdfPanel from './parts/PdfPanel.vue'
import AdvancedPanel from './parts/AdvancedPanel.vue'

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

const activeTab = ref('convert')

const fallbackConvertFormatOptions = [
  { label: 'PNG', value: 'png' },
  { label: 'JPG', value: 'jpg' },
  { label: 'WEBP', value: 'webp' },
  { label: 'BMP', value: 'bmp' },
  { label: 'TIFF', value: 'tiff' },
  { label: 'GIF', value: 'gif' },
  { label: 'SVG', value: 'svg' },
  { label: 'AVIF', value: 'avif' },
  { label: 'ICO', value: 'ico' },
  { label: 'ICNS', value: 'icns' },
  { label: 'TGA', value: 'tga' },
  { label: 'QOI', value: 'qoi' },
  { label: 'PPM', value: 'ppm' },
  { label: 'JP2', value: 'jp2' }
]

const fallbackRasterFormatOptions = fallbackConvertFormatOptions.filter((item) => item.value !== 'svg')
const fallbackImageFilter = [
  '图片 (*.png;*.apng;*.jpg;*.jpeg;*.jpe;*.jfif;*.webp;*.bmp;*.dib;*.tif;*.tiff;*.gif;*.avif;*.avifs;*.ico;*.icns;*.tga;*.icb;*.vda;*.vst;*.qoi;*.ppm;*.pnm;*.pbm;*.pgm;*.pfm;*.jp2;*.j2k;*.j2c;*.jpc;*.jpf;*.jpx)'
]

const supportedFormats = reactive({
  convert: [...fallbackConvertFormatOptions],
  raster: [...fallbackRasterFormatOptions],
  imageFilter: [...fallbackImageFilter]
})

const normalizeFormatOptions = (items = [], fallback = []) => {
  if (!Array.isArray(items) || !items.length) return [...fallback]
  const seen = new Set()
  return items
    .map((item) => {
      if (!item) return null
      if (typeof item === 'string') {
        return {
          label: item.toUpperCase(),
          value: item
        }
      }
      const value = String(item.value || '').trim()
      if (!value) return null
      return {
        label: String(item.label || value).toUpperCase(),
        value
      }
    })
    .filter((item) => {
      if (!item || seen.has(item.value)) return false
      seen.add(item.value)
      return true
    })
}

const syncSupportedFormats = (payload = {}) => {
  const convert = normalizeFormatOptions(payload.convertFormats, fallbackConvertFormatOptions)
  const raster = normalizeFormatOptions(payload.rasterFormats, convert.filter((item) => item.value !== 'svg'))
  supportedFormats.convert = convert
  supportedFormats.raster = raster.length ? raster : [...fallbackRasterFormatOptions]
  supportedFormats.imageFilter =
    payload.fileDialogFilter && typeof payload.fileDialogFilter === 'string'
      ? [payload.fileDialogFilter]
      : [...fallbackImageFilter]
}

const loadSupportedFormats = async () => {
  const apiMethod = window.pywebview?.api?.image_supported_formats
  if (typeof apiMethod !== 'function') return
  try {
    const res = await apiMethod()
    if (res?.code === 0) {
      syncSupportedFormats(res)
    }
  } catch {
    // 保持前端兜底格式，不额外打断用户操作
  }
}

watch(
  () => visibleProxy.value,
  (visible) => {
    if (visible) {
      loadSupportedFormats()
    }
  },
  { immediate: true }
)
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
      <el-tabs v-model="activeTab" class="image-tabs">
        <el-tab-pane label="格式转换" name="convert">
          <FormatPanel :supported-formats="supportedFormats" />
        </el-tab-pane>

        <el-tab-pane label="批量压缩" name="compress">
          <CompressPanel :supported-formats="supportedFormats" />
        </el-tab-pane>

        <el-tab-pane label="批量水印" name="watermark">
          <WatermarkPanel :supported-formats="supportedFormats" />
        </el-tab-pane>

        <el-tab-pane label="裁剪工具" name="crop">
          <CropPanel :supported-formats="supportedFormats" />
        </el-tab-pane>

        <el-tab-pane label="旋转 / 翻转" name="rotate">
          <RotatePanel :supported-formats="supportedFormats" />
        </el-tab-pane>

        <el-tab-pane label="图片转 PDF" name="pdf">
          <PdfPanel :supported-formats="supportedFormats" />
        </el-tab-pane>

        <el-tab-pane label="高级批量" name="advanced">
          <AdvancedPanel :supported-formats="supportedFormats" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 使用全局深空玻璃主题样式 */
</style>
