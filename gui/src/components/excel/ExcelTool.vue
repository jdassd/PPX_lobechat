<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#1f9d55">
    <section class="panel">
      <el-form inline>
        <el-form-item label="表头所在行"><el-input-number v-model="rules.headerRow" :min="1" :max="1048576" /></el-form-item>
        <el-form-item label="公式处理"
          ><el-select v-model="rules.formulaPolicy" style="width: 200px"><el-option label="保留本行相对引用" value="preserve" /><el-option label="使用已保存的缓存值" value="values" /></el-select
        ></el-form-item>
        <el-form-item v-if="['process', 'merge'].includes(activeTab)"><el-checkbox v-model="rules.trimText">去除文本首尾空格</el-checkbox></el-form-item>
      </el-form>
      <el-alert title="表头与公式规则用于当前读取和执行。质检不清洗原始数据；处理输出为新的 xlsx，不保留宏。公式仅支持本行相对引用，缓存值需先在 Excel 中计算并保存。" type="info" :closable="false" />
    </section>
    <el-alert v-if="error && activeTab !== 'profile'" :title="error" type="error" show-icon :closable="false" class="excel-error" />
    <StructurePanel v-show="activeTab === 'structure'" :preview="state.preview" :loading="loading" :select-excel="selectExcel" :load-preview="loadPreview" :clear-input="clearInput" />
    <ProfilePanel v-show="activeTab === 'profile'" :rules="rules" />
    <ProcessPanel v-show="activeTab === 'process'" :preview="state.preview" :process="state.process" :schema-fields="schemaFields" :loading="loading" :select-excel="selectExcel" :select-dir="selectDir" :remove-file="removeFile" :clear-list="clearList" :open-path="openPath" :run-process="runProcess" :clear-input="clearInput" :load-preview="loadPreview">
      <el-form-item label="去重字段"
        ><el-select v-model="rules.deduplicateColumns" multiple clearable placeholder="留空不去重" style="width: 100%"><el-option v-for="field in schemaFields" :key="field" :value="field" :label="field" /></el-select
      ></el-form-item>
      <template #comparison>
        <p class="scope-note">比较仅展示有界样本；执行处理会读取完整数据，包括附加分表。样本不能代替全表去重、排序或分组结果。</p>
        <el-button :disabled="!state.preview.file || !schemaFields.length" :loading="loading" @click="previewProcess">比较处理前后样本</el-button>
        <p v-if="comparison">{{ comparison.msg }}</p>
        <div v-if="comparison" class="comparison-grid">
          <el-table :data="comparison.before || []" max-height="260"><el-table-column v-for="field in schemaFields" :key="field" :prop="field" :label="'处理前 · ' + field" min-width="130" /></el-table>
          <el-table :data="comparison.after || []" max-height="260"><el-table-column v-for="field in schemaFields" :key="field" :prop="field" :label="'处理后 · ' + field" min-width="130" /></el-table>
        </div>
      </template>
    </ProcessPanel>
    <SplitPanel v-show="activeTab === 'split'" :rules="rules" />
    <MergePanel v-show="activeTab === 'merge'" :merge="state.merge" :loading="loading" :select-excel="selectExcel" :select-dir="selectDir" :remove-file="removeFile" :clear-list="clearList" :open-path="openPath" :run-merge-tables="runMergeTables" :load-table-columns="loadTableColumns" />
    <section v-if="state.logs.length" class="panel log-panel">
      <header>
        <h4>操作日志</h4>
        <p>最近执行记录；当前文件的结果显示在上方</p>
      </header>
      <el-timeline
        ><el-timeline-item v-for="item in state.logs" :key="item.id" :type="item.type" :timestamp="item.time" placement="top"
          ><p>{{ item.message }}</p>
          <p class="scope-note">{{ item.action }}</p></el-timeline-item
        ></el-timeline
      >
    </section>
  </ToolWorkspace>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { mergeFileQueue, useDraft } from '../../utils/workspace'
import { callApiRaw, selectInputFiles } from '@/utils/pyapi'
import { useInitialTab } from '@/composables/useInitialTab'
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import StructurePanel from './parts/StructurePanel.vue'
import ProfilePanel from './parts/ProfilePanel.vue'
import ProcessPanel from './parts/ProcessPanel.vue'
import SplitPanel from './parts/SplitPanel.vue'
import MergePanel from './parts/MergePanel.vue'
import { useExcelRequest } from './useExcelRequest'

