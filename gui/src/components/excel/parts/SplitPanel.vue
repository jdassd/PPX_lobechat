<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import FileSelector from '@/components/shared/FileSelector.vue'
import ResultTable from '@/components/shared/ResultTable.vue'
import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const loading = ref(false)
const form = reactive({ file: null, sheet: '', sheets: [], schema: [], schemaText: '', delimiter: '|', column: '', minRows: 1, limit: 0, emptyLabel: '未分类', outputDir: '', groups: [], files: [] })
const selected = computed(() => (form.file ? [form.file] : []))
const resultRows = computed(() => form.groups.map((item, index) => ({ ...item, file: form.files[index] || '' })))

const ready = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const loadPreview = async () => {
  if (!form.file) return
  const result = await callApi('excel_preview', { filePath: form.file.path, sheetName: form.sheet })
  if (!result.ok) return ElMessage.error(result.message || '读取工作簿失败')
  form.sheet = result.data.sheet || form.sheet
  form.sheets = result.data.sheets || []
  form.schema = result.data.schema || []
  form.schemaText = result.data.schemaText || ''
  form.delimiter = result.data.delimiter || '|'
  if (!form.schema.includes(form.column)) form.column = form.schema[0] || ''
}
const selectFile = async () => {
  if (!ready()) return
  const picked = await callApiRaw('system_pyCreateFileDialog', excelFilter)
  if (!picked?.length) return
  form.file = picked[0]
  form.sheet = ''
  await loadPreview()
}
const selectDir = async () => {
  if (!ready()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) form.outputDir = dir
}
const clear = () => {
  form.file = null
  form.schema = []
  form.groups = []
  form.files = []
}
const run = async () => {
  if (!form.file || !form.column) return ElMessage.warning('请选择 Excel 文件和拆分列')
  loading.value = true
  try {
    const result = await callApi('excel_split_by_column', { filePath: form.file.path, sheetName: form.sheet, schemaText: form.schemaText, delimiter: form.delimiter, column: form.column, minRows: form.minRows, limit: form.limit, emptyLabel: form.emptyLabel, outputDir: form.outputDir })
    if (!result.ok) return ElMessage.error(result.message || '拆分失败')
    form.groups = result.data.groups || []
    form.files = result.data.files || []
    form.outputDir = result.data.outputDir || form.outputDir
    ElMessage.success(result.message || '拆分完成')
  } finally {
    loading.value = false
  }
}
const openOutput = () => form.outputDir && callApiRaw('system_pyOpenFile', form.outputDir)
</script>

<template>
  <section class="panel">
    <header>
      <h4>按列拆分工作簿</h4>
      <p>根据指定字段分组，将每个分组导出为独立 Excel 文件</p>
    </header>
    <FileSelector label="Excel 文件" :files="selected" removable @select="selectFile" @remove="clear" />
    <el-form :model="form" label-width="110px" class="form-block">
      <el-form-item v-if="form.sheets.length > 1" label="工作表"
        ><el-select v-model="form.sheet" style="width: 240px" @change="loadPreview"><el-option v-for="sheet in form.sheets" :key="sheet" :label="sheet" :value="sheet" /></el-select
      ></el-form-item>
      <el-form-item label="拆分列"
        ><el-select v-model="form.column" filterable style="width: 240px"><el-option v-for="field in form.schema" :key="field" :label="field" :value="field" /></el-select
      ></el-form-item>
      <el-form-item label="最少行数"><el-input-number v-model="form.minRows" :min="1" /></el-form-item>
      <el-form-item label="最多分组"><el-input-number v-model="form.limit" :min="0" /><span class="hint">0 表示不限</span></el-form-item>
      <el-form-item label="空值分组"><el-input v-model="form.emptyLabel" style="width: 240px" /></el-form-item>
      <el-form-item label="输出目录"
        ><div class="field-row"><el-input v-model="form.outputDir" readonly placeholder="自动创建" /><el-button @click="selectDir">选择</el-button></div></el-form-item
      >
      <el-form-item><el-button type="primary" :loading="loading" @click="run">开始拆分</el-button></el-form-item>
    </el-form>
    <ResultTable
      title="拆分结果"
      :items="resultRows"
      :columns="[
        { prop: 'label', label: '分组' },
        { prop: 'rows', label: '行数', width: 90 },
        { prop: 'file', label: '文件' }
      ]"
    >
      <template #actions><el-button v-if="form.outputDir" text type="primary" @click="openOutput">打开目录</el-button></template>
    </ResultTable>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
.hint {
  margin-left: 8px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>
