<script setup>
import { useDraft } from '../../../utils/workspace'
import { computed, inject, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, pickPdf, pickDir, openPath } = inject('pdfApi')
const shared = inject('pdfShared')

const form = useDraft('pdf/parts/PageWorkbenchPanel/form', { filePath: '', password: '', outputDir: '', outputName: '', addPageNumbers: false, pageNumberStart: 1, pageNumberPosition: 'bottom-center' })
const pages = ref([])
const output = ref('')
const loadingPreview = ref(false)
const pageIndex = ref(1)
const pageSize = 24
const sourceSignature = ref('')
const sourceCount = ref(0)
const thumbnails = ref({})
const selected = ref([])
const pageRange = ref('')
const moveTarget = ref(1)
const undoStack = ref([])
const redoStack = ref([])
const dragPage = ref(null)
const visiblePages = computed(() => pages.value.slice((pageIndex.value - 1) * pageSize, pageIndex.value * pageSize))
let previewRequest = 0
const remember = () => {
  undoStack.value.push(pages.value.map((page) => ({ ...page })))
  undoStack.value = undoStack.value.slice(-100)
  redoStack.value = []
}
const undo = () => {
  if (undoStack.value.length) {
    redoStack.value.push(pages.value)
    pages.value = undoStack.value.pop()
  }
}
const redo = () => {
  if (redoStack.value.length) {
    undoStack.value.push(pages.value)
    pages.value = redoStack.value.pop()
  }
}
const loadVisible = async () => {
  const request = ++previewRequest
  const missing = visiblePages.value.filter((page) => !thumbnails.value[page.originalPage]).map((page) => page.originalPage)
  if (!missing.length || !form.filePath) return
  loadingPreview.value = true
  try {
    const result = await callApi('pdf_page_preview', { filePath: form.filePath, password: form.password, pageNumbers: missing, limit: pageSize, width: 160 })
    if (request !== previewRequest || !result) return
    if (result.sourceSignature !== sourceSignature.value) return ElMessage.error('源文件已变化，请重新载入后再编辑')
    const entries = Object.entries(thumbnails.value)
    thumbnails.value = Object.fromEntries(entries.slice(-pageSize * 3))
    for (const page of result.pages || []) thumbnails.value[page.page] = page.preview
  } finally {
    if (request === previewRequest) loadingPreview.value = false
  }
}
watch(() => visiblePages.value.map((page) => page.originalPage).join(','), loadVisible)

const choosePdf = async () => {
  const selected = await pickPdf()
  if (!selected.length) return
  form.filePath = selected[0].path
  form.outputDir = selected[0].dir
  form.outputName = `${selected[0].filename.replace(/\.pdf$/i, '')}_pages.pdf`
  await loadPages()
}

const acceptLaunchFiles = async (event) => {
  const files = event?.detail?.files || window.__PPX_OPEN_FILES__ || []
  const pdf = files.find((path) => String(path).toLowerCase().endsWith('.pdf'))
  if (!pdf || form.filePath === pdf) return
  form.filePath = pdf
  const slash = Math.max(pdf.lastIndexOf('/'), pdf.lastIndexOf('\\'))
  form.outputDir = slash >= 0 ? pdf.slice(0, slash) : ''
  form.outputName = `${pdf.slice(slash + 1).replace(/\.pdf$/i, '')}_pages.pdf`
  await loadPages()
}

const loadPages = async () => {
  if (!form.filePath) return ElMessage.warning('请先选择 PDF')
  loadingPreview.value = true
  try {
    ++previewRequest
    const result = await callApi('pdf_page_preview', { filePath: form.filePath, password: form.password, limit: pageSize, width: 160 })
    if (result) {
      sourceSignature.value = result.sourceSignature
      sourceCount.value = result.pageCount
      thumbnails.value = Object.fromEntries((result.pages || []).map((page) => [page.page, page.preview]))
      pages.value = Array.from({ length: result.pageCount }, (_, index) => ({ originalPage: index + 1, rotateBy: 0 }))
      pageIndex.value = 1
      selected.value = []
      undoStack.value = []
      redoStack.value = []
    }
  } finally {
    loadingPreview.value = false
  }
}

const move = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= pages.value.length) return
  remember()
  const [page] = pages.value.splice(index, 1)
  pages.value.splice(target, 0, page)
}

const rotate = (page) => {
  remember()
  page.rotateBy = (page.rotateBy + 90) % 360
}

const restoreOrder = () => {
  remember()
  pages.value = Array.from({ length: sourceCount.value }, (_, index) => ({ originalPage: index + 1, rotateBy: 0 }))
}