const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const TABS = [
  { name: 'structure', label: '结构定义' },
  { name: 'profile', label: '数据质检' },
  { name: 'process', label: '清洗与处理' },
  { name: 'split', label: '按列拆分' },
  { name: 'merge', label: '分表合并' }
]
const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = useInitialTab(TABS, () => props.initialTab, 'structure')
const rules = useDraft('excel/options', { headerRow: 1, formulaPolicy: 'preserve', trimText: false, deduplicateColumns: [] })
const comparison = ref(null)
const state = useDraft('excel/ExcelTool/state', {
  preview: { file: null, sheet: '', sheets: [], delimiter: '|', schemaText: '', schema: [], sample: [], rowCount: 0 },
  process: { groupBy: '', sortBy: '', sortOrder: 'asc', exportGroups: true, exportJson: true, exportCombined: true, outputDir: '', summary: null, groups: [], groupFiles: [], jsonPath: '', combinedPath: '', mergeFiles: [] },
  merge: { tables: [], outputDir: '', outputName: '合并主表.xlsx', result: '' },
  logs: []
})
const schemaFields = computed(() => state.preview.schema)
const pushLog = (type, message, action) => {
  state.logs.unshift({ id: Date.now() + Math.random(), type, message, action, time: new Date().toLocaleTimeString() })
  state.logs.splice(6)
}
const { loading, error, request, safely } = useExcelRequest(pushLog)
let inputVersion = 0
let previewSequence = 0
let processSequence = 0
let mergeSequence = 0
let selectionSequence = 0
let settingSheet = false
const readingRules = () => ({ headerRow: rules.headerRow, formulaPolicy: rules.formulaPolicy, trimText: false, deduplicateColumns: [] })
const clearResults = () => {
  processSequence += 1
  comparison.value = null
  Object.assign(state.process, { summary: null, groups: [], groupFiles: [], jsonPath: '', combinedPath: '' })
}
const resetPreviewData = () => {
  inputVersion += 1
  previewSequence += 1
  clearResults()
  error.value = ''
  Object.assign(state.preview, { schema: [], schemaText: '', sample: [], rowCount: 0 })
  state.process.groupBy = ''
  state.process.sortBy = ''
  state.process.mergeFiles = []
  rules.deduplicateColumns = []
}
const clearInput = () => {
  selectionSequence += 1
  state.preview.file = null
}
const loadPreview = async () => {
  if (!state.preview.file) return ElMessage.warning('请选择 Excel 文件')
  clearResults()
  const sequence = ++previewSequence
  const version = inputVersion
  const current = () => sequence === previewSequence && version === inputVersion
  const res = await request(
    'excel_preview',
    {
      filePath: state.preview.file.path,
      sheetName: state.preview.sheet,
      delimiter: state.preview.delimiter || '|',
      schemaText: state.preview.schemaText,
      ...readingRules()
    },
    current
  )
  if (!res) return
  settingSheet = true
  state.preview.sheet = res.sheet || state.preview.sheet
  settingSheet = false
  Object.assign(state.preview, {
    schema: res.schema || [],
    delimiter: res.delimiter || '|',
    schemaText: res.schemaText || (res.schema || []).join(res.delimiter || '|'),
    rowCount: res.rowCount || 0,
    sample: res.sample || [],
    sheets: res.sheets || []
  })
}
watch(
  () => state.preview.file,
  () => {
    resetPreviewData()
    settingSheet = true
    state.preview.sheet = ''
    settingSheet = false
    state.preview.sheets = []
    if (state.preview.file) loadPreview()
  },
  { flush: 'sync' }
)
watch(
  () => state.preview.sheet,
  () => {
    if (settingSheet) return
    resetPreviewData()
    if (state.preview.file) loadPreview()
  },
  { flush: 'sync' }
)
watch(
  () => [rules.headerRow, rules.formulaPolicy],
  () => {
    resetPreviewData()
    if (state.preview.file) loadPreview()
    mergeSequence += 1
    state.merge.result = ''
    state.merge.tables.forEach((item) => loadTableColumns(item))
  },
  { flush: 'sync' }
)
watch(() => [rules.trimText, ...rules.deduplicateColumns, state.process.groupBy, state.process.sortBy, state.process.sortOrder, state.preview.schemaText, state.preview.delimiter, JSON.stringify(state.process.mergeFiles)], clearResults, { flush: 'sync' })
watch(
  () => [rules.trimText, JSON.stringify(state.merge.tables)],
  () => {
    mergeSequence += 1
    state.merge.result = ''
  },
  { flush: 'sync' }
)

