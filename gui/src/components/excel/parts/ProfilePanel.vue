<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import FileSelector from '@/components/shared/FileSelector.vue'
import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const loading = ref(false)
const exporting = ref(false)
const form = reactive({ file: null, sheet: '', sheets: [], schemaText: '', delimiter: '|', summary: null, profiles: [], outputDir: '', output: '' })
const files = computed(() => (form.file ? [form.file] : []))
const rows = computed(() => form.profiles.map((item) => ({ ...item, blankText: `${Math.round((item.blankRatio || 0) * 100)}%`, topText: (item.topValues || []).map((entry) => `${entry.value} (${entry.count})`).join('、'), rangeText: item.numeric && Object.keys(item.numeric).length ? `${item.numeric.min} ~ ${item.numeric.max}，均值 ${item.numeric.avg}` : '' })))

const ready = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const selectFile = async () => {
  if (!ready()) return
  const picked = await callApiRaw('system_pyCreateFileDialog', excelFilter)
  if (!picked?.length) return
  form.file = picked[0]
  form.outputDir = picked[0].dir
  form.profiles = []
  const preview = await callApi('excel_preview', { filePath: form.file.path, sheetName: '' })
  if (preview.ok) {
    form.sheet = preview.data.sheet || ''
    form.sheets = preview.data.sheets || []
    form.schemaText = preview.data.schemaText || ''
    form.delimiter = preview.data.delimiter || '|'
  }
}
const chooseOutput = async () => {
  if (!ready()) return
  const directory = await callApiRaw('system_pySelectDirDialog', form.outputDir || '')
  if (directory) form.outputDir = directory
}
const exportReport = async () => {
  if (!form.file) return ElMessage.warning('请先选择 Excel 文件')
  exporting.value = true
  try {
    const result = await callApi('excel_quality_report', { filePath: form.file.path, sheetName: form.sheet, schemaText: form.schemaText, delimiter: form.delimiter, outputDir: form.outputDir })
    if (!result.ok) return ElMessage.error(result.message || '导出失败')
    form.output = result.data.output
    ElMessage.success(result.message || '报告已生成')
  } finally {
    exporting.value = false
  }
}
const openOutput = async () => {
  if (form.output) await callApiRaw('system_pyOpenFile', form.output)
}
const clear = () => {
  form.file = null
  form.summary = null
  form.profiles = []
}
const run = async () => {
  if (!form.file) return ElMessage.warning('请先选择 Excel 文件')
  loading.value = true
  try {
    const result = await callApi('excel_column_profile', { filePath: form.file.path, sheetName: form.sheet, schemaText: form.schemaText, delimiter: form.delimiter })
    if (!result.ok) return ElMessage.error(result.message || '分析失败')
    form.summary = result.data.summary || null
    form.profiles = result.data.profiles || []
    ElMessage.success(result.message || '数据质检完成')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>Excel 数据质检</h4>
      <p>分析缺失值、唯一值、高频值、数据类型与数值范围</p>
    </header>
    <FileSelector label="Excel 文件" :files="files" removable @select="selectFile" @remove="clear" />
    <el-form :model="form" label-width="100px" class="form-block">
      <el-form-item v-if="form.sheets.length > 1" label="工作表"
        ><el-select v-model="form.sheet" style="width: 240px"><el-option v-for="sheet in form.sheets" :key="sheet" :label="sheet" :value="sheet" /></el-select
      ></el-form-item>
      <el-form-item><el-button type="primary" :loading="loading" @click="run">开始质检</el-button></el-form-item>
    </el-form>
    <el-alert v-if="form.summary" type="success" :closable="false" :title="`${form.summary.sheet}：${form.summary.totalRows} 行，${form.summary.columns} 列`" />
    <el-table v-if="rows.length" :data="rows" border size="small" max-height="420" class="result-table">
      <el-table-column prop="field" label="字段" min-width="130" fixed />
      <el-table-column prop="type" label="类型" width="80" />
      <el-table-column prop="unique" label="唯一值" width="90" />
      <el-table-column prop="blanks" label="空值" width="75" />
      <el-table-column prop="blankText" label="空值率" width="85" />
      <el-table-column prop="rangeText" label="数值范围" min-width="180" show-overflow-tooltip />
      <el-table-column prop="topText" label="高频值" min-width="220" show-overflow-tooltip />
    </el-table>
    <div v-if="rows.length" class="report-row">
      <el-input v-model="form.outputDir" placeholder="报告输出目录"
        ><template #append><el-button @click="chooseOutput">选择</el-button></template></el-input
      >
      <el-button :loading="exporting" @click="exportReport">导出质量报告</el-button>
      <el-button v-if="form.output" type="primary" plain @click="openOutput">打开报告</el-button>
    </div>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
.result-table {
  margin-top: 16px;
}
.report-row {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) auto auto;
  gap: 10px;
  margin-top: 14px;
}
</style>
