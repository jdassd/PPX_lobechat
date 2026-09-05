<script setup>
import { useDraft } from '../../utils/workspace'
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentChecked, FolderOpened, Picture, Upload } from '@element-plus/icons-vue'

import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const props = defineProps({
  sourceType: {
    type: String,
    required: true,
    validator: (value) => ['image', 'pdf'].includes(value)
  }
})

const loading = ref(false)
const result = reactive({ preview: '', outputs: [], lineCount: 0, pageCount: 0, confidence: 0, uncertain: [] })
const form = useDraft(`${props.sourceType}/ocr/form`, { file: null, outputDir: '', pageSpec: '', dpi: 220, outputMode: props.sourceType === 'pdf' ? 'both' : 'text', autoRotate: false, rotation: 0 })

const isPdf = computed(() => props.sourceType === 'pdf')
const selectedPath = computed(() => form.file?.path || form.file || '')
const selectedName = computed(() => form.file?.filename || selectedPath.value.split(/[\\/]/).pop() || '')
const filter = computed(() => (isPdf.value ? ['PDF 文件 (*.pdf)'] : ['图片 (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff)']))

const ensureDesktop = () => {
  if (hasPyApi()) return true
  ElMessage.warning('OCR 需要在桌面客户端中使用')
  return false
}

const selectFile = async () => {
  if (!ensureDesktop()) return
  try {
    const files = await callApiRaw('system_pyCreateFileDialog', filter.value)
    if (files?.length) form.file = files[0]
  } catch (error) {
    ElMessage.error(error?.message || '选择文件失败')
  }
}

const selectDir = async () => {
  if (!ensureDesktop()) return
  try {
    const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
    if (dir) form.outputDir = dir
  } catch (error) {
    ElMessage.error(error?.message || '选择目录失败')
  }
}

const openOutput = async (path) => {
  if (!path || !ensureDesktop()) return
  try {
    await callApiRaw('system_pyOpenFile', path)
  } catch (error) {
    ElMessage.error(error?.message || '打开输出文件失败')
  }
}

