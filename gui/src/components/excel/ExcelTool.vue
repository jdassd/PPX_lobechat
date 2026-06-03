<template>
  <el-drawer
    v-model="visibleProxy"
    size="80%"
    append-to-body
    custom-class="excel-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">EXCEL WORKSHOP</p>
          <h3>Excel 工具集</h3>
          <p class="sub">支持结构定义、按列分组、分表导出与 JSON 图表</p>
        </div>
      </div>
    </template>
    <div class="excel-tool">
      <el-tabs v-model="activeTab" class="excel-tabs">
        <el-tab-pane label="结构定义" name="structure">
          <StructurePanel
            :preview="state.preview"
            :loading="state.loading"
            :select-excel="selectExcel"
            :load-preview="loadPreview"
          />
        </el-tab-pane>

        <el-tab-pane label="数据处理" name="process">
          <ProcessPanel
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
        </el-tab-pane>

        <el-tab-pane label="图表制作" name="chart">
          <ChartPanel
            :chart="state.chart"
            :chart-fields="chartFields"
            :loading="state.loading"
            :chart-data-sample="chartDataSample"
            :chart-option-sample="chartOptionSample"
            :select-excel="selectExcel"
            :load-chart-preview="loadChartPreview"
            :run-chart-build="runChartBuild"
            :set-chart-ref="setChartRef"
          />
        </el-tab-pane>

        <el-tab-pane label="分表合并" name="merge">
          <MergePanel
            :merge="state.merge"
            :loading="state.loading"
            :select-excel="selectExcel"
            :select-dir="selectDir"
            :remove-file="removeFile"
            :clear-list="clearList"
            :open-path="openPath"
            :run-merge-tables="runMergeTables"
          />
        </el-tab-pane>
      </el-tabs>

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
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted, onUnmounted, nextTick, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'
import StructurePanel from './parts/StructurePanel.vue'
import ProcessPanel from './parts/ProcessPanel.vue'
import ChartPanel from './parts/ChartPanel.vue'
import MergePanel from './parts/MergePanel.vue'

const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const chartDataSample = JSON.stringify(
  {
    dimension: '地区',
    metric: '销量',
    aggregate: 'sum',
    rows: [
      { name: '华北', value: 120 },
      { name: '华东', value: 98 },
      { name: '华南', value: 76 }
    ]
  },
  null,
  2
)
const chartOptionSample = JSON.stringify(
  {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['华北', '华东', '华南'] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: [120, 98, 76] }]
  },
  null,
  2
)

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

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
  chart: {
    file: null,
    sheet: '',
    sheets: [],
    delimiter: '|',
    schemaText: '',
    schema: [],
    chartType: 'bar',
    dimension: '',
    metric: '',
    aggregate: 'sum',
    data: null,
    option: null,
    dataJson: '',
    optionJson: ''
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
const chartFields = computed(() => state.chart.schema)

let suppressSheetReload = false
let suppressChartReload = false

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

watch(
  () => state.chart.sheet,
  (val, oldVal) => {
    if (suppressChartReload) return
    if (val === oldVal) return
    if (state.chart.file) {
      loadChartPreview(true)
    }
  }
)

watch(
  () => state.chart.aggregate,
  (val) => {
    if (val === 'count') {
      state.chart.metric = ''
    }
  }
)

watch(
  () => state.chart.schema,
  (schema) => {
    if (!schema.includes(state.chart.dimension)) {
      state.chart.dimension = ''
    }
    if (!schema.includes(state.chart.metric)) {
      state.chart.metric = ''
    }
  },
  { deep: true }
)

const chartRef = ref(null)
const chartInstance = shallowRef(null)

// 由 ChartPanel 通过函数 ref 回传画布 DOM，使壳继续统一管理 echarts 生命周期
const setChartRef = (el) => {
  chartRef.value = el
}

const renderChart = async () => {
  if (!chartRef.value || !state.chart.option) return
  await nextTick()
  if (!chartInstance.value) {
    chartInstance.value = echarts.init(chartRef.value)
  }
  chartInstance.value.setOption(state.chart.option, true)
}

const resizeChart = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

const disposeChart = () => {
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
}

onMounted(() => {
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  disposeChart()
})

watch(
  () => activeTab.value,
  (val) => {
    if (val === 'chart') {
      renderChart()
      nextTick(() => resizeChart())
    }
  }
)

watch(
  () => state.chart.option,
  () => {
    if (activeTab.value === 'chart') {
      renderChart()
    }
  }
)

watch(
  () => props.modelValue,
  (val) => {
    if (!val) {
      disposeChart()
      return
    }
    if (activeTab.value === 'chart') {
      renderChart()
      nextTick(() => resizeChart())
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
  if (target === 'chart') {
    state.chart.file = result[0]
    resetChartData()
    await loadChartPreview(true)
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

const resetChartData = () => {
  suppressChartReload = true
  state.chart.sheet = ''
  suppressChartReload = false
  state.chart.sheets = []
  state.chart.schema = []
  state.chart.schemaText = ''
  state.chart.dimension = ''
  state.chart.metric = ''
  state.chart.data = null
  state.chart.option = null
  state.chart.dataJson = ''
  state.chart.optionJson = ''
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

const loadChartPreview = async (silent = false) => {
  if (!state.chart.file) {
    if (!silent) {
      ElMessage.warning('请选择 Excel 文件')
    }
    return
  }
  const res = await callApi('excel_preview', {
    filePath: state.chart.file.path,
    sheetName: state.chart.sheet,
    delimiter: state.chart.delimiter || '|',
    schemaText: state.chart.schemaText
  })
  if (!res) return
  state.chart.schema = res.schema || []
  state.chart.delimiter = res.delimiter || state.chart.delimiter || '|'
  state.chart.schemaText = res.schemaText || state.chart.schema.join(state.chart.delimiter || '|')
  state.chart.sheets = res.sheets || []
  if (!state.chart.sheet && res.sheet) {
    suppressChartReload = true
    state.chart.sheet = res.sheet
    suppressChartReload = false
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

const runChartBuild = async () => {
  if (!state.chart.file) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  if (!state.chart.dimension) {
    ElMessage.warning('请选择维度列')
    return
  }
  if (state.chart.aggregate !== 'count' && !state.chart.metric) {
    ElMessage.warning('请选择数值列')
    return
  }
  const payload = {
    filePath: state.chart.file.path,
    sheetName: state.chart.sheet,
    delimiter: state.chart.delimiter || '|',
    schemaText: state.chart.schemaText,
    chartType: state.chart.chartType,
    dimension: state.chart.dimension,
    metric: state.chart.metric,
    aggregate: state.chart.aggregate
  }
  const res = await callApi('excel_chart_build', payload)
  if (!res) return
  state.chart.data = res.data || null
  state.chart.option = res.option || null
  state.chart.dataJson = res.data ? JSON.stringify(res.data, null, 2) : ''
  state.chart.optionJson = res.option ? JSON.stringify(res.option, null, 2) : ''
  renderChart()
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