const selectRange = () => {
  const numbers = new Set()
  for (const part of pageRange.value.split(/[,，\s]+/).filter(Boolean)) {
    const match = /^(\d+)(?:-(\d+))?$/.exec(part)
    if (!match) return ElMessage.warning('使用原页码，例如 1-8,12,20-30')
    const start = Number(match[1])
    const end = Number(match[2] || start)
    if (start < 1 || end > sourceCount.value || end < start) return ElMessage.warning('页码范围无效')
    for (let number = start; number <= end; number++) numbers.add(number)
  }
  selected.value = pages.value.filter((page) => numbers.has(page.originalPage)).map((page) => page.originalPage)
}
const removePages = (numbers) => {
  if (numbers.length >= pages.value.length) return ElMessage.warning('至少保留一页')
  remember()
  pages.value = pages.value.filter((page) => !numbers.includes(page.originalPage))
  selected.value = []
  pageIndex.value = Math.min(pageIndex.value, Math.ceil(pages.value.length / pageSize))
}
const rotateSelected = () => {
  remember()
  pages.value.forEach((page) => {
    if (selected.value.includes(page.originalPage)) page.rotateBy = (page.rotateBy + 90) % 360
  })
}
const moveSelected = () => {
  remember()
  const moving = pages.value.filter((page) => selected.value.includes(page.originalPage))
  const remaining = pages.value.filter((page) => !selected.value.includes(page.originalPage))
  remaining.splice(Math.max(0, Math.min(remaining.length, moveTarget.value - 1)), 0, ...moving)
  pages.value = remaining
}
const drop = (page) => {
  const from = pages.value.findIndex((item) => item.originalPage === dragPage.value)
  const to = pages.value.findIndex((item) => item.originalPage === page.originalPage)
  if (from >= 0) move(from, to - from)
}

const chooseOutput = async () => {
  const directory = await pickDir(form.outputDir)
  if (directory) form.outputDir = directory
}

const execute = async () => {
  if (!form.filePath || !pages.value.length) return ElMessage.warning('请先载入 PDF 页面')
  const rotations = Object.fromEntries(pages.value.filter((page) => page.rotateBy).map((page) => [String(page.originalPage), page.rotateBy]))
  const result = await callApi('pdf_page_workbench', {
    ...form,
    sourceSignature: sourceSignature.value,
    pageOrder: pages.value.map((page) => page.originalPage),
    rotations
  })
  if (result?.output) output.value = result.output
}

onMounted(() => {
  window.addEventListener('ppx-open-files', acceptLaunchFiles)
  acceptLaunchFiles()
})
onUnmounted(() => window.removeEventListener('ppx-open-files', acceptLaunchFiles))
</script>

