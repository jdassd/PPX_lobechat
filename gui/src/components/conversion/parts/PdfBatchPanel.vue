<script setup>
import { computed, reactive, ref } from 'vue'
import { FolderOpened, Loading, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'
import ConversionFileQueue from './ConversionFileQueue.vue'

const props = defineProps({
  engine: { type: Object, required: true },
  mode: { type: String, required: true, validator: (value) => ['images', 'pdf'].includes(value) }
})
const emit = defineEmits(['open-engine'])

const IMAGE_FILTER = ['图片文件 (*.jpg;*.jpeg;*.png;*.webp;*.gif;*.avif;*.tif;*.tiff;*.bmp;*.heic;*.heif;*.ico;*.tga;*.cr2;*.cr3;*.nef;*.arw;*.dng)', '全部文件 (*.*)']
const PDF_FILTER = ['PDF 文件 (*.pdf)']
const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'avif', 'tif', 'tiff', 'bmp', 'heic', 'heif', 'ico', 'tga', 'cr2', 'cr3', 'crw', 'nef', 'arw', 'dng', 'raf', 'rw2', 'orf', 'pef', 'srw', '3fr', 'erf', 'fff', 'iiq', 'kdc', 'mef', 'mrw', 'x3f'])

const files = ref([])
const results = ref([])
const loading = ref(false)
const form = reactive({ outputDir: '', outputName: '' })

const isMerge = computed(() => props.mode === 'pdf')
const title = computed(() => (isMerge.value ? '把多份 PDF，收进一个文件。' : '按你的顺序，把图片装订成 PDF。'))
const description = computed(() => (isMerge.value ? '队列顺序就是最终文档顺序；原文件不会被修改。' : '支持常见图片、HEIC 与相机 RAW；队列顺序就是 PDF 页序。'))
const minimum = computed(() => (isMerge.value ? 2 : 1))
const canRun = computed(() => props.engine.available && files.value.length >= minimum.value && !loading.value)

const filePath = (file) => file?.path || String(file || '')
const extensionOf = (file) => {
  const match = filePath(file)
    .toLowerCase()
    .match(/\.([^.]+)$/)
  return match?.[1] || ''
}
const accepts = (file) => (isMerge.value ? extensionOf(file) === 'pdf' : IMAGE_EXTENSIONS.has(extensionOf(file)))

const selectFiles = async () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在 PPX 桌面客户端中使用')
    return
  }
  const picked = await callApiRaw('system_pyCreateFileDialog', isMerge.value ? PDF_FILTER : IMAGE_FILTER)
  if (!picked?.length) return
  const rejected = picked.filter((item) => !accepts(item))
  if (rejected.length) {
    ElMessage.warning(isMerge.value ? '已忽略非 PDF 文件' : '已忽略不支持的图片文件')
  }
  const seen = new Set(files.value.map((item) => filePath(item).toLowerCase()))
  files.value = [
    ...files.value,
    ...picked.filter(accepts).filter((item) => {
      const identity = filePath(item).toLowerCase()
      if (!identity || seen.has(identity)) return false
      seen.add(identity)
      return true
    })
  ]
  results.value = []
}

const removeFile = (index) => {
  files.value.splice(index, 1)
  results.value = []
}

const moveFile = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= files.value.length) return
  const copy = [...files.value]
  ;[copy[index], copy[target]] = [copy[target], copy[index]]
  files.value = copy
}

const selectOutputDir = async () => {
  if (!hasPyApi()) return
  const directory = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (directory) form.outputDir = directory
}

const reveal = (path) => {
  if (path && hasPyApi()) callApiRaw('system_revealFile', path)
}

const openFile = (path) => {
  if (path && hasPyApi()) callApiRaw('system_pyOpenFile', path)
}