const loadTableColumns = async (item) => {
  const revision = (item.revision || 0) + 1
  item.revision = revision
  item.columns = []
  item.fieldMapping = {}
  const current = () => item.revision === revision && state.merge.tables.includes(item)
  const result = await request('excel_preview', { filePath: item.path, sheetName: item.sheet, limit: 1, ...readingRules() }, current)
  if (result) item.columns = result.schema || []
}
const selectExcel = async (target, multiple = false) => {
  const sequence = ++selectionSequence
  const version = inputVersion
  const result = await safely(() => (target === 'mergeTables' ? selectInputFiles('excel/merge', excelFilter) : target === 'processInput' ? selectInputFiles('excel/process', excelFilter) : callApiRaw('system_pyCreateFileDialog', excelFilter)))
  if (sequence !== selectionSequence || !result?.length) return
  if (target === 'preview' || target === 'processInput') {
    state.preview.file = { ...result[0] }
    return
  }
  if (target === 'processMerge' && version !== inputVersion) return
  const mapped = (multiple ? result : [result[0]]).map((item) => ({ ...item, sheet: '', fieldMapping: {}, columns: [] }))
  if (target === 'processMerge') state.process.mergeFiles = mergeFileQueue(state.process.mergeFiles, mapped)
  else {
    state.merge.tables = mergeFileQueue(state.merge.tables, mapped)
    state.merge.tables.filter((item) => !item.columns.length).forEach((item) => loadTableColumns(item))
  }
}
const selectDir = async (target) => {
  const form = target === 'process' ? state.process : state.merge
  const dir = await safely(() => callApiRaw('system_pySelectDirDialog', form.outputDir || ''))
  if (dir) form.outputDir = dir
}
const removeFile = (target, index) => {
  const list = target === 'processMerge' ? state.process.mergeFiles : state.merge.tables
  list.splice(index, 1)
}
const clearList = (target) => {
  selectionSequence += 1
  const list = target === 'processMerge' ? state.process.mergeFiles : state.merge.tables
  list.splice(0)
}
const openPath = (path) => path && safely(() => callApiRaw('system_pyOpenFile', path))
const processPayload = () => ({
  filePath: state.preview.file.path,
  sheetName: state.preview.sheet,
  delimiter: state.preview.delimiter || '|',
  schemaText: state.preview.schemaText,
  headerRow: rules.headerRow,
  formulaPolicy: rules.formulaPolicy,
  trimText: rules.trimText,
  deduplicateColumns: [...rules.deduplicateColumns],
  groupBy: state.process.groupBy,
  sortBy: state.process.sortBy,
  sortOrder: state.process.sortOrder,
  outputDir: state.process.outputDir,
  exportGroups: state.process.exportGroups,
  exportJson: state.process.exportJson,
  exportCombined: state.process.exportCombined,
  mergeFiles: state.process.mergeFiles.map((item) => ({ path: item.path, sheet: item.sheet, fieldMapping: { ...item.fieldMapping } }))
})
const previewProcess = async () => {
  if (!state.preview.file || !schemaFields.value.length) return ElMessage.warning('请先选择 Excel 并读取工作表')
  const sequence = ++processSequence
  comparison.value = null
  const res = await request('excel_process_preview', processPayload(), () => sequence === processSequence)
  if (res) comparison.value = res
}
const runProcess = async () => {
  if (!state.preview.file || !schemaFields.value.length) return ElMessage.warning('请先选择 Excel 并读取工作表')
  clearResults()
  const sequence = processSequence
  const res = await request('excel_process', processPayload(), () => sequence === processSequence, [state.preview.file])
  if (!res) return
  Object.assign(state.process, { summary: res.summary, groups: res.groups || [], groupFiles: res.groupFiles || [], jsonPath: res.jsonPath || '', combinedPath: res.combinedPath || '' })
  ElMessage.success(res.msg || '完整数据处理完成')
}
const runMergeTables = async () => {
  if (!state.merge.tables.length) return ElMessage.warning('请先选择需要合并的分表')
  const sequence = ++mergeSequence
  state.merge.result = ''
  const res = await request(
    'excel_merge_tables',
    {
      tables: state.merge.tables.map((item) => ({ path: item.path, sheet: item.sheet, fieldMapping: { ...item.fieldMapping } })),
      delimiter: '|',
      schemaText: '',
      ...readingRules(),
      trimText: rules.trimText,
      outputDir: state.merge.outputDir,
      outputName: state.merge.outputName
    },
    () => sequence === mergeSequence,
    state.merge.tables
  )
  if (res) {
    state.merge.result = res.output
    ElMessage.success(res.msg || '合并完成')
  }
}
</script>

<style scoped>
.excel-error {
  margin-bottom: 14px;
}
.comparison-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 12px;
}
.scope-note,
.log-panel header p {
  color: var(--ppx-text-muted);
  font-size: 12px;
  line-height: 1.6;
}
.log-panel header {
  margin-bottom: 14px;
}
@media (max-width: 1100px) {
  .comparison-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
