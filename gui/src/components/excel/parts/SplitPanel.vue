<script setup>
import { computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useDraft } from '../../../utils/workspace'
import ResultTable from '@/components/shared/ResultTable.vue'
import { callApiRaw, selectInputFiles } from '@/utils/pyapi'
import { useExcelRequest } from '../useExcelRequest'

const props = defineProps({ rules: { type: Object, required: true } })
const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const form = useDraft('excel/parts/SplitPanel/form', { file: null, sheet: '', sheets: [], schema: [], schemaText: '', delimiter: '|', column: '', minRows: 1, limit: 0, emptyLabel: '未分类', outputDir: '', groups: [], files: [] })
const { loading, error, request, safely } = useExcelRequest()
const resultRows = computed(() => form.groups.map((item, index) => ({ ...item, file: form.files[index] || '' })))
let version = 0
let pickSequence = 0
let settingSheet = false
const readingRules = () => ({ headerRow: props.rules.headerRow, formulaPolicy: props.rules.formulaPolicy, trimText: false, deduplicateColumns: [] })
const invalidate = () => {
  version += 1
  Object.assign(form, { schema: [], schemaText: '', column: '', groups: [], files: [] })
  error.value = ''
}
const loadPreview = async () => {
  if (!form.file) return
  invalidate()
  const revision = ++version
  const result = await request('excel_preview', { filePath: form.file.path, sheetName: form.sheet, ...readingRules() }, () => revision === version)
  if (!result) return
  settingSheet = true
  form.sheet = result.sheet || form.sheet
  settingSheet = false
  Object.assign(form, { sheets: result.sheets || [], schema: result.schema || [], schemaText: result.schemaText || '', delimiter: result.delimiter || '|' })
  if (!form.schema.includes(form.column)) form.column = form.schema[0] || ''
}
watch(
  () => form.file,
  () => {
    invalidate()
    settingSheet = true
    form.sheet = ''
    settingSheet = false
    form.sheets = []
    if (form.file) loadPreview()
  },
  { flush: 'sync' }
)
watch(
  () => [form.sheet, props.rules.headerRow, props.rules.formulaPolicy],
  () => {
    if (settingSheet) return
    invalidate()
    if (form.file) loadPreview()
  },
  { flush: 'sync' }
)
watch(
  () => [form.column, form.minRows, form.limit, form.emptyLabel],
  () => {
    version += 1
    form.groups = []
    form.files = []
  },
  { flush: 'sync' }
)
const selectFile = async () => {
  const sequence = ++pickSequence
  const picked = await safely(() => selectInputFiles('excel/split', excelFilter))
  if (sequence === pickSequence && picked?.length) form.file = { ...picked[0] }
}
const selectDir = async () => {
  const dir = await safely(() => callApiRaw('system_pySelectDirDialog', form.outputDir))
  if (dir) form.outputDir = dir
}
const clear = () => {
  pickSequence += 1
  form.file = null
}
const run = async () => {
  if (!form.file || !form.column) return ElMessage.warning('请选择 Excel 文件和拆分列')
  const revision = ++version
  form.groups = []
  form.files = []
  const result = await request('excel_split_by_column', { filePath: form.file.path, sheetName: form.sheet, schemaText: form.schemaText, delimiter: form.delimiter, column: form.column, minRows: form.minRows, limit: form.limit, emptyLabel: form.emptyLabel, outputDir: form.outputDir, ...readingRules() }, () => revision === version)
  if (result) {
    form.groups = result.groups || []
    form.files = result.files || []
    form.outputDir = result.outputDir || form.outputDir
    ElMessage.success(result.msg || '拆分完成')
  }
}
const openOutput = () => form.outputDir && safely(() => callApiRaw('system_pyOpenFile', form.outputDir))
</script>

<template>
  <section class="panel">
    <header>
      <h4>按列拆分工作簿</h4>
      <p>根据指定字段分组，将每组导出为独立 Excel 文件；拆分使用上方表头与公式规则。</p>
    </header>
    <div class="split-input"><el-button @click="selectFile">选择 / 接收 Excel</el-button><el-button v-if="form.file" text type="danger" @click="clear">移除主文件</el-button></div>
    <p v-if="form.file" class="input-path">{{ form.file.path }}</p>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-form :model="form" label-width="110px" class="form-block">
      <el-form-item v-if="form.sheets.length" label="工作表"
        ><el-select v-model="form.sheet" style="width: 240px"><el-option v-for="sheet in form.sheets" :key="sheet" :label="sheet" :value="sheet" /></el-select
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
      <el-form-item><el-button type="primary" :disabled="!form.file || !form.column" :loading="loading" @click="run">开始拆分</el-button><el-button v-if="form.file" :loading="loading" @click="loadPreview">重新读取工作表</el-button></el-form-item>
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
      <template #actions><el-button v-if="form.files.length" text type="primary" @click="openOutput">打开目录</el-button></template>
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
.input-path {
  overflow-wrap: anywhere;
  font-size: 12px;
  line-height: 1.6;
  color: var(--ppx-text-primary);
}
.split-input {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}
</style>