const run = async () => {
  if (!canRun.value) {
    ElMessage.warning(!props.engine.available ? '请先连接转换引擎' : `请至少添加 ${minimum.value} 个文件`)
    return
  }
  loading.value = true
  results.value = []
  try {
    const method = isMerge.value ? 'format_center_merge_pdfs' : 'format_center_images_to_pdf'
    const { ok, data, message } = await callApi(method, {
      files: files.value.map(filePath),
      outputDir: form.outputDir,
      outputName: form.outputName
    })
    if (!ok) throw new Error(message || '生成 PDF 失败')
    const payload = data && typeof data === 'object' ? data : {}
    const rawOutputs = Array.isArray(payload.outputs) ? payload.outputs : Array.isArray(payload.files) ? payload.files : []
    results.value = rawOutputs.map((item) => (typeof item === 'string' ? { path: item, fileName: item.split(/[\\/]/).pop() } : item)).filter((item) => item?.path)
    form.outputDir = payload.outputDir || form.outputDir
    ElMessage.success(message || 'PDF 已生成')
  } catch (error) {
    ElMessage.error(error?.message || '生成 PDF 失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="pdf-page">
    <header class="page-intro">
      <div>
        <span class="eyebrow">{{ isMerge ? 'PDF COLLECTION' : 'IMAGE BINDING' }}</span>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <el-tag :type="engine.available ? 'success' : 'warning'" effect="plain">{{ engine.available ? '本地处理' : '引擎未连接' }}</el-tag>
    </header>

    <el-alert v-if="!engine.loading && !engine.available" class="engine-alert" type="warning" :closable="false" show-icon>
      <template #title>{{ engine.detail }}</template>
      <el-button text type="primary" size="small" @click="emit('open-engine')">查看连接方式</el-button>
    </el-alert>

    <div class="binding-sheet">
      <section class="source-section">
        <div class="section-head">
          <div>
            <span>01</span>
            <div>
              <b>{{ isMerge ? 'PDF 队列' : '图片页序' }}</b
              ><small>使用上下箭头调整最终顺序</small>
            </div>
          </div>
          <el-button type="primary" :disabled="loading" @click="selectFiles"
            ><el-icon><Plus /></el-icon>添加{{ isMerge ? ' PDF' : '图片' }}</el-button
          >
        </div>
        <div v-if="!files.length" class="empty-source" role="button" tabindex="0" @click="selectFiles" @keydown.enter="selectFiles">
          <span
            ><el-icon :size="22"><Plus /></el-icon
          ></span>
          <b>{{ isMerge ? '选择两份或更多 PDF' : '选择一张或更多图片' }}</b>
          <p>添加后可在转换前重新排序</p>
        </div>
        <ConversionFileQueue v-else :files="files" sortable :busy="loading" @remove="removeFile" @move="moveFile" />
      </section>

      <section class="output-section">
        <div class="section-head">
          <div>
            <span>02</span>
            <div><b>命名与保存</b><small>留空名称时，由引擎根据第一项自动命名</small></div>
          </div>
        </div>
        <div class="option-grid">
          <label>
            <span>输出文件名</span>
            <el-input v-model="form.outputName" placeholder="例如：资料汇总.pdf" />
          </label>
          <label>
            <span>输出目录</span>
            <div class="path-field">
              <el-input v-model="form.outputDir" readonly placeholder="默认保存到 下载/PPX转换结果" />
              <el-button @click="selectOutputDir"
                ><el-icon><FolderOpened /></el-icon>选择</el-button
              >
            </div>
          </label>
        </div>
      </section>

      <footer class="run-row">
        <div>
          <b>{{ files.length }} 个文件</b><small>{{ files.length >= minimum ? '顺序确认后即可开始' : `还需至少 ${minimum - files.length} 个文件` }}</small>
        </div>
        <el-button type="primary" size="large" :loading="loading" :disabled="!canRun" @click="run">{{ isMerge ? '合并 PDF' : '生成 PDF' }}</el-button>
      </footer>

      <div v-if="loading" class="running-note">
        <el-icon class="spin"><Loading /></el-icon><span>正在生成 PDF，长文档请耐心等待</span>
      </div>

      <section v-if="results.length" class="result-section">
        <div class="section-head">
          <div>
            <span>03</span>
            <div><b>已生成</b><small>输出文件已同步到任务中心</small></div>
          </div>
          <el-button v-if="form.outputDir" text type="primary" @click="reveal(form.outputDir)">打开输出目录</el-button>
        </div>
        <article v-for="item in results" :key="item.path" class="result-row">
          <div>
            <b>{{ item.fileName || item.path?.split(/[\\/]/).pop() }}</b
            ><small>{{ item.path }}</small>
          </div>
          <el-button text @click="openFile(item.path)">打开</el-button>
          <el-button text @click="reveal(item.path)">定位</el-button>
        </article>
      </section>
    </div>
  </section>
</template>

<style scoped>
.pdf-page {
  color: var(--ppx-text-secondary);
}
.page-intro {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
}
.eyebrow {
  color: var(--accent);
  font-size: 10.5px;
  font-weight: 750;
  letter-spacing: 0.08em;
}
.page-intro h2 {
  margin: 5px 0 7px;
  color: var(--ppx-text-primary);
  font-size: clamp(22px, 3vw, 29px);
  letter-spacing: -0.025em;
}
.page-intro p {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12.5px;
}
.engine-alert {
  margin-bottom: 16px;
}
.binding-sheet {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  background: var(--ppx-bg-surface);
  box-shadow: var(--ppx-shadow-sm);
  overflow: hidden;
}
.source-section,
.output-section,
.result-section {
  padding: clamp(17px, 2.5vw, 24px);
}
.output-section,
.result-section,
.run-row,
.running-note {
  border-top: 1px solid var(--ppx-glass-border);
}
.section-head,
.section-head > div,
.section-head > div > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.section-head {
  margin-bottom: 14px;
}
.section-head > div > span {
  display: inline-grid;
  place-items: center;
  width: 31px;
  height: 25px;
  flex: 0 0 auto;
  border-radius: 7px;
  background: color-mix(in srgb, var(--accent) 12%, var(--ppx-bg-inset));
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
}
.section-head > div > div {
  align-items: flex-start;
  flex-direction: column;
  gap: 3px;
}
.section-head b,
.run-row b,
.result-row b {
  color: var(--ppx-text-primary);
  font-size: 13px;
}
.section-head small,
.run-row small,
.result-row small {
  color: var(--ppx-text-muted);
  font-size: 10.5px;
}
.empty-source {
  min-height: 170px;
  display: flex;
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
.empty-source > span {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  margin-bottom: 10px;
  border-radius: 13px;
  background: color-mix(in srgb, var(--accent) 12%, var(--ppx-bg-inset));
  color: var(--accent);
}
.empty-source b {
  color: var(--ppx-text-primary);
  font-size: 13.5px;
}
.empty-source p {
  margin: 5px 0 0;
  color: var(--ppx-text-muted);
  font-size: 11.5px;
}
.option-grid {
  display: grid;
  grid-template-columns: minmax(220px, 0.75fr) minmax(0, 1.25fr);
  gap: 16px;
}
.option-grid label {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 7px;
}
.option-grid label > span {
  color: var(--ppx-text-secondary);
  font-size: 11.5px;
  font-weight: 650;
}
.path-field {
  display: flex;
  gap: 8px;
}
.run-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px clamp(17px, 2.5vw, 24px);
  background: var(--ppx-bg-base);
}
.run-row > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.running-note {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 12px clamp(17px, 2.5vw, 24px);
  color: var(--accent);
  font-size: 11.5px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.result-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  min-height: 54px;
  border-top: 1px solid var(--ppx-glass-border);
}
.result-row > div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.result-row b,
.result-row small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-row small {
  font-family: var(--ppx-font-mono);
}
@media (max-width: 700px) {
  .page-intro,
  .run-row {
    align-items: stretch;
    flex-direction: column;
  }
  .option-grid {
    grid-template-columns: 1fr;
  }
  .result-row {
    grid-template-columns: 1fr;
    padding: 10px 0;
  }
}
</style>
