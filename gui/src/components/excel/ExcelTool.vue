<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#1f9d55">
    <StructurePanel
      v-show="activeTab === 'structure'"
      :preview="state.preview"
      :loading="state.loading"
      :select-excel="selectExcel"
      :load-preview="loadPreview"
    />

    <ProcessPanel
      v-show="activeTab === 'process'"
      :process="state.process"
      :schema-fields="schemaFields"
      :loading="state.loading"
      :select-excel="selectExcel"
      :select-dir="selectDir"
      :remove-file="removeFile"
      :clear-list="clearList"
      :open-path="openPath"
      :run-process="runProcess"
    />

    <MergePanel
      v-show="activeTab === 'merge'"
      :merge="state.merge"
      :loading="state.loading"
      :select-excel="selectExcel"
      :select-dir="selectDir"
      :remove-file="removeFile"
      :clear-list="clearList"
      :open-path="openPath"
      :run-merge-tables="runMergeTables"
    />

    <section class="panel log-panel">
      <header>
        <h4>操作日志</h4>
        <p>展示最近的执行记录与返回信息</p>
      </header>
      <el-timeline>
        <el-timeline-item
          v-for="item in state.logs"
          :key="item.id"
          :type="item.type"
          :timestamp="item.time"
          placement="top"
        >
          <div class="log-entry">
            <p>{{ item.message }}</p>
            <p class="log-sub">{{ item.action }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </section>
  </ToolWorkspace>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import StructurePanel from './parts/StructurePanel.vue'
import ProcessPanel from './parts/ProcessPanel.vue'
import MergePanel from './parts/MergePanel.vue'

const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']

const TABS = [
  { name: 'structure', label: '结构定义' },
  { name: 'process', label: '数据处理' },
  { name: 'merge', label: '分表合并' },
]

const activeTab = ref('structure')

const state = reactive({
  loading: false,
  preview: {
    file: null,
    sheet: '',
    sheets: [],
    delimiter: '|',
    schemaText: '',
    schema: [],
    sample: [],
    rowCount: 0
  },
  process: {
    groupBy: '',
    sortBy: '',
    sortOrder: 'asc',
    exportGroups: true,
    exportJson: true,
    exportCombined: false,
    outputDir: '',
    summary: null,
    groups: [],
    groupFiles: [],
    jsonPath: '',
    combinedPath: '',
    mergeFiles: []
  },
  merge: {
    tables: [],
    outputDir: '',
    outputName: '合并主表.xlsx',
    result: ''
  },
  logs: []
})

const schemaFields = computed(() => state.preview.schema)

let suppressSheetReload = false

watch(
  () => state.preview.sheet,
  (val, oldVal) => {
    if (suppressSheetReload) return
    if (val === oldVal) return
    if (state.preview.file) {
      loadPreview(true)
    }
  }
)

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const callApi = async (method, payload) => {
  if (!ensurePyReady()) return null
  if (!window.pywebview.api[method]) {
    ElMessage.error('当前客户端版本缺少 Excel 能力')
    return null
  }
  state.loading = true
  try {
    // 统一封装：归一化返回 { ok, message, data }
    const result = await pyCall(method, payload)
    if (result.ok) {
      ElMessage.success(result.message || '操作成功')
      pushLog('success', result.message || '操作成功', method)
      return result.data
    }
    const msg = result.message || '操作失败'
    ElMessage.error(msg)
    pushLog('warning', msg, method)
    return null
  } catch (error) {
    ElMessage.error(error.message || '执行失败')
    pushLog('danger', error.message || '执行失败', method)
    return null
  } finally {
    state.loading = false
  }
}

const pushLog = (type, message, action) => {
  state.logs.unshift({
    id: Date.now() + Math.random(),
    type,
    message,
    action,
    time: new Date().toLocaleTimeString()
  })
  if (state.logs.length > 6) {
    state.logs.pop()
  }
}

const selectExcel = async (target, multiple = false) => {
  if (!ensurePyReady()) return
  const result = await callApiRaw('system_pyCreateFileDialog', excelFilter)
  if (!result || !result.length) return
  if (target === 'preview') {
    state.preview.file = result[0]
    resetPreviewData()
    await loadPreview(true)
    return
  }
  const files = multiple ? result : [result[0]]
  const mapped = files.map((item) => ({
    ...item,
    sheet: '',
    id: `${item.path}_${Math.random().toString(16).slice(2)}`
  }))
  if (target === 'processMerge') {
    state.process.mergeFiles.push(...mapped)
  } else if (target === 'mergeTables') {
    state.merge.tables.push(...mapped)
  }
}

const resetPreviewData = () => {
  suppressSheetReload = true
  state.preview.sheet = ''
  suppressSheetReload = false
  state.preview.sheets = []
  state.preview.schema = []
  state.preview.schemaText = ''
  state.preview.sample = []
  state.preview.rowCount = 0
  state.process.groupBy = ''
  state.process.sortBy = ''
  state.process.summary = null
  state.process.groups = []
  state.process.groupFiles = []
  state.process.jsonPath = ''
  state.process.combinedPath = ''
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const current =
    target === 'process'
      ? state.process.outputDir
      : state.merge.outputDir
  const dir = await callApiRaw('system_pySelectDirDialog', current || '')
  if (!dir) return
  if (target === 'process') {
    state.process.outputDir = dir
  } else {
    state.merge.outputDir = dir
  }
}

const removeFile = (target, index) => {
  if (target === 'processMerge') {
    state.process.mergeFiles.splice(index, 1)
  } else {
    state.merge.tables.splice(index, 1)
  }
}

const clearList = (target) => {
  if (target === 'processMerge') {
    state.process.mergeFiles.splice(0, state.process.mergeFiles.length)
  } else {
    state.merge.tables.splice(0, state.merge.tables.length)
  }
}

const openPath = (path) => {
  if (!path || !ensurePyReady()) return
  callApiRaw('system_pyOpenFile', path)
}

const loadPreview = async (silent = false) => {
  if (!state.preview.file) {
    if (!silent) {
      ElMessage.warning('请选择 Excel 文件')
    }
    return
  }
  const res = await callApi('excel_preview', {
    filePath: state.preview.file.path,
    sheetName: state.preview.sheet,
    delimiter: state.preview.delimiter || '|',
    schemaText: state.preview.schemaText
  })
  if (!res) return
  state.preview.schema = res.schema || []
  state.preview.delimiter = res.delimiter || state.preview.delimiter || '|'
  state.preview.schemaText = res.schemaText || state.preview.schema.join(state.preview.delimiter || '|')
  state.preview.rowCount = res.rowCount || 0
  state.preview.sample = res.sample || []
  state.preview.sheets = res.sheets || []
  if (!state.preview.sheet && res.sheet) {
    suppressSheetReload = true
    state.preview.sheet = res.sheet
    suppressSheetReload = false
  }
}

const runProcess = async () => {
  if (!state.preview.file) {
    ElMessage.warning('请先完成结构定义')
    return
  }
  const payload = {
    filePath: state.preview.file.path,
    sheetName: state.preview.sheet,
    delimiter: state.preview.delimiter || '|',
    schemaText: state.preview.schemaText,
    groupBy: state.process.groupBy,
    sortBy: state.process.sortBy,
    sortOrder: state.process.sortOrder,
    outputDir: state.process.outputDir,
    exportGroups: state.process.exportGroups,
    exportJson: state.process.exportJson,
    exportCombined: state.process.exportCombined,
    mergeFiles: state.process.mergeFiles.map((item) => ({
      path: item.path,
      sheet: item.sheet
    }))
  }
  const res = await callApi('excel_process', payload)
  if (!res) return
  state.process.summary = res.summary
  state.process.groups = res.groups || []
  state.process.groupFiles = res.groupFiles || []
  state.process.jsonPath = res.jsonPath || ''
  state.process.combinedPath = res.combinedPath || ''
  if (res.schema) {
    state.preview.schema = res.schema
  }
}

const runMergeTables = async () => {
  if (!state.merge.tables.length) {
    ElMessage.warning('请先选择需要合并的分表')
    return
  }
  const res = await callApi('excel_merge_tables', {
    tables: state.merge.tables.map((item) => ({
      path: item.path,
      sheet: item.sheet
    })),
    schemaText: state.preview.schemaText,
    delimiter: state.preview.delimiter || '|',
    outputDir: state.merge.outputDir,
    outputName: state.merge.outputName
  })
  if (!res) return
  state.merge.result = res.output
}
</script>

<style scoped>
/* 使用全局深空玻璃主题样式 */

/* 日志面板 */
.log-panel header {
  margin-bottom: 10px;
}

.log-panel header h4 {
  margin: 0;
  color: var(--ppx-text-primary);
}

.log-panel header p {
  margin: 6px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-sub {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>