<template>
  <section class="panel-card">
    <div class="panel-title">
      <div>
        <h3>PDF 页面工作台</h3>
        <p>缩略图预览、重排、旋转、删除，并可统一添加页码。</p>
      </div>
      <el-button :loading="loadingPreview" @click="choosePdf">选择 PDF</el-button>
    </div>
    <el-form label-position="top">
      <div class="path-row">
        <el-input v-model="form.filePath" placeholder="选择 PDF 文件" @change="loadPages" />
        <el-input v-model="form.password" type="password" show-password placeholder="源文件密码（如有）" />
      </div>
      <div class="page-toolbar">
        <span>原 {{ sourceCount }} 页 → 保留 {{ pages.length }} 页</span>
        <el-button size="small" :disabled="!undoStack.length" @click="undo">撤销</el-button>
        <el-button size="small" :disabled="!redoStack.length" @click="redo">重做</el-button>
        <el-button size="small" :disabled="!pages.length" @click="restoreOrder">恢复原顺序</el-button>
        <el-button size="small" :disabled="!form.filePath" :loading="loadingPreview" @click="loadPages">重新载入</el-button>
      </div>
      <div v-if="pages.length" class="page-toolbar">
        <el-input v-model="pageRange" placeholder="原页码范围：1-8,12" style="width: 170px" @keyup.enter="selectRange" />
        <el-button size="small" @click="selectRange">批选</el-button>
        <el-button size="small" @click="selected = selected.length === pages.length ? [] : pages.map((item) => item.originalPage)">全选 / 清空</el-button>
        <el-button size="small" :disabled="!selected.length" @click="rotateSelected">旋转所选</el-button>
        <el-button size="small" type="danger" :disabled="!selected.length" @click="removePages(selected)">删除所选 {{ selected.length || '' }}</el-button>
      </div>
      <div v-if="selected.length" class="page-toolbar"><span>移动所选页面至新位置：</span><el-input-number v-model="moveTarget" :min="1" :max="pages.length" /><el-button @click="moveSelected">移动</el-button></div>
      <el-pagination v-if="pages.length" v-model:current-page="pageIndex" :page-size="pageSize" :total="pages.length" layout="prev, pager, next, jumper, total" />
      <div v-if="pages.length" class="page-grid">
        <article v-for="(page, index) in visiblePages" :key="page.originalPage" class="page-card" draggable="true" @dragstart="dragPage = page.originalPage" @dragover.prevent @drop.prevent="drop(page)">
          <div class="thumb-wrap"><img v-if="thumbnails[page.originalPage]" :src="thumbnails[page.originalPage]" :alt="`第 ${page.originalPage} 页`" :style="{ transform: `rotate(${page.rotateBy}deg)` }" /><span v-else>正在加载缩略图</span></div>
          <el-checkbox :model-value="selected.includes(page.originalPage)" @change="selected = $event ? [...selected, page.originalPage] : selected.filter((number) => number !== page.originalPage)">原第 {{ page.originalPage }} 页</el-checkbox>
          <small>新第 {{ (pageIndex - 1) * pageSize + index + 1 }} 页 · 旋转 {{ page.rotateBy }}°</small>
          <div class="page-actions">
            <el-button text :disabled="pageIndex === 1 && index === 0" @click="move((pageIndex - 1) * pageSize + index, -1)">←</el-button>
            <el-button text @click="rotate(page)">旋转</el-button>
            <el-button text :disabled="(pageIndex - 1) * pageSize + index === pages.length - 1" @click="move((pageIndex - 1) * pageSize + index, 1)">→</el-button>
            <el-button text type="danger" :disabled="pages.length === 1" @click="removePages([page.originalPage])">删除</el-button>
          </div>
        </article>
      </div>
      <el-empty v-else :image-size="70" description="选择 PDF 后显示页面缩略图" />

      <div class="options-row">
        <el-checkbox v-model="form.addPageNumbers">添加页码</el-checkbox>
        <el-input-number v-model="form.pageNumberStart" :min="0" :disabled="!form.addPageNumbers" />
        <el-select v-model="form.pageNumberPosition" :disabled="!form.addPageNumbers"> <el-option label="底部居中" value="bottom-center" /><el-option label="底部左侧" value="bottom-left" /><el-option label="底部右侧" value="bottom-right" /> <el-option label="顶部居中" value="top-center" /><el-option label="顶部左侧" value="top-left" /><el-option label="顶部右侧" value="top-right" /> </el-select>
      </div>
      <div class="path-row output-row">
        <el-input v-model="form.outputDir" placeholder="输出目录"
          ><template #append><el-button @click="chooseOutput">选择</el-button></template></el-input
        >
        <el-input v-model="form.outputName" placeholder="输出文件名" />
      </div>
      <div class="footer-actions">
        <el-button type="primary" :loading="shared.loading" :disabled="!pages.length" @click="execute">生成新 PDF</el-button>
        <el-button v-if="output" @click="openPath(output)">打开结果</el-button>
      </div>
    </el-form>
  </section>
</template>

<style scoped>
.panel-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 14px;
  padding: 18px;
  background: var(--ppx-bg-elevated);
}
.panel-title,
.page-toolbar,
.footer-actions,
.options-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.panel-title {
  justify-content: space-between;
  margin-bottom: 14px;
}
h3 {
  margin: 0 0 4px;
}
p {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}
.path-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 10px;
}
.page-toolbar {
  justify-content: flex-end;
  margin: 14px 0 10px;
  font-size: 13px;
  color: var(--ppx-text-muted);
}
.page-toolbar span {
  margin-right: auto;
}
.page-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 10px;
  max-height: 480px;
  overflow: auto;
  padding: 3px;
}
.page-card {
  min-width: 0;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 10px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: var(--ppx-bg-soft);
}
.thumb-wrap {
  height: 178px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: white;
  border-radius: 6px;
}
.thumb-wrap img {
  max-width: 100%;
  max-height: 100%;
  transition: transform 0.2s;
}
.page-card strong {
  font-size: 12px;
}
.page-card small {
  color: var(--ppx-text-muted);
}
.page-actions {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
}
.options-row {
  margin: 16px 0;
}
.options-row .el-select {
  width: 160px;
}
.output-row {
  margin-top: 10px;
}
.footer-actions {
  justify-content: flex-end;
  margin-top: 14px;
}
@media (max-width: 850px) {
  .path-row {
    grid-template-columns: 1fr;
  }
}
</style>
