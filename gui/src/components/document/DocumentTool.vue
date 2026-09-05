<script setup>
import { useDraft } from '../../utils/workspace'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi, callApiRaw } from '@/utils/pyapi'

const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = ref(props.initialTab || 'search')
const loading = ref(false)
const indexing = ref(false)
const searching = ref(false)
const status = reactive({ documents: 0, freshDocuments: 0, staleDocuments: 0, missingDocuments: 0, staleSamples: [], sourceBytes: 0, databaseBytes: 0, updatedAt: 0, extensions: [] })
const indexForm = useDraft('document/DocumentTool/indexForm', { directories: [], files: [], recursive: true, rebuild: false, prune: false, ocr: false })
const searchForm = useDraft('document/DocumentTool/searchForm', { query: '', extension: '', directory: '', limit: 50 })
const results = ref([])
const hitPreview = ref(null)
const locate = async (item, location) => {
  if (location.page) {
    const response = await callApi('pdf_page_preview', { filePath: item.path, pageNumbers: [location.page] })
    if (!response.ok) return ElMessage.error(response.message)
    hitPreview.value = response.data
  } else ElMessage.info(location.sheet ? `${location.sheet}，第 ${location.row} 行` : location.paragraph ? `正文第 ${location.paragraph} 段（含表格段落）` : `第 ${location.line} 行`)
}
const tableForm = useDraft('document/DocumentTool/tableForm', { filePath: '', outputDir: '', outputName: '', outputFormat: 'xlsx', pageSpec: '', dpi: 220, columnTolerance: 0, autoRotate: false, rotation: 0 })
const tableResult = ref(null)
const tablePage = ref(1)
const tableRowPage = ref(1)
const currentTable = computed(() => tableResult.value?.tables?.[tablePage.value - 1])
const tableColumnCount = computed(() => Math.max(1, ...(currentTable.value?.rows || []).map((row) => row.length)))
const exportCorrected = async () => {
  loading.value = true
  try {
    const response = await callApi('ocr_table', { ...tableForm, tables: tableResult.value.tables, saveFile: true })
    if (!response.ok) return ElMessage.error(response.message)
    tableResult.value = { ...response.data, tables: tableResult.value.tables }
    ElMessage.success('已导出核对后的表格')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

const formatBytes = (bytes) => {
  const value = Number(bytes || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`
  return `${(value / 1024 ** 3).toFixed(1)} GB`
}
const updatedText = computed(() => (status.updatedAt ? new Date(status.updatedAt * 1000).toLocaleString() : '尚未建立'))
const excerptParts = (value) => {
  const text = String(value || '')
  const parts = []
  const marked = /<mark>([\s\S]*?)<\/mark>/gi
  let cursor = 0
  let match
  let hasMarkedPart = false
  while ((match = marked.exec(text))) {
    hasMarkedPart = true
    if (match.index > cursor) parts.push({ text: text.slice(cursor, match.index), highlight: false })
    parts.push({ text: match[1], highlight: true })
    cursor = marked.lastIndex
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), highlight: false })
  if (hasMarkedPart) return parts
  const keyword = searchForm.query.trim()
  if (!keyword) return [{ text, highlight: false }]
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text
    .split(new RegExp(`(${escaped})`, 'gi'))
    .filter(Boolean)
    .map((item) => ({ text: item, highlight: item.toLowerCase() === keyword.toLowerCase() }))
}

const refreshStatus = async () => {
  const response = await callApi('document_index_status')
  if (response.ok) Object.assign(status, response.data)
}

const chooseDirectory = async () => {
  const path = await callApiRaw('system_pySelectDirDialog', indexForm.directories[0] || '')
  if (path && !indexForm.directories.includes(path)) indexForm.directories.push(path)
}

const chooseFiles = async () => {
  const files = await callApiRaw('system_pyCreateFileDialog', ['支持的文档 (*.pdf;*.docx;*.xlsx;*.xlsm;*.txt;*.md;*.markdown;*.csv;*.json;*.log)'])
  for (const file of files || []) {
    if (file?.path && !indexForm.files.includes(file.path)) indexForm.files.push(file.path)
  }
}

const buildIndex = async () => {
  if (!indexForm.directories.length && !indexForm.files.length) return ElMessage.warning('请先添加至少一个目录或文件')
  indexing.value = true
  try {
    const response = await callApi('document_index_build', { ...indexForm })
    if (response.ok) {
      ElMessage.success(response.message || '索引更新完成')
      await refreshStatus()
    } else ElMessage.error(response.message || '索引失败')
  } catch (error) {
    ElMessage.error(error?.message || '索引失败')
  } finally {
    indexing.value = false
  }
}

const search = async () => {
  if (!searchForm.query.trim()) return ElMessage.warning('请输入关键词')
  searching.value = true
  try {
    const response = await callApi('document_index_search', { ...searchForm })
    if (!response.ok) return ElMessage.error(response.message || '搜索失败')
    results.value = response.data.results || []
  } catch (error) {
    ElMessage.error(error?.message || '搜索失败')
  } finally {
    searching.value = false
  }
}

const openPath = async (path) => {
  if (path) await callApiRaw('system_pyOpenFile', path)
}

const removeResult = async (path) => {
  const response = await callApi('document_index_remove', { path })
  if (!response.ok) return ElMessage.error(response.message || '移除失败')
  results.value = results.value.filter((item) => item.path !== path)
  await refreshStatus()
}

const clearIndex = async () => {
  await ElMessageBox.confirm('这只会清空本机搜索索引，不会删除原文件。', '清空文档索引', { type: 'warning' })
  const response = await callApi('document_index_clear')
  if (!response.ok) return ElMessage.error(response.message || '清空失败')
  results.value = []
  ElMessage.success('索引已清空')
  await refreshStatus()
}

const chooseTableFile = async () => {
  const files = await callApiRaw('system_pyCreateFileDialog', ['图片或 PDF (*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff;*.pdf)'])
  if (!files?.length) return
  tableForm.filePath = files[0].path
  tableForm.outputDir = files[0].dir
  tableForm.outputName = `${files[0].filename.replace(/\.[^.]+$/, '')}_table`
}

const chooseTableOutput = async () => {
  const path = await callApiRaw('system_pySelectDirDialog', tableForm.outputDir || '')
  if (path) tableForm.outputDir = path
}

const recognizeTable = async () => {
  if (!tableForm.filePath) return ElMessage.warning('请先选择图片或 PDF')
  loading.value = true
  try {
    const response = await callApi('ocr_table', { ...tableForm, saveFile: false })
    if (!response.ok) return ElMessage.error(response.message || '识别失败')
    tableResult.value = response.data
    tablePage.value = 1
    tableRowPage.value = 1
    ElMessage.success(response.message || '表格识别完成')
  } catch (error) {
    ElMessage.error(error?.message || '识别失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.initialTab,
  (value) => {
    if (value) activeTab.value = value
  }
)
onMounted(refreshStatus)
</script>

<template>
  <div class="document-tool">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="全文搜索" name="search">
        <section class="hero-search">
          <div>
            <h3>本地文档搜索</h3>
            <p>索引和搜索都在本机完成，文件不会上传。</p>
          </div>
          <el-input v-model="searchForm.query" size="large" clearable placeholder="搜索 PDF、Word、Excel、Markdown…" @keyup.enter="search">
            <template #append><el-button :loading="searching" @click="search">搜索</el-button></template>
          </el-input>
          <div class="search-filters">
            <el-select v-model="searchForm.extension" clearable placeholder="全部类型"><el-option v-for="ext in status.extensions" :key="ext" :label="ext" :value="ext" /></el-select>
            <el-input v-model="searchForm.directory" clearable placeholder="限定目录（可选）" />
          </div>
        </section>
        <div class="result-list">
          <article v-for="item in results" :key="item.path" class="result-card">
            <div class="result-icon">{{ item.extension.replace('.', '').toUpperCase() }}</div>
            <div class="result-main">
              <div class="result-title">
                <strong>{{ item.title }}</strong>
                <el-tag v-if="item.missing" size="small" type="danger" effect="plain">源文件缺失</el-tag>
                <el-tag v-else-if="item.stale" size="small" type="warning" effect="plain">索引已过期</el-tag>
              </div>
              <p>
                <template v-for="(part, index) in excerptParts(item.excerpt)" :key="index"
                  ><mark v-if="part.highlight">{{ part.text }}</mark
                  ><span v-else>{{ part.text }}</span></template
                >
              </p>
              <div>
                <el-button v-for="(location, index) in item.locations || []" :key="index" text size="small" :disabled="item.missing || item.stale" @click="locate(item, location)">{{ location.page ? `第 ${location.page} 页${location.ocr ? ' · OCR' : ''}` : location.sheet ? `${location.sheet} · 行 ${location.row}` : location.paragraph ? `段落 ${location.paragraph}` : `行 ${location.line}` }}</el-button
                ><el-tag v-if="item.truncated" type="warning">仅索引前 200 万字符</el-tag>
              </div>
              <small>{{ item.path }} · {{ formatBytes(item.size) }}</small>
            </div>
            <div class="result-actions"><el-button type="primary" text :disabled="item.missing" @click="openPath(item.path)">打开</el-button><el-button type="danger" text @click="removeResult(item.path)">移出索引</el-button></div>
          </article>
          <el-empty v-if="!results.length" description="输入关键词搜索本机文档" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="智能收件箱 / 索引" name="index">
        <div class="status-grid">
          <div class="metric">
            <strong>{{ status.documents }}</strong
            ><span>已索引文档</span>
          </div>
          <div class="metric">
            <strong>{{ formatBytes(status.sourceBytes) }}</strong
            ><span>源文件总量</span>
          </div>
          <div class="metric">
            <strong>{{ formatBytes(status.databaseBytes) }}</strong
            ><span>本地索引大小</span>
          </div>
          <div class="metric">
            <strong class="time-value">{{ updatedText }}</strong
            ><span>最近更新</span>
          </div>
          <div class="metric" :class="{ warning: status.staleDocuments }">
            <strong>{{ status.staleDocuments }}</strong
            ><span>过期或缺失（缺失 {{ status.missingDocuments }}）</span>
          </div>
        </div>
        <el-alert v-if="status.staleDocuments" class="stale-alert" type="warning" :closable="false" show-icon title="部分源文件已变化或缺失；更新索引可刷新内容，勾选清理可移除目录中的失效记录。" />
        <section class="index-card">
          <div class="section-head">
            <div>
              <h3>建立本地索引</h3>
              <p>支持 PDF、DOCX、XLSX、TXT、Markdown、CSV、JSON 和日志文件。</p>
            </div>
            <div class="source-actions"><el-button @click="chooseFiles">添加文件</el-button><el-button @click="chooseDirectory">添加目录</el-button></div>
          </div>
          <h4>目录</h4>
          <div class="directory-list">
            <div v-for="(directory, index) in indexForm.directories" :key="directory" class="directory-item">
              <span>{{ directory }}</span
              ><el-button text type="danger" @click="indexForm.directories.splice(index, 1)">移除</el-button>
            </div>
            <el-empty v-if="!indexForm.directories.length" :image-size="54" description="还没有选择目录" />
          </div>
          <h4>单独文件</h4>
          <div class="directory-list file-list">
            <div v-for="(file, index) in indexForm.files" :key="file" class="directory-item">
              <span>{{ file }}</span
              ><el-button text type="danger" @click="indexForm.files.splice(index, 1)">移除</el-button>
            </div>
            <el-empty v-if="!indexForm.files.length" :image-size="48" description="可按需添加单个文档" />
          </div>
          <div class="index-options"><el-checkbox v-model="indexForm.recursive">包含子目录</el-checkbox><el-checkbox v-model="indexForm.prune">移除目录中已不存在文件的旧记录</el-checkbox><el-checkbox v-model="indexForm.rebuild">重新提取所选范围</el-checkbox><el-checkbox v-model="indexForm.ocr">扫描 PDF 使用 OCR</el-checkbox></div>
          <div class="footer-actions"><el-button type="danger" plain @click="clearIndex">清空索引</el-button><el-button type="primary" :loading="indexing" @click="buildIndex">更新索引</el-button></div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="表格 OCR" name="table">
        <section class="index-card">
          <div class="section-head">
            <div>
              <h3>图片 / PDF 表格识别</h3>
              <p>根据文字坐标重建规则表格，可导出 Excel、CSV 与 JSON。</p>
            </div>
            <el-button @click="chooseTableFile">选择文件</el-button>
          </div>
          <el-alert title="先识别，再逐页核对并修改单元格，最后导出。低置信度文字会标黄；合并单元格需人工整理。" type="info" :closable="false" show-icon />
          <el-form label-position="top" class="table-form">
            <div class="two-columns">
              <el-form-item label="源文件"><el-input v-model="tableForm.filePath" /></el-form-item><el-form-item label="PDF 页码（图片可留空）"><el-input v-model="tableForm.pageSpec" placeholder="例如 1-3,5；留空为全部" /></el-form-item>
            </div>
            <div class="three-columns">
              <el-form-item label="方向校正"><el-checkbox v-model="tableForm.autoRotate">比较四个方向（较慢）</el-checkbox></el-form-item>
              <el-form-item label="输出格式"
                ><el-select v-model="tableForm.outputFormat"><el-option label="Excel" value="xlsx" /><el-option label="CSV" value="csv" /><el-option label="JSON" value="json" /><el-option label="全部" value="all" /></el-select
              ></el-form-item>
              <el-form-item label="PDF 渲染 DPI"><el-input-number v-model="tableForm.dpi" :min="120" :max="400" /></el-form-item>
              <el-form-item label="列对齐容差（0=自动）"><el-input-number v-model="tableForm.columnTolerance" :min="0" :max="500" /></el-form-item>
            </div>
            <div class="two-columns">
              <el-form-item label="输出目录"
                ><el-input v-model="tableForm.outputDir"
                  ><template #append><el-button @click="chooseTableOutput">选择</el-button></template></el-input
                ></el-form-item
              ><el-form-item label="输出名称"><el-input v-model="tableForm.outputName" /></el-form-item>
            </div>
            <div class="footer-actions"><el-button type="primary" :loading="loading" @click="recognizeTable">识别并检查表格</el-button><el-button v-if="tableResult?.tables?.length" type="success" :loading="loading" @click="exportCorrected">导出已核对的表格</el-button><el-button v-if="tableResult?.output" @click="openPath(tableResult.output)">打开结果</el-button></div>
          </el-form>
          <div v-if="currentTable">
            <el-pagination v-model:current-page="tablePage" :page-size="1" :total="tableResult.tables.length" layout="prev, pager, next, total" @current-change="tableRowPage = 1" />
            <p>源第 {{ currentTable.page }} 页 · 方向校正 {{ currentTable.rotation || 0 }}° · {{ currentTable.uncertain?.length || 0 }} 处低置信度内容</p>
            <el-button size="small" @click="currentTable.rows.push(Array(tableColumnCount).fill(''))">添加行</el-button>
            <el-button size="small" @click="currentTable.rows.forEach((row) => row.push(''))">添加列</el-button>
            <el-table :data="currentTable.rows.slice((tableRowPage - 1) * 30, tableRowPage * 30)" max-height="450" border>
              <el-table-column v-for="column in tableColumnCount" :key="column" :label="'列 ' + column" min-width="160">
                <template #default="scope"><el-input v-model="scope.row[column - 1]" :class="{ uncertain: (currentTable.uncertain || []).some((text) => String(scope.row[column - 1] || '').includes(text)) }" /></template>
              </el-table-column>
              <el-table-column label="操作" width="75"
                ><template #default="scope"><el-button text type="danger" @click="currentTable.rows.splice((tableRowPage - 1) * 30 + scope.$index, 1)">删除行</el-button></template></el-table-column
              >
            </el-table>
            <el-pagination v-model:current-page="tableRowPage" :page-size="30" :total="currentTable.rows.length" layout="prev, pager, next, total" />
          </div>
          <el-result v-if="tableResult" icon="success" :title="`${tableResult.rowCount} 行 × ${tableResult.columnCount} 列`" :sub-title="tableResult.outputDir" />
        </section>
      </el-tab-pane>
    </el-tabs>
    <el-dialog :model-value="Boolean(hitPreview)" title="命中页预览" width="min(800px, 90vw)" @close="hitPreview = null">
      <el-image v-for="page in hitPreview?.pages || []" :key="page.page" :src="page.preview || page.image" style="width: 100%" />
    </el-dialog>
  </div>
</template>

<style scoped>
.uncertain :deep(.el-input__wrapper) {
  background: var(--el-color-warning-light-8);
}
.document-tool {
  height: 100%;
  overflow: auto;
  box-sizing: border-box;
  padding: 18px 22px 30px;
}
.hero-search,
.index-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 15px;
  background: var(--ppx-bg-elevated);
  padding: 20px;
}
.hero-search {
  display: grid;
  grid-template-columns: 260px minmax(280px, 1fr);
  gap: 14px 20px;
  align-items: center;
}
.hero-search .search-filters {
  grid-column: 2;
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 10px;
}
h3 {
  margin: 0 0 4px;
}
p {
  margin: 0;
  color: var(--ppx-text-muted);
}
.result-list {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.result-card {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 14px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  background: var(--ppx-bg-elevated);
}
.result-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: white;
  background: #4f7cff;
  font-size: 11px;
  font-weight: 700;
}
.result-main {
  min-width: 0;
}
.result-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.result-main p {
  margin: 5px 0;
  font-size: 13px;
  line-height: 1.5;
}
.result-main mark {
  padding: 1px 3px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--el-color-warning) 35%, transparent);
  color: var(--ppx-text-primary);
}
.result-main small {
  display: block;
  color: var(--ppx-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-actions {
  display: flex;
  flex-direction: column;
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.metric {
  padding: 18px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  background: var(--ppx-bg-elevated);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.metric strong {
  font-size: 24px;
  color: var(--accent);
}
.metric.warning strong {
  color: var(--el-color-warning);
}
.metric .time-value {
  font-size: 14px;
}
.metric span {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.section-head,
.directory-item,
.footer-actions,
.index-options {
  display: flex;
  align-items: center;
  gap: 14px;
}
.section-head {
  justify-content: space-between;
  margin-bottom: 14px;
}
.source-actions {
  display: flex;
  gap: 8px;
}
.section-head p {
  font-size: 13px;
}
.directory-list {
  border: 1px dashed var(--ppx-glass-border);
  border-radius: 10px;
  min-height: 100px;
  padding: 8px;
}
.index-card h4 {
  margin: 14px 0 8px;
  color: var(--ppx-text-secondary);
  font-size: 13px;
}
.file-list {
  min-height: 80px;
}
.stale-alert {
  margin-bottom: 14px;
}
.directory-item {
  justify-content: space-between;
  padding: 8px 10px;
}
.index-options {
  margin: 14px 0;
  flex-wrap: wrap;
}
.footer-actions {
  justify-content: flex-end;
}
.table-form {
  margin-top: 16px;
}
.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.three-columns {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 14px;
}
@media (max-width: 850px) {
  .hero-search,
  .two-columns,
  .three-columns {
    grid-template-columns: 1fr;
  }
  .hero-search .search-filters {
    grid-column: 1;
  }
  .status-grid {
    grid-template-columns: 1fr 1fr;
  }
  .result-card {
    grid-template-columns: 48px minmax(0, 1fr);
  }
  .result-actions {
    grid-column: 2;
    flex-direction: row;
  }
}
</style>