const run = async () => {
  if (!ensureDesktop()) return
  if (!selectedPath.value) {
    ElMessage.warning('请先选择源文件')
    return
  }
  loading.value = true
  result.preview = ''
  result.outputs = []
  try {
    const payload = {
      filePath: selectedPath.value,
      autoRotate: form.autoRotate,
      rotation: form.rotation,
      outputDir: form.outputDir,
      saveFile: true,
      pageSpec: form.pageSpec,
      dpi: form.dpi,
      outputMode: isPdf.value ? form.outputMode : 'text'
    }
    const response = await callApi(isPdf.value ? 'ocr_pdf' : 'ocr_image', payload)
    if (!response.ok) {
      ElMessage.error(response.message || 'OCR 识别失败')
      return
    }
    const data = response.data || {}
    result.preview = data.preview || ''
    result.outputs = data.outputs?.length ? data.outputs : data.output ? [data.output] : []
    result.lineCount = data.lineCount || 0
    result.pageCount = data.pageCount || 0
    result.confidence = Math.round((data.averageConfidence || 0) * 100)
    result.uncertain = (data.lines || (data.pages || []).flatMap((page) => page.lines.map((line) => ({ ...line, page: page.page })))).filter((line) => line.lowConfidence)
    ElMessage.success(response.message || 'OCR 识别完成')
  } catch (error) {
    ElMessage.error(error?.message || 'OCR 识别失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel ocr-panel">
    <header>
      <h4>{{ isPdf ? '扫描 PDF 文字识别' : '图片文字识别' }}</h4>
      <p>{{ isPdf ? '离线识别扫描页面，可同时输出纯文本和可搜索 PDF' : '离线识别图片中的中英文，并导出 UTF-8 文本' }}</p>
    </header>

    <el-alert title="文件只在本机处理。首次运行需要数秒加载识别模型。" type="info" :closable="false" show-icon />

    <button class="source-card" type="button" @click="selectFile">
      <span class="source-icon"
        ><el-icon :size="24"><component :is="isPdf ? DocumentChecked : Picture" /></el-icon
      ></span>
      <span class="source-meta"
        ><b>{{ selectedName || (isPdf ? '选择扫描 PDF' : '选择图片') }}</b
        ><small>{{ selectedPath || '点击从电脑中选择文件' }}</small></span
      >
      <el-icon><Upload /></el-icon>
    </button>

    <el-form :model="form" label-width="104px" class="form-block">
      <el-form-item label="方向校正"
        ><el-checkbox v-model="form.autoRotate">比较四个方向（较慢）</el-checkbox><el-select v-if="!form.autoRotate" v-model="form.rotation" style="width: 140px"><el-option v-for="angle in [0, 90, 180, 270]" :key="angle" :value="angle" :label="angle + '°'" /></el-select
      ></el-form-item>
      <template v-if="isPdf">
        <el-form-item label="识别页码"><el-input v-model="form.pageSpec" placeholder="留空识别全部，例如 1-3,5" /></el-form-item>
        <el-form-item label="清晰度">
          <el-slider v-model="form.dpi" :min="150" :max="320" :step="10" show-input />
        </el-form-item>
        <el-form-item label="输出内容">
          <el-radio-group v-model="form.outputMode">
            <el-radio-button label="both">文本 + 可搜索 PDF</el-radio-button>
            <el-radio-button label="searchable_pdf">仅可搜索 PDF</el-radio-button>
            <el-radio-button label="text">仅文本</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </template>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" readonly placeholder="留空则保存到源文件目录" /><el-button @click="selectDir"
            ><el-icon><FolderOpened /></el-icon>&nbsp;选择</el-button
          >
        </div>
      </el-form-item>
    </el-form>

    <div class="actions"><el-button type="primary" :loading="loading" :disabled="!selectedPath" @click="run">开始 OCR</el-button></div>

    <div v-if="result.preview || result.outputs.length" class="result-card">
      <div class="result-head">
        <b>识别结果</b><span>{{ result.pageCount ? `${result.pageCount} 页 · ` : '' }}{{ result.lineCount }} 行 · 平均置信度 {{ result.confidence }}%</span>
      </div>
      <el-input v-if="result.preview" :model-value="result.preview" type="textarea" :rows="9" readonly />
      <el-collapse v-if="result.uncertain.length"
        ><el-collapse-item :title="`${result.uncertain.length} 行低置信度内容，请核对原文`"
          ><p v-for="(line, index) in result.uncertain.slice(0, 100)" :key="index">
            <el-tag type="warning" size="small">{{ Math.round(line.score * 100) }}%</el-tag> {{ line.page ? `第 ${line.page} 页` : '' }} {{ line.text }}
          </p></el-collapse-item
        ></el-collapse
      >
      <div v-if="result.outputs.length" class="outputs">
        <el-button v-for="path in result.outputs" :key="path" plain @click="openOutput(path)"
          ><el-icon><FolderOpened /></el-icon>&nbsp;打开 {{ path.split(/[\\/]/).pop() }}</el-button
        >
      </div>
    </div>
  </section>
</template>

<style scoped>
.ocr-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.source-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 15px;
  border: 1px dashed var(--ppx-glass-border-hover);
  border-radius: 12px;
  background: var(--ppx-bg-inset);
  color: var(--ppx-text-secondary);
  cursor: pointer;
  text-align: left;
}
.source-card:hover {
  border-color: var(--accent);
}
.source-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 11px;
  background: var(--ppx-bg-surface);
  color: var(--accent);
}
.source-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.source-meta b {
  color: var(--ppx-text-primary);
  font-size: 13.5px;
}
.source-meta small {
  margin-top: 3px;
  color: var(--ppx-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.form-block {
  max-width: 760px;
}
.field-row {
  width: 100%;
  display: flex;
  gap: 8px;
}
.actions {
  display: flex;
  justify-content: flex-end;
}
.result-card {
  padding-top: 16px;
  border-top: 1px solid var(--ppx-glass-border);
}
.result-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  color: var(--ppx-text-primary);
  font-size: 13px;
}
.result-head span {
  color: var(--ppx-text-muted);
  font-size: 11.5px;
}
.outputs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
</style>
