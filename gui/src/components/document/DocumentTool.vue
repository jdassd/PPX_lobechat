<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi, callApiRaw } from '@/utils/pyapi'

const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = ref(props.initialTab || 'search')
const loading = ref(false)
const indexing = ref(false)
const searching = ref(false)
const status = reactive({ documents: 0, sourceBytes: 0, databaseBytes: 0, updatedAt: 0, extensions: [] })
const indexForm = reactive({ directories: [], recursive: true, rebuild: false, prune: false })
const searchForm = reactive({ query: '', extension: '', directory: '', limit: 50 })
const results = ref([])
const tableForm = reactive({ filePath: '', outputDir: '', outputName: '', outputFormat: 'xlsx', pageSpec: '', dpi: 220, columnTolerance: 0 })
const tableResult = ref(null)

const formatBytes = (bytes) => {
  const value = Number(bytes || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`
  return `${(value / 1024 ** 3).toFixed(1)} GB`
}
const updatedText = computed(() => (status.updatedAt ? new Date(status.updatedAt * 1000).toLocaleString() : '尚未建立'))
const cleanExcerpt = (value) => String(value || '').replace(/<\/?mark>/g, '')

const refreshStatus = async () => {
  const response = await callApi('document_index_status')
  if (response.ok) Object.assign(status, response.data)
}

const chooseDirectory = async () => {
  const path = await callApiRaw('system_pySelectDirDialog', indexForm.directories[0] || '')
  if (path && !indexForm.directories.includes(path)) indexForm.directories.push(path)
}

const buildIndex = async () => {
  if (!indexForm.directories.length) return ElMessage.warning('请先添加至少一个目录')
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
    const response = await callApi('ocr_table', { ...tableForm })
    if (!response.ok) return ElMessage.error(response.message || '识别失败')
    tableResult.value = response.data
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
              <strong>{{ item.title }}</strong>
              <p>{{ cleanExcerpt(item.excerpt) }}</p>
              <small>{{ item.path }} · {{ formatBytes(item.size) }}</small>
            </div>
            <div class="result-actions"><el-button type="primary" text @click="openPath(item.path)">打开</el-button><el-button type="danger" text @click="removeResult(item.path)">移出索引</el-button></div>
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
        </div>
        <section class="index-card">
          <div class="section-head">
            <div>
              <h3>建立本地索引</h3>
              <p>支持 PDF、DOCX、XLSX、TXT、Markdown、CSV、JSON 和日志文件。</p>
            </div>
            <el-button @click="chooseDirectory">添加目录</el-button>
          </div>
          <div class="directory-list">
            <div v-for="(directory, index) in indexForm.directories" :key="directory" class="directory-item">
              <span>{{ directory }}</span
              ><el-button text type="danger" @click="indexForm.directories.splice(index, 1)">移除</el-button>
            </div>
            <el-empty v-if="!indexForm.directories.length" :image-size="54" description="还没有选择目录" />
          </div>
          <div class="index-options"><el-checkbox v-model="indexForm.recursive">包含子目录</el-checkbox><el-checkbox v-model="indexForm.prune">移除目录中已不存在文件的旧记录</el-checkbox><el-checkbox v-model="indexForm.rebuild">重建全部索引</el-checkbox></div>
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
          <el-alert title="适合有清晰行列对齐的表格；复杂合并单元格建议导出后人工校正。" type="info" :closable="false" show-icon />
          <el-form label-position="top" class="table-form">
            <div class="two-columns">
              <el-form-item label="源文件"><el-input v-model="tableForm.filePath" /></el-form-item><el-form-item label="PDF 页码（图片可留空）"><el-input v-model="tableForm.pageSpec" placeholder="例如 1-3,5；留空为全部" /></el-form-item>
            </div>
            <div class="three-columns">
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
            <div class="footer-actions"><el-button type="primary" :loading="loading" @click="recognizeTable">开始识别</el-button><el-button v-if="tableResult?.output" @click="openPath(tableResult.output)">打开结果</el-button></div>
          </el-form>
          <el-result v-if="tableResult" icon="success" :title="`${tableResult.rowCount} 行 × ${tableResult.columnCount} 列`" :sub-title="tableResult.outputDir" />
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
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
.result-main p {
  margin: 5px 0;
  font-size: 13px;
  line-height: 1.5;
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
  grid-template-columns: repeat(4, 1fr);
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
.section-head p {
  font-size: 13px;
}
.directory-list {
  border: 1px dashed var(--ppx-glass-border);
  border-radius: 10px;
  min-height: 100px;
  padding: 8px;
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
