<template>
  <el-drawer
    v-model="visibleProxy"
    size="70%"
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
        <el-tag type="primary" size="large">Preview</el-tag>
      </div>
    </template>
    <div class="excel-tool">
      <el-tabs v-model="activeTab" class="excel-tabs">
        <el-tab-pane label="结构定义" name="structure">
          <section class="panel">
            <header>
              <h4>配置固定格式</h4>
              <p>定义第一行字段、选择工作表并预览样例数据</p>
            </header>
            <el-form :model="state.preview" label-width="110px">
              <el-form-item label="源 Excel">
                <div class="field-row">
                  <el-button type="primary" @click="selectExcel('preview')">选择文件</el-button>
                  <span v-if="state.preview.file" class="file-chip">{{ state.preview.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
                </div>
              </el-form-item>
              <el-form-item v-if="state.preview.sheets.length" label="工作表">
                <el-select v-model="state.preview.sheet" style="width: 220px">
                  <el-option v-for="sheet in state.preview.sheets" :key="sheet" :label="sheet" :value="sheet" />
                </el-select>
              </el-form-item>
              <el-form-item label="分隔符">
                <el-input
                  v-model="state.preview.delimiter"
                  placeholder="默认使用 |"
                  maxlength="4"
                  style="width: 120px"
                />
              </el-form-item>
              <el-form-item label="结构定义">
                <el-input
                  v-model="state.preview.schemaText"
                  type="textarea"
                  :rows="2"
                  placeholder="示例：姓名|手机号|地区|业务类型"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="loadPreview">刷新预览</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.preview.schema.length" class="schema-chips">
              <p class="result-title">字段结构</p>
              <div class="schema-tags">
                <el-tag
                  v-for="field in state.preview.schema"
                  :key="field"
                  size="large"
                  effect="plain"
                >
                  {{ field }}
                </el-tag>
              </div>
              <p class="schema-note">总行数：{{ state.preview.rowCount }} · 当前工作表：{{ state.preview.sheet || '默认' }}</p>
            </div>
            <div v-if="state.preview.sample.length" class="result-block">
              <p class="result-title">样例数据</p>
              <el-table
                :data="state.preview.sample"
                height="260"
                border
                size="small"
                header-cell-class-name="table-header"
              >
                <el-table-column
                  v-for="field in state.preview.schema"
                  :key="field"
                  :prop="field"
                  :label="field"
                  show-overflow-tooltip
                />
              </el-table>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="数据处理" name="process">
          <section class="panel">
            <header>
              <h4>分组 / 排序 / 导出</h4>
              <p>按照指定列拆分分表，可选导出 JSON 供图表使用</p>
            </header>
            <el-form :model="state.process" label-width="120px">
              <el-form-item label="按列分组">
                <el-select v-model="state.process.groupBy" placeholder="可选" clearable style="width: 220px">
                  <el-option
                    v-for="field in schemaFields"
                    :key="field"
                    :label="field"
                    :value="field"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="排序字段">
                <div class="field-row">
                  <el-select v-model="state.process.sortBy" placeholder="可选" clearable style="width: 220px">
                    <el-option
                      v-for="field in schemaFields"
                      :key="field"
                      :label="field"
                      :value="field"
                    />
                  </el-select>
                  <el-radio-group v-model="state.process.sortOrder" size="small">
                    <el-radio-button label="asc">升序</el-radio-button>
                    <el-radio-button label="desc">降序</el-radio-button>
                  </el-radio-group>
                </div>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input
                    v-model="state.process.outputDir"
                    placeholder="留空则自动创建"
                    readonly
                  />
                  <el-button @click="selectDir('process')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="导出选项">
                <div class="toggle-row">
                  <el-checkbox v-model="state.process.exportGroups" :disabled="!state.process.groupBy">
                    分组导出 Excel
                  </el-checkbox>
                  <el-checkbox v-model="state.process.exportJson" :disabled="!state.process.groupBy">
                    导出 JSON 图表
                  </el-checkbox>
                  <el-checkbox v-model="state.process.exportCombined">
                    合并主表
                  </el-checkbox>
                </div>
              </el-form-item>
            </el-form>

            <div class="subpanel">
              <div class="subpanel-head">
                <div>
                  <h5>附加分表</h5>
                  <p>支持在主表前批量合并多个分表，再进入分组流程</p>
                </div>
                <div class="field-row">
                  <el-button size="small" @click="selectExcel('processMerge', true)">添加分表</el-button>
                  <el-button size="small" text type="danger" @click="clearList('processMerge')" :disabled="!state.process.mergeFiles.length">
                    清空
                  </el-button>
                </div>
              </div>
              <el-table
                v-if="state.process.mergeFiles.length"
                :data="state.process.mergeFiles"
                size="small"
                border
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column prop="filename" label="文件名" />
                <el-table-column label="工作表" width="220">
                  <template #default="scope">
                    <el-input
                      v-model="scope.row.sheet"
                      size="small"
                      placeholder="留空使用默认工作表"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="scope">
                    <el-button link type="danger" @click="removeFile('processMerge', scope.$index)">移除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-else description="尚未添加分表" />
            </div>

            <div class="actions">
              <el-button type="primary" :loading="state.loading" @click="runProcess">执行处理</el-button>
            </div>

            <div v-if="state.process.summary" class="result-block">
              <p class="result-title">处理摘要</p>
              <el-descriptions :column="2" size="small" border>
                <el-descriptions-item label="总行数">
                  {{ state.process.summary.totalRows }}
                </el-descriptions-item>
                <el-descriptions-item label="分组列">
                  {{ state.process.summary.groupBy || '未设置' }}
                </el-descriptions-item>
                <el-descriptions-item label="排序列">
                  {{ state.process.summary.sortBy || '未设置' }}（{{ state.process.summary.sortOrder === 'desc' ? '降序' : '升序' }}）
                </el-descriptions-item>
                <el-descriptions-item label="分组数量">
                  {{ state.process.summary.groupCount }}
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="state.process.groups.length" class="group-table">
                <el-table :data="state.process.groups" size="small" border>
                  <el-table-column prop="key" label="分组值" />
                  <el-table-column prop="count" label="行数" width="120" />
                </el-table>
              </div>

              <div class="result-list">
                <template v-if="state.process.groupFiles.length">
                  <p class="result-title">分组文件</p>
                  <el-scrollbar max-height="140px">
                    <div class="tag-list">
                      <el-tag
                        v-for="file in state.process.groupFiles"
                        :key="file"
                        type="success"
                        effect="plain"
                        @click="openPath(file)"
                      >
                        {{ file }}
                      </el-tag>
                    </div>
                  </el-scrollbar>
                </template>

                <div class="tag-list">
                  <el-tag
                    v-if="state.process.jsonPath"
                    type="info"
                    effect="plain"
                    @click="openPath(state.process.jsonPath)"
                  >
                    JSON：{{ state.process.jsonPath }}
                  </el-tag>
                  <el-tag
                    v-if="state.process.combinedPath"
                    type="warning"
                    effect="plain"
                    @click="openPath(state.process.combinedPath)"
                  >
                    主表：{{ state.process.combinedPath }}
                  </el-tag>
                </div>
              </div>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="分表合并" name="merge">
          <section class="panel">
            <header>
              <h4>独立合并工具</h4>
              <p>将多个分表统一导出为一个 Excel，方便生成主表</p>
            </header>
            <div class="subpanel">
              <div class="subpanel-head">
                <div>
                  <h5>分表列表</h5>
                  <p>支持批量选择或多次添加</p>
                </div>
                <div class="field-row">
                  <el-button size="small" @click="selectExcel('mergeTables', true)">选择文件</el-button>
                  <el-button
                    size="small"
                    text
                    type="danger"
                    @click="clearList('mergeTables')"
                    :disabled="!state.merge.tables.length"
                  >
                    清空
                  </el-button>
                </div>
              </div>
              <el-table
                v-if="state.merge.tables.length"
                :data="state.merge.tables"
                size="small"
                border
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column prop="filename" label="文件名" />
                <el-table-column label="工作表" width="220">
                  <template #default="scope">
                    <el-input
                      v-model="scope.row.sheet"
                      size="small"
                      placeholder="留空使用默认工作表"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="scope">
                    <el-button link type="danger" @click="removeFile('mergeTables', scope.$index)">移除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-else description="尚未添加分表" />
            </div>
            <el-form :model="state.merge" label-width="120px" class="merge-form">
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.merge.outputDir" readonly placeholder="留空自动创建" />
                  <el-button @click="selectDir('merge')">选择目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="输出文件名">
                <el-input v-model="state.merge.outputName" placeholder="例如：汇总主表.xlsx" />
              </el-form-item>
            </el-form>
            <div class="actions">
              <el-button type="primary" :loading="state.loading" @click="runMergeTables">
                开始合并
              </el-button>
            </div>
            <div v-if="state.merge.result" class="result-block">
              <p class="result-title">输出结果</p>
              <el-tag type="success" effect="plain" @click="openPath(state.merge.result)">
                {{ state.merge.result }}
              </el-tag>
            </div>
          </section>
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
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const excelFilter = ['Excel 文件 (*.xlsx;*.xlsm;*.xltx;*.xltm)']

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
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const callApi = async (method, payload) => {
  if (!ensurePyReady()) return null
  const api = window.pywebview.api
  if (!api[method]) {
    ElMessage.error('当前客户端版本缺少 Excel 能力')
    return null
  }
  state.loading = true
  try {
    const res = await api[method](payload)
    if (res?.code === 0) {
      ElMessage.success(res.msg || '操作成功')
      pushLog('success', res.msg || '操作成功', method)
      return res
    }
    const msg = res?.msg || '操作失败'
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
  const result = await window.pywebview.api.system_pyCreateFileDialog(excelFilter)
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
  const dir = await window.pywebview.api.system_pySelectDirDialog(current || '')
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
  window.pywebview.api.system_pyOpenFile(path)
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
.excel-tool-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding-bottom: 0;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.drawer-head h3 {
  margin: 4px 0;
  font-size: 24px;
}

.drawer-head .eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.2em;
  color: #7a8093;
}

.drawer-head .sub {
  margin: 0;
  color: #6c7185;
  font-size: 14px;
}

.excel-tool {
  padding-right: 12px;
}

.excel-tabs {
  margin-bottom: 20px;
}

.panel {
  background: #fdfdff;
  padding: 20px;
  border: 1px solid #edf0f5;
  border-radius: 18px;
  margin-bottom: 24px;
}

.panel header h4 {
  margin: 0;
}

.panel header p {
  margin: 6px 0 0;
  color: #7a8093;
  font-size: 13px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-chip {
  padding: 6px 10px;
  border-radius: 8px;
  background: #eef2ff;
  color: #4058d7;
  font-size: 13px;
}

.schema-chips {
  margin-top: 10px;
}

.schema-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.schema-note {
  margin: 8px 0 0;
  font-size: 12px;
  color: #868c9f;
}

.result-block {
  margin-top: 16px;
}

.result-title {
  margin: 0 0 10px;
  font-weight: 600;
  color: #4d5366;
}

.table-header {
  background: #f0f2f9 !important;
}

.toggle-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.subpanel {
  margin-top: 18px;
  border: 1px dashed #dbe1ee;
  border-radius: 14px;
  padding: 12px;
  background: #ffffff;
}

.subpanel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.subpanel-head h5 {
  margin: 0;
  font-size: 15px;
}

.subpanel-head p {
  margin: 6px 0 0;
  color: #8c92a6;
  font-size: 12px;
}

.actions {
  margin-top: 16px;
}

.group-table {
  margin: 16px 0;
}

.tag-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.merge-form {
  margin-top: 18px;
}

.log-panel {
  padding: 18px;
}

.log-panel header {
  margin-bottom: 10px;
}

.log-panel header h4 {
  margin: 0;
}

.log-panel header p {
  margin: 6px 0 0;
  color: #9299ae;
  font-size: 12px;
}

.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-sub {
  margin: 0;
  color: #9da3b4;
  font-size: 12px;
}
</style>
