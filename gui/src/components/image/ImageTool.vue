<script setup>
import { computed, reactive } from 'vue'
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
  resize: {
    files: [],
    mode: 'percent',
    percent: 80,
    width: 1920,
    height: 1080,
    keepRatio: true,
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
    outputDir: '',
    generatedDir: '',
    result: ''
  },
  rotate: {
    files: [],
    operation: 'rotate90',
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
  }
})

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
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(imageFilter)
  if (files?.length) {
    state[target][field] = files[0]
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

const runResize = async () => {
  if (!ensurePyReady() || !ensureFilesReady('resize')) return
  state.loading = true
  try {
    const payload = {
      files: pickPaths(state.resize.files),
      mode: state.resize.mode,
      percent: state.resize.percent,
      width: state.resize.width,
      height: state.resize.height,
      keepRatio: state.resize.keepRatio,
      outputDir: state.resize.outputDir
    }
    const res = await window.pywebview.api.image_batch_resize(payload)
    if (res?.code === 0) {
      state.resize.result = res.files || []
      state.resize.generatedDir = res.outputDir || state.resize.outputDir
      ElMessage.success(res.msg || '缩放完成')
    } else {
      ElMessage.error(res?.msg || '缩放失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '缩放失败')
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
          <p class="sub">格式转换、缩放、压缩、水印及 PDF 合成</p>
        </div>
        <el-tag type="warning" size="large">Phase 2</el-tag>
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

        <el-tab-pane label="批量缩放" name="resize">
          <section class="panel">
            <header>
              <h4>尺寸调整</h4>
              <p>可按百分比或像素缩放尺寸，支持保持比例</p>
            </header>
            <FileSelector
              label="待处理图片"
              :files="state.resize.files"
              :removable="true"
              @select="selectImages('resize')"
              @remove="(file) => removeFile('resize', file)"
            />
            <el-form :model="state.resize" label-width="120px" class="form-block">
              <el-form-item label="模式">
                <el-radio-group v-model="state.resize.mode">
                  <el-radio-button label="percent">按百分比</el-radio-button>
                  <el-radio-button label="pixel">按像素</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.resize.mode === 'percent'" label="缩放比例">
                <el-slider v-model="state.resize.percent" :min="10" :max="300" show-input />
              </el-form-item>
              <template v-else>
                <el-form-item label="目标尺寸">
                  <div class="field-row">
                    <el-input-number v-model="state.resize.width" :min="32" />
                    <span>×</span>
                    <el-input-number v-model="state.resize.height" :min="32" />
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-checkbox v-model="state.resize.keepRatio">保持原比例</el-checkbox>
                </el-form-item>
              </template>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.resize.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('resize')">选目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runResize">开始处理</el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.resize.result.length"
              title="输出文件"
              :items="state.resize.result.map((path) => ({ path }))"
              :columns="[{ label: '文件路径', prop: 'path' }]"
            >
              <template #actions>
                <el-button text type="primary" @click="openDir('resize')">打开目录</el-button>
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

        <el-tab-pane label="水印 / 批处理" name="watermark">
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
              <el-form-item label="位置">
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
                </el-select>
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
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  color: #8a90a6;
  letter-spacing: 2px;
}

.image-tabs {
  margin-top: 10px;
}

.panel {
  background: #fff;
  border: 1px solid #e9edf5;
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 24px;
}

.panel header h4 {
  margin: 0;
}

.panel header p {
  margin: 6px 0 0;
  color: #7a829d;
  font-size: 13px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.field-row--wrap {
  flex-wrap: wrap;
}

.form-block {
  margin-top: 18px;
}

.watermark-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.link {
  color: #2f73ff;
  cursor: pointer;
}
</style>
