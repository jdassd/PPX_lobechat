<template>
  <section class="panel">
    <header>
      <h4>拖动缩略图调整页面顺序</h4>
      <p>先生成预览，再通过拖动页面缩略图重排顺序，无需手动填写页码</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="页面预览">
        <div class="reorder-preview">
          <div class="field-row">
            <el-button
              type="primary"
              plain
              :loading="form.loadingPreview"
              :disabled="!form.file"
              @click="loadReorderPreview"
            >
              生成预览
            </el-button>
            <span class="reorder-hint">生成后可在下方拖动页面缩略图调整顺序（当前预览最多前 80 页）</span>
          </div>
          <template v-if="form.pages && form.pages.length">
            <el-scrollbar max-height="260px">
              <div class="reorder-grid">
                <div
                  v-for="(page, index) in form.pages"
                  :key="page.page"
                  class="reorder-page"
                  draggable="true"
                  @dragstart="onReorderDragStart(index, $event)"
                  @dragover.prevent="onReorderDragOver(index, $event)"
                  @drop.prevent="onReorderDrop(index, $event)"
                >
                  <div class="reorder-thumb">
                    <img :src="page.image" :alt="`第 ${page.page} 页`" />
                  </div>
                  <p class="reorder-page-label">第 {{ page.page }} 页</p>
                </div>
              </div>
            </el-scrollbar>
            <p class="reorder-hint">当前顺序即为重排后的顺序，执行前可多次调整。</p>
          </template>
          <p v-else class="reorder-empty-hint">请选择 PDF 后点击“生成预览”。</p>
        </div>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.appendRemaining">自动追加剩余页码</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runReorder">执行重排</el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-tag type="success" effect="plain" @click="openPath(form.output)">
        {{ form.output }}
      </el-tag>
    </div>
  </section>
</template>

<script setup>
import { inject, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickPdf } = inject('pdfApi')
const shared = inject('pdfShared')

const form = reactive({
  file: null,
  orderText: '',
  appendRemaining: true,
  output: '',
  pages: [],
  loadingPreview: false
})

const reorderDragState = reactive({
  fromIndex: -1
})

const selectPdf = async () => {
  const result = await pickPdf()
  if (!result.length) return
  form.file = result[0]
}

const syncReorderOrderText = () => {
  if (!form.pages || !form.pages.length) {
    form.orderText = ''
    return
  }
  form.orderText = form.pages.map((item) => item.page).join(',')
}

const loadReorderPreview = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  form.loadingPreview = true
  try {
    const res = await callApi('pdf_convert_to_images', {
      filePath: form.file.path,
      dpi: 120,
      format: 'png',
      maxPages: 80
    })
    if (res && Array.isArray(res.files)) {
      form.pages = res.files.map((path, index) => ({
        page: index + 1,
        image: path
      }))
      syncReorderOrderText()
    }
  } finally {
    form.loadingPreview = false
  }
}

const onReorderDragStart = (index, event) => {
  reorderDragState.fromIndex = index
  if (event && event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(index))
  }
}

const onReorderDragOver = (index, event) => {
  if (event && event.preventDefault) {
    event.preventDefault()
  }
  if (event && event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

const onReorderDrop = (index, event) => {
  if (event && event.preventDefault) {
    event.preventDefault()
  }
  let from = reorderDragState.fromIndex
  if (from === -1 && event && event.dataTransfer) {
    const raw = event.dataTransfer.getData('text/plain')
    const parsed = Number.parseInt(raw, 10)
    if (!Number.isNaN(parsed)) {
      from = parsed
    }
  }
  const list = form.pages
  if (!list || !list.length) return
  if (from < 0 || from >= list.length) return
  if (index < 0 || index >= list.length) return
  if (from === index) return

  const [moved] = list.splice(from, 1)
  list.splice(index, 0, moved)
  reorderDragState.fromIndex = -1
  syncReorderOrderText()
}

const runReorder = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  let order = []
  if (form.pages && form.pages.length) {
    order = form.pages.map((item) => item.page)
  } else if (form.orderText) {
    order = form.orderText
      .split(',')
      .map((item) => Number(item.trim()))
      .filter((num) => Number.isInteger(num) && num > 0)
  }
  if (!order.length) {
    ElMessage.warning('请先生成预览并拖动调整页面顺序')
    return
  }
  const res = await callApi('pdf_reorder_pages', {
    filePath: form.file.path,
    order,
    appendRemaining: form.appendRemaining
  })
  if (res) {
    form.output = res.output
  }
}
</script>

<style scoped>
/* 页面重排预览 */
.reorder-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reorder-hint,
.reorder-empty-hint {
  margin: 8px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.reorder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.reorder-page {
  background: var(--ppx-glass-bg);
  border-radius: 10px;
  border: 1px solid var(--ppx-glass-border);
  padding: 8px;
  cursor: grab;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: all var(--ppx-transition-fast);
}

.reorder-page:hover {
  border-color: var(--ppx-glass-border-hover);
  background: var(--ppx-glass-bg-hover);
}

.reorder-page:active {
  cursor: grabbing;
}

.reorder-thumb {
  width: 100%;
  padding-top: 140px;
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  background: var(--ppx-bg-elevated);
}

.reorder-thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.reorder-page-label {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}
</style>
