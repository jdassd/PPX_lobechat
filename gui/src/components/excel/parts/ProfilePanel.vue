<script setup>
import { computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useDraft } from '../../../utils/workspace'
import { callApiRaw, selectInputFiles } from '@/utils/pyapi'
import { useExcelRequest } from '../useExcelRequest'

const props = defineProps({ rules: { type: Object, required: true } })
const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const form = useDraft('excel/parts/ProfilePanel/form', { file: null, sheet: '', sheets: [], schemaText: '', delimiter: '|', summary: null, profiles: [], outputDir: '', output: '' })
const { loading, error, request, safely } = useExcelRequest()
const rows = computed(() => form.profiles.map((item) => ({ ...item, blankText: `${Math.round((item.blankRatio || 0) * 100)}%`, topText: (item.topValues || []).map((entry) => `${entry.value} (${entry.count})`).join('、'), rangeText: item.numeric && Object.keys(item.numeric).length ? `${item.numeric.min} ~ ${item.numeric.max}，均值 ${item.numeric.avg}` : '' })))
let version = 0
let pickSequence = 0
let settingSheet = false
const payload = () => ({
  filePath: form.file.path,
  sheetName: form.sheet,
  schemaText: form.schemaText,
  delimiter: form.delimiter,
  headerRow: props.rules.headerRow,
  formulaPolicy: props.rules.formulaPolicy,
  trimText: false,
  deduplicateColumns: []
})
const invalidate = () => {
  version += 1
  Object.assign(form, { summary: null, profiles: [], output: '', schemaText: '' })
  error.value = ''
}
const loadPreview = async () => {
  if (!form.file) return
  invalidate()
  const revision = ++version
  const result = await request('excel_preview', payload(), () => revision === version)
  if (!result) return
  settingSheet = true
  form.sheet = result.sheet || form.sheet
  settingSheet = false
  form.sheets = result.sheets || []
  form.schemaText = result.schemaText || ''
  form.delimiter = result.delimiter || '|'
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
const selectFile = async () => {
  const sequence = ++pickSequence
  const picked = await safely(() => selectInputFiles('excel/profile', excelFilter))
  if (sequence !== pickSequence || !picked?.length) return
  form.file = { ...picked[0] }
  if (!form.outputDir) form.outputDir = picked[0].dir || ''
}
const clear = () => {
  pickSequence += 1
  invalidate()
  form.file = null
}
const chooseOutput = async () => {
  const directory = await safely(() => callApiRaw('system_pySelectDirDialog', form.outputDir || ''))
  if (directory) form.outputDir = directory
}
const exportReport = async () => {
  if (!form.file) return ElMessage.warning('请先选择 Excel 文件')
  const revision = ++version
  form.output = ''
  const result = await request('excel_quality_report', { ...payload(), outputDir: form.outputDir }, () => revision === version, [form.file])
  if (result) {
    form.output = result.output || ''
    ElMessage.success(result.msg || '报告已生成')
  }
}
const openOutput = () => form.output && safely(() => callApiRaw('system_pyOpenFile', form.output))
const run = async () => {
  if (!form.file) return ElMessage.warning('请先选择 Excel 文件')
  const revision = ++version
  Object.assign(form, { summary: null, profiles: [], output: '' })
  const result = await request('excel_column_profile', payload(), () => revision === version, [form.file])
  if (result) {
    form.summary = result.summary || null
    form.profiles = result.profiles || []
    ElMessage.success(result.msg || '数据质检完成')
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>Excel 数据质检</h4>
      <p>检查当前工作表的完整数据：缺失值、唯一值、高频值、类型与数值范围，不修改源文件。</p>
    </header>
    <div class="profile-input">
      <div><el-button @click="selectFile">选择 / 接收 Excel</el-button><el-button v-if="form.file" text type="danger" @click="clear">移除主文件</el-button></div>
      <p v-if="form.file" class="input-path">{{ form.file.path }}</p>
      <p>接收只替换主文件；确认工作表后手动开始质检。</p>
    </div>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="result-table" />
    <el-form :model="form" label-width="100px" class="form-block">
      <el-form-item v-if="form.sheets.length" label="工作表"
        ><el-select v-model="form.sheet" style="width: 240px"><el-option v-for="sheet in form.sheets" :key="sheet" :label="sheet" :value="sheet" /></el-select
      ></el-form-item>
      <el-form-item><el-button type="primary" :disabled="!form.file || !form.schemaText" :loading="loading" @click="run">开始质检</el-button><el-button v-if="form.file" :loading="loading" @click="loadPreview">重新读取工作表</el-button></el-form-item>
    </el-form>
    <el-alert v-if="form.summary" type="success" :closable="false" :title="`${form.summary.sheet}：${form.summary.totalRows} 行，${form.summary.columns} 列`" />
    <el-table v-if="rows.length" :data="rows" border size="small" max-height="340" class="result-table">
      <el-table-column prop="field" label="字段" min-width="130" fixed />
      <el-table-column prop="type" label="类型" width="80" /><el-table-column prop="unique" label="唯一值" width="90" /><el-table-column prop="blanks" label="空值" width="75" /><el-table-column prop="blankText" label="空值率" width="85" /> <el-table-column prop="rangeText" label="数值范围" min-width="180" show-overflow-tooltip /><el-table-column prop="topText" label="高频值" min-width="220" show-overflow-tooltip />
    </el-table>
    <div v-if="form.summary" class="report-row">
      <el-input v-model="form.outputDir" placeholder="报告输出目录"
        ><template #append><el-button @click="chooseOutput">选择</el-button></template></el-input
      >
      <el-button :loading="loading" @click="exportReport">导出质量报告</el-button><el-button v-if="form.output" type="primary" plain @click="openOutput">打开报告</el-button>
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
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}
.report-row > .el-input {
  flex: 1 1 240px;
}
.profile-input p {
  color: var(--ppx-text-muted);
  font-size: 12px;
  line-height: 1.6;
}
.profile-input .input-path {
  color: var(--ppx-text-primary);
  overflow-wrap: anywhere;
}
</style>
