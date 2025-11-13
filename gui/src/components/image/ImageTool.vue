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
  if (!files || !files.length) return
  state[target].files = files
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

const pickPaths = (files) => files.map((item) => item.path || item)

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
    size="78%"
    append-to-body
    custom-class="image-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">IMAGE TOOLKIT</p>
          <h3>图片处理工具</h3>
          <p class="sub">格式转换、批量缩放与压缩一步到位</p>
        </div>
        <el-tag type="success" size="large">Phase 1</el-tag>
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
                  <el-input v-model="state.format.outputDir" placeholder="留空则自动创建" readonly />
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

.form-block {
  margin-top: 18px;
}
</style>
