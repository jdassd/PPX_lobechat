<script setup>
import { inject, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, pickPdf, pickDir, openPath } = inject('pdfApi')
const shared = inject('pdfShared')

const form = reactive({ filePath: '', password: '', outputDir: '', outputName: '', addPageNumbers: false, pageNumberStart: 1, pageNumberPosition: 'bottom-center' })
const pages = ref([])
const output = ref('')
const loadingPreview = ref(false)
const truncated = ref(false)

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
    const result = await callApi('pdf_page_preview', { filePath: form.filePath, password: form.password, maxPages: 300, width: 160 })
    if (result) {
      pages.value = (result.pages || []).map((page) => ({ ...page, originalPage: page.page, rotateBy: 0 }))
      truncated.value = !!result.truncated
      if (truncated.value) ElMessage.warning(`该 PDF 共 ${result.pageCount} 页，页面工作台最多载入 ${result.loadedCount} 页；为避免误删，已禁用生成。`)
    }
  } finally {
    loadingPreview.value = false
  }
}

const move = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= pages.value.length) return
  const [page] = pages.value.splice(index, 1)
  pages.value.splice(target, 0, page)
}

const rotate = (page) => {
  page.rotateBy = (page.rotateBy + 90) % 360
}

const restoreOrder = () => {
  pages.value.sort((a, b) => a.originalPage - b.originalPage)
  pages.value.forEach((page) => (page.rotateBy = 0))
}

const chooseOutput = async () => {
  const directory = await pickDir(form.outputDir)
  if (directory) form.outputDir = directory
}

const execute = async () => {
  if (!form.filePath || !pages.value.length) return ElMessage.warning('请先载入 PDF 页面')
  if (truncated.value) return ElMessage.warning('页面未完整载入，不能生成新 PDF')
  const rotations = Object.fromEntries(pages.value.filter((page) => page.rotateBy).map((page) => [String(page.originalPage), page.rotateBy]))
  const result = await callApi('pdf_page_workbench', {
    ...form,
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
        <span>当前保留 {{ pages.length }} 页</span>
        <el-button size="small" :disabled="!pages.length" @click="restoreOrder">恢复原顺序</el-button>
        <el-button size="small" :disabled="!form.filePath" :loading="loadingPreview" @click="loadPages">重新载入</el-button>
      </div>
      <el-alert v-if="truncated" title="页面数量超过工作台上限。为防止未显示页面被遗漏，本页禁止生成；请先用“页码切割”分段处理。" type="warning" :closable="false" show-icon />
      <div v-if="pages.length" class="page-grid">
        <article v-for="(page, index) in pages" :key="page.originalPage" class="page-card">
          <div class="thumb-wrap"><img :src="page.preview" :alt="`第 ${page.originalPage} 页`" :style="{ transform: `rotate(${page.rotateBy}deg)` }" /></div>
          <strong>原第 {{ page.originalPage }} 页</strong>
          <small>新第 {{ index + 1 }} 页 · 旋转 {{ page.rotateBy }}°</small>
          <div class="page-actions">
            <el-button text :disabled="index === 0" @click="move(index, -1)">←</el-button>
            <el-button text @click="rotate(page)">旋转</el-button>
            <el-button text :disabled="index === pages.length - 1" @click="move(index, 1)">→</el-button>
            <el-button text type="danger" :disabled="pages.length === 1" @click="pages.splice(index, 1)">删除</el-button>
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
        <el-button type="primary" :loading="shared.loading" :disabled="!pages.length || truncated" @click="execute">生成新 PDF</el-button>
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
