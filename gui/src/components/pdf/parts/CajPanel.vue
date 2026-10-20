<script setup>
import { computed, inject, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { mergeFileQueue, useDraft } from '../../../utils/workspace'

const { callApiDetailed, openPath, pickCaj, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const form = useDraft('pdf/parts/CajPanel/form', {
  files: [],
  outputDir: '',
  items: [],
  output: ''
})

const readyCount = computed(() => form.files.length)

watch(
  () => form.files.map((file) => file.path).join('\0'),
  () => {
    form.items = []
    form.output = ''
  }
)

const selectFiles = async () => {
  const picked = await pickCaj('pdf/caj')
  if (!picked.length) return
  const rejected = picked.filter((item) => !/\.caj$/i.test(item.path || String(item)))
  if (rejected.length) ElMessage.warning('已忽略非 CAJ 文件')
  form.files = mergeFileQueue(
    form.files,
    picked.filter((item) => /\.caj$/i.test(item.path || String(item)))
  )
}

const removeFile = (path) => {
  form.files = form.files.filter((file) => file.path !== path)
}

const clearFiles = () => {
  form.files = []
}

const selectDir = async () => {
  const directory = await pickDir(form.outputDir || '')
  if (directory) form.outputDir = directory
}

const run = async () => {
  if (!form.files.length) {
    ElMessage.warning('请先选择 CAJ 文件')
    return
  }
  form.items = []
  form.output = ''
  const result = await callApiDetailed(
    'pdf_caj_to_pdf',
    {
      files: form.files.map((file) => file.path || String(file)),
      outputDir: form.outputDir
    },
    form.files
  )
  if (!result) return
  const payload = result.data && typeof result.data === 'object' ? result.data : {}
  form.items = Array.isArray(payload.items) ? payload.items : []
  form.output = payload.output || ''
  if (result.ok && !payload.items?.length && Array.isArray(payload.files)) {
    form.items = payload.files.map((path, index) => ({
      source: form.files[index]?.path || '',
      output: path,
      status: 'success'
    }))
  }
}

const statusLabel = (item) => (item.status === 'success' ? '已完成' : '失败')
const sourceName = (item) => item.source?.split(/[\\/]/).pop() || '未知文件'
const outputName = (item) => item.output?.split(/[\\/]/).pop() || ''
</script>

<template>
  <section class="caj-panel">
    <header class="panel-intro">
      <div>
        <span class="eyebrow">CAJ → PDF</span>
        <h2>把 CAJ 文档转成 PDF</h2>
        <p>在本机批量转换，原始文件会保留。</p>
      </div>
      <el-tag type="success" effect="plain">本地处理</el-tag>
    </header>

    <el-alert class="format-note" type="info" :closable="false" show-icon>
      <template #title>支持内嵌 PDF 的 CAJ；HN、C8 和加密格式暂不支持</template>
    </el-alert>

    <section class="source-section">
      <div class="section-head">
        <div class="section-index">01</div>
        <div class="section-title">
          <b>待转换文件</b>
          <small>可一次选择多个 .caj 文件</small>
        </div>
        <div class="section-actions">
          <el-button v-if="form.files.length" text :disabled="shared.loading" @click="clearFiles">清空</el-button>
          <el-button type="primary" :disabled="shared.loading" @click="selectFiles">{{ form.files.length ? '添加 CAJ' : '选择 CAJ 文件' }}</el-button>
        </div>
      </div>

      <div v-if="!form.files.length" class="empty-source" role="button" tabindex="0" @click="selectFiles" @keydown.enter="selectFiles" @keydown.space.prevent="selectFiles">
        <span class="empty-mark">＋</span>
        <b>选择一个或多个 CAJ 文件</b>
        <small>文件留在本机处理，不会上传</small>
      </div>
      <div v-else class="file-list">
        <article v-for="(file, index) in form.files" :key="file.path" class="file-row">
          <span class="file-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="file-copy">
            <b>{{ file.filename || file.path?.split(/[\\/]/).pop() }}</b>
            <small :title="file.path">{{ file.path }}</small>
          </div>
          <el-button text size="small" :disabled="shared.loading" :aria-label="'移除 ' + (file.filename || file.path)" @click="removeFile(file.path)">移除</el-button>
        </article>
      </div>
    </section>

    <section class="output-section">
      <div class="section-head">
        <div class="section-index">02</div>
        <div class="section-title">
          <b>保存位置</b>
          <small>留空时，PDF 保存到各源文件所在目录</small>
        </div>
      </div>
      <div class="path-field">
        <el-input v-model="form.outputDir" readonly placeholder="默认使用每个源文件所在目录" aria-label="输出目录" />
        <el-button :disabled="shared.loading" @click="selectDir">选择目录</el-button>
        <el-button v-if="form.outputDir" text :disabled="shared.loading" @click="form.outputDir = ''">使用源目录</el-button>
      </div>
    </section>

    <footer class="run-row">
      <div>
        <b>{{ readyCount }} 个文件</b>
        <small>{{ readyCount ? '准备就绪后开始批量转换' : '先添加 CAJ 文件' }}</small>
      </div>
      <el-button type="primary" size="large" :disabled="!readyCount" :loading="shared.loading" @click="run">开始转换</el-button>
    </footer>

    <section v-if="form.items.length" class="result-section" aria-live="polite">
      <div class="section-head result-heading">
        <div class="section-index">03</div>
        <div class="section-title">
          <b>转换结果</b>
          <small>{{ form.items.filter((item) => item.status === 'success').length }} 项成功，{{ form.items.filter((item) => item.status !== 'success').length }} 项失败</small>
        </div>
        <el-button v-if="form.output" text type="primary" @click="openPath(form.output)">打开输出目录</el-button>
      </div>
      <article v-for="(item, index) in form.items" :key="item.source || index" class="result-row">
        <span class="result-status" :class="item.status === 'success' ? 'is-success' : 'is-error'">{{ statusLabel(item) }}</span>
        <div class="result-copy">
          <b>{{ sourceName(item) }}</b>
          <small v-if="item.status === 'success' && item.output" :title="item.output">{{ item.output }}</small>
          <small v-else class="error-copy">{{ item.error || '未生成 PDF' }}</small>
        </div>
        <el-button v-if="item.status === 'success' && item.output" text @click="openPath(item.output)">{{ outputName(item) }} · 打开</el-button>
      </article>
    </section>
  </section>
</template>

<style scoped>
.caj-panel {
  --accent: #e0533d;
  color: var(--ppx-text-secondary);
}
.panel-intro {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin: 0 0 18px;
}
.eyebrow {
  color: var(--accent);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.1em;
}
.panel-intro h2 {
  margin: 5px 0 6px;
  color: var(--ppx-text-primary);
  font-size: clamp(20px, 2.7vw, 27px);
  letter-spacing: -0.025em;
}
.panel-intro p {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.format-note {
  margin-bottom: 18px;
}
.source-section,
.output-section,
.result-section {
  padding: 19px 20px;
  border-top: 1px solid var(--ppx-glass-border);
}
.source-section {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg) var(--ppx-radius-lg) 0 0;
  background: var(--ppx-bg-surface);
}
.section-head {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 14px;
}
.section-index {
  display: grid;
  flex: 0 0 auto;
  width: 29px;
  height: 25px;
  place-items: center;
  border-radius: 6px;
  background: color-mix(in srgb, var(--accent) 12%, var(--ppx-bg-inset));
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
}
.section-title {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}
.section-title b,
.run-row b,
.result-copy b {
  color: var(--ppx-text-primary);
  font-size: 12.5px;
}
.section-title small,
.run-row small,
.result-copy small {
  color: var(--ppx-text-muted);
  font-size: 10.5px;
}
.section-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.empty-source {
  display: flex;
  min-height: 142px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--ppx-glass-border-hover);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-base);
  cursor: pointer;
}
.empty-source:hover,
.empty-source:focus-visible {
  border-color: var(--accent);
  outline: none;
}
.empty-mark {
  margin-bottom: 8px;
  color: var(--accent);
  font-size: 27px;
  line-height: 1;
}
.empty-source b {
  color: var(--ppx-text-primary);
  font-size: 12.5px;
}
.empty-source small {
  margin-top: 5px;
  color: var(--ppx-text-muted);
  font-size: 10.5px;
}
.file-list {
  max-height: 320px;
  overflow-y: auto;
}
.file-row,
.result-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 54px;
  border-top: 1px solid var(--ppx-glass-border);
}
.file-index {
  color: var(--ppx-text-muted);
  font-family: var(--ppx-font-mono);
  font-size: 10px;
}
.file-copy,
.result-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}
.file-copy b,
.file-copy small,
.result-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-copy b {
  color: var(--ppx-text-primary);
  font-size: 12px;
}
.file-copy small,
.result-copy small {
  color: var(--ppx-text-muted);
  font-size: 10px;
  font-family: var(--ppx-font-mono);
}
.result-copy .error-copy {
  white-space: normal;
  overflow-wrap: anywhere;
}
.output-section {
  border-right: 1px solid var(--ppx-glass-border);
  border-left: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-surface);
}
.output-section .section-head {
  margin-bottom: 9px;
}
.path-field {
  display: flex;
  gap: 8px;
}
.run-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 15px 20px;
  border: 1px solid var(--ppx-glass-border);
  border-top: 1px solid var(--ppx-glass-border);
  border-radius: 0 0 var(--ppx-radius-lg) var(--ppx-radius-lg);
  background: var(--ppx-bg-base);
}
.run-row > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.result-section {
  margin-top: 20px;
  padding: 0 20px 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  background: var(--ppx-bg-surface);
}
.result-heading {
  margin: 0;
  padding: 14px 0;
}
.result-status {
  flex: 0 0 auto;
  width: 50px;
  font-size: 10px;
  font-weight: 700;
}
.is-success {
  color: var(--el-color-success);
}
.is-error,
.error-copy {
  color: var(--el-color-danger) !important;
}
@media (max-width: 620px) {
  .source-section,
  .output-section,
  .result-section {
    padding-right: 13px;
    padding-left: 13px;
  }
  .section-head {
    align-items: flex-start;
  }
  .section-actions {
    margin-left: auto;
  }
  .path-field,
  .run-row {
    align-items: stretch;
    flex-direction: column;
  }
  .run-row > .el-button {
    width: 100%;
  }
  .result-row {
    flex-wrap: wrap;
    padding: 8px 0;
  }
  .result-copy {
    flex-basis: calc(100% - 72px);
  }
}
</style>
