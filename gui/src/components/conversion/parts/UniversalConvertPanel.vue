<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ArrowRight, Delete, FolderOpened, Loading, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'
import ConversionFileQueue from './ConversionFileQueue.vue'

const props = defineProps({ engine: { type: Object, required: true } })
const emit = defineEmits(['open-engine'])

const FILE_FILTER = [
  '可转换文件 (*.jpg;*.jpeg;*.png;*.webp;*.gif;*.avif;*.tif;*.tiff;*.bmp;*.heic;*.heif;*.ico;*.tga;*.cr2;*.cr3;*.nef;*.arw;*.dng;*.txt;*.md;*.html;*.json;*.csv;*.xml;*.yaml;*.epub;*.mobi;*.doc;*.docx;*.odt;*.rtf;*.wps;*.wpt;*.wpd;*.ofd;*.xls;*.xlsx;*.xlsm;*.ods;*.tsv;*.et;*.ett;*.ppt;*.pptx;*.odp;*.dps;*.dpt;*.pdf;*.mp3;*.wav;*.flac;*.m4a;*.aac;*.ogg;*.opus;*.wma;*.mp4;*.mov;*.mkv;*.webm;*.avi;*.m4v;*.wmv;*.flv;*.zip)',
  '全部文件 (*.*)'
]
const PREFERENCE_KEY = 'ppx-conversion-target-by-source'

const files = ref([])
const targets = ref([])
const results = ref([])
const failures = ref([])
const warnings = ref([])
const loading = ref(false)
const dropActive = ref(false)
let analysisSequence = 0
const analysis = reactive({ loading: false, error: '', items: [], mixed: false })
const form = reactive({
  targetFormat: '',
  outputDir: '',
  compressionLevel: '6',
  videoCodec: 'h264',
  advanced: false
})

const formatLabels = {
  jpg: 'JPG 图片',
  png: 'PNG 图片',
  webp: 'WebP 图片',
  avif: 'AVIF 图片',
  tiff: 'TIFF 图片',
  gif: 'GIF 动图',
  pdf: 'PDF 文档',
  docx: 'Word 文档',
  xlsx: 'Excel 工作簿',
  pptx: 'PowerPoint 演示',
  txt: '纯文本',
  md: 'Markdown',
  html: 'HTML 网页',
  json: 'JSON 数据',
  csv: 'CSV 表格',
  epub: 'EPUB 电子书',
  zip: 'ZIP 压缩包',
  mp4: 'MP4 视频',
  mov: 'MOV 视频',
  mkv: 'MKV 视频',
  webm: 'WebM 视频',
  mp3: 'MP3 音频',
  wav: 'WAV 音频',
  flac: 'FLAC 音频',
  m4a: 'M4A 音频',
  ogg: 'OGG 音频',
  aac: 'AAC 音频',
  opus: 'OPUS 音频',
  wma: 'WMA 音频'
}
const categoryLabels = {
  image: '图片',
  text: '文本',
  document: '文档',
  spreadsheet: '表格',
  presentation: '演示文稿',
  pdf: 'PDF',
  audio: '音频',
  video: '视频',
  zip: '压缩包'
}

const filePath = (file) => file?.path || String(file || '')
const fileName = (file) => file?.filename || filePath(file).split(/[\\/]/).pop()
const extensionOf = (file) => {
  const match = fileName(file).toLowerCase().match(/\.([^.]+)$/)
  return match?.[1] || ''
}
const sourceExtensions = computed(() => [...new Set(files.value.map(extensionOf).filter(Boolean))])
const sourceCategories = computed(() => [...new Set(analysis.items.map((item) => item.category).filter(Boolean))])
const sourceSummary = computed(() => {
  if (!files.value.length) return '等待文件'
  if (analysis.loading) return '正在识别'
  if (sourceCategories.value.length === 1) return `${categoryLabels[sourceCategories.value[0]] || sourceCategories.value[0]} · ${files.value.length} 个文件`
  return `${sourceCategories.value.length} 类格式 · ${files.value.length} 个文件`
})
const targetOptions = computed(() => targets.value.map((value) => ({ value, label: formatLabels[value] || value.toUpperCase() })))
const showCompression = computed(() => form.targetFormat === 'zip')
const showVideoCodec = computed(() => ['mp4', 'mov', 'mkv'].includes(form.targetFormat))
const hasAdvancedOptions = computed(() => showCompression.value || showVideoCodec.value)
const canRun = computed(() => props.engine.available && files.value.length && form.targetFormat && !analysis.loading && !loading.value)

const normalizeFile = (item) => {
  const path = typeof item === 'string' ? item : item?.path
  if (!path) return null
  return {
    ...(typeof item === 'object' ? item : {}),
    path,
    filename: typeof item === 'object' && item.filename ? item.filename : path.split(/[\\/]/).pop()
  }
}

const readPreferences = () => {
  try {
    const value = JSON.parse(localStorage.getItem(PREFERENCE_KEY) || '{}')
    return value && typeof value === 'object' ? value : {}
  } catch {
    return {}
  }
}

const rememberTarget = (value) => {
  if (!value) return
  const preferences = readPreferences()
  sourceExtensions.value.forEach((extension) => {
    preferences[extension] = value
  })
  try {
    localStorage.setItem(PREFERENCE_KEY, JSON.stringify(preferences))
  } catch {
    // 目标格式记忆是增强功能，失败时不影响转换。
  }
}

const chooseRememberedTarget = () => {
  if (targets.value.includes(form.targetFormat)) return
  const preferences = readPreferences()
  const remembered = [...new Set(sourceExtensions.value.map((extension) => preferences[extension]).filter(Boolean))]
  form.targetFormat = remembered.length === 1 && targets.value.includes(remembered[0]) ? remembered[0] : targets.value.length === 1 ? targets.value[0] : ''
}

const analyzeFiles = async () => {
  const sequence = ++analysisSequence
  analysis.error = ''
  analysis.items = []
  targets.value = []
  if (!files.value.length) {
    analysis.loading = false
    form.targetFormat = ''
    return
  }
  if (!props.engine.available) {
    analysis.loading = false
    analysis.error = props.engine.detail || '转换引擎未就绪'
    return
  }
  analysis.loading = true
  try {
    const { ok, data, message } = await callApi('format_center_targets', { files: files.value.map(filePath) })
    if (sequence !== analysisSequence) return
    if (!ok) throw new Error(message || '无法分析目标格式')
    const payload = data && typeof data === 'object' ? data : {}
    analysis.items = payload.items || []
    analysis.mixed = Boolean(payload.mixed)
    targets.value = payload.commonTargets || []
    if (!targets.value.length) {
      analysis.error = '这些文件没有共同的目标格式，请按同类文件分批转换。'
      form.targetFormat = ''
      return
    }
    chooseRememberedTarget()
  } catch (error) {
    if (sequence !== analysisSequence) return
    analysis.error = error?.message || '格式分析失败'
    form.targetFormat = ''
  } finally {
    if (sequence === analysisSequence) analysis.loading = false
  }
}

const addFiles = async (items = []) => {
  const normalized = items.map(normalizeFile).filter(Boolean)
  if (!normalized.length) return
  const combined = [...files.value, ...normalized]
  const seen = new Set()
  files.value = combined.filter((item) => {
    const identity = filePath(item).toLowerCase()
    if (!identity || seen.has(identity)) return false
    seen.add(identity)
    return true
  })
  results.value = []
  failures.value = []
  warnings.value = []
  await analyzeFiles()
}

const selectFiles = async () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在 PPX 桌面客户端中使用')
    return
  }
  const picked = await callApiRaw('system_pyCreateFileDialog', FILE_FILTER)
  if (picked?.length) await addFiles(picked)
}

const removeFile = async (index) => {
  files.value.splice(index, 1)
  await analyzeFiles()
}

const clearFiles = () => {
  analysisSequence += 1
  files.value = []
  targets.value = []
  results.value = []
  failures.value = []
  warnings.value = []
  form.targetFormat = ''
  analysis.error = ''
  analysis.items = []
  analysis.loading = false
}

const handleDrop = async (event) => {
  dropActive.value = false
  const dropped = Array.from(event.dataTransfer?.files || []).filter((file) => file?.path)
  if (!dropped.length) {
    ElMessage.info('当前窗口无法读取拖入文件的本地路径，请使用“添加文件”')
    return
  }
  await addFiles(dropped)
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

const runConversion = async () => {
  if (!canRun.value) {
    ElMessage.warning(!props.engine.available ? '请先连接转换引擎' : !files.value.length ? '请先添加文件' : '请选择目标格式')
    return
  }
  loading.value = true
  results.value = []
  failures.value = []
  warnings.value = []
  try {
    rememberTarget(form.targetFormat)
    const { ok, data, message } = await callApi('format_center_convert', {
      files: files.value.map(filePath),
      targetFormat: form.targetFormat,
      outputDir: form.outputDir,
      compressionLevel: form.compressionLevel,
      videoCodec: form.videoCodec
    })
    const payload = data && typeof data === 'object' ? data : {}
    failures.value = Array.isArray(payload.failures) ? payload.failures : []
    form.outputDir = payload.outputDir || form.outputDir
    if (!ok) {
      if (failures.value.length) {
        ElMessage.error(message || '转换失败')
        return
      }
      throw new Error(message || '转换失败')
    }
    const rawOutputs = Array.isArray(payload.outputs) ? payload.outputs : Array.isArray(payload.files) ? payload.files : []
    results.value = rawOutputs.map((item) => (typeof item === 'string' ? { path: item, fileName: item.split(/[\\/]/).pop() } : item)).filter((item) => item?.path)
    warnings.value = Array.isArray(payload.warnings) ? payload.warnings : []
    if (failures.value.length) ElMessage.warning(message || `转换完成，${failures.value.length} 个文件失败`)
    else ElMessage.success(message || '转换完成')
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    loading.value = false
  }
}

const onLaunchFiles = (event) => addFiles(event.detail?.files || [])

watch(
  () => props.engine.available,
  (available) => {
    if (available && files.value.length && !targets.value.length && !analysis.loading) analyzeFiles()
  }
)
watch(
  () => form.targetFormat,
  (value) => {
    if (value) rememberTarget(value)
  }
)

onMounted(() => {
  window.addEventListener('ppx-open-files', onLaunchFiles)
  if (Array.isArray(window.__PPX_OPEN_FILES__) && window.__PPX_OPEN_FILES__.length) addFiles(window.__PPX_OPEN_FILES__)
})
onUnmounted(() => window.removeEventListener('ppx-open-files', onLaunchFiles))
</script>

<template>
  <section class="convert-page">
    <header class="page-intro">
      <div>
        <span class="eyebrow">全格式工作台</span>
        <h2>把不同文件，送往同一个目标。</h2>
        <p>支持图片、文本、Office / WPS、PDF、音频、视频、电子书与压缩包；目标格式会按所选文件实时收敛。</p>
      </div>
      <el-tag :type="engine.available ? 'success' : 'warning'" effect="plain">{{ engine.loading ? '检测引擎' : engine.available ? '本地引擎已就绪' : '需要连接引擎' }}</el-tag>
    </header>

    <el-alert v-if="!engine.loading && !engine.available" class="engine-alert" type="warning" :closable="false" show-icon>
      <template #title>{{ engine.detail }}</template>
      <el-button text type="primary" size="small" @click="emit('open-engine')">查看连接方式</el-button>
    </el-alert>

    <div class="flow">
      <section class="step-block source-step">
        <div class="step-head">
          <span class="step-index">01</span>
          <div><b>添加源文件</b><small>可混合选择；转换中心只显示所有文件共有的目标格式</small></div>
          <div class="step-actions">
            <el-button v-if="files.length" text :disabled="loading" @click="clearFiles"><el-icon><Delete /></el-icon>清空</el-button>
            <el-button type="primary" :disabled="loading" @click="selectFiles"><el-icon><Plus /></el-icon>添加文件</el-button>
          </div>
        </div>
        <div
          v-if="!files.length"
          class="drop-zone"
          :class="{ active: dropActive }"
          role="button"
          tabindex="0"
          @click="selectFiles"
          @keydown.enter="selectFiles"
          @dragenter.prevent="dropActive = true"
          @dragover.prevent="dropActive = true"
          @dragleave.prevent="dropActive = false"
          @drop.prevent="handleDrop"
        >
          <span class="drop-plus"><el-icon :size="22"><Plus /></el-icon></span>
          <b>选择或拖入要转换的文件</b>
          <p>可一次添加多种格式；所有处理都在本机完成</p>
        </div>
        <ConversionFileQueue v-else :files="files" :busy="loading" @remove="removeFile" />
      </section>

      <div class="route-line" aria-label="转换路径">
        <div><small>输入</small><b>{{ sourceSummary }}</b></div>
        <span><el-icon><ArrowRight /></el-icon></span>
        <div><small>输出</small><b>{{ form.targetFormat ? formatLabels[form.targetFormat] || form.targetFormat.toUpperCase() : '选择目标格式' }}</b></div>
      </div>

      <section class="step-block target-step">
        <div class="step-head">
          <span class="step-index">02</span>
          <div><b>设置输出</b><small>先选择目标格式，再按需展开相关高级选项</small></div>
        </div>

        <el-alert v-if="analysis.error" class="analysis-alert" type="warning" :closable="false" :title="analysis.error" />
        <div class="option-grid">
          <label class="option-field">
            <span>目标格式</span>
            <el-select v-model="form.targetFormat" filterable :loading="analysis.loading" :disabled="!files.length || Boolean(analysis.error)" placeholder="选择共同目标格式">
              <el-option v-for="item in targetOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <small v-if="analysis.mixed">已按混合文件计算格式交集</small>
          </label>
          <label class="option-field output-field">
            <span>输出目录</span>
            <div class="path-field">
              <el-input v-model="form.outputDir" readonly placeholder="默认保存到 下载/PPX转换结果" />
              <el-button @click="selectOutputDir"><el-icon><FolderOpened /></el-icon>选择</el-button>
            </div>
          </label>
        </div>

        <button v-if="hasAdvancedOptions" class="advanced-toggle" type="button" :aria-expanded="form.advanced" @click="form.advanced = !form.advanced">
          <span>{{ form.advanced ? '收起高级选项' : '显示此格式的高级选项' }}</span><small>{{ form.targetFormat.toUpperCase() }}</small>
        </button>
        <el-collapse-transition>
          <div v-if="hasAdvancedOptions && form.advanced" class="advanced-grid">
            <label v-if="showCompression" class="option-field">
              <span>ZIP 压缩级别</span>
              <el-radio-group v-model="form.compressionLevel">
                <el-radio-button label="1">快速</el-radio-button>
                <el-radio-button label="6">均衡</el-radio-button>
                <el-radio-button label="9">更小</el-radio-button>
              </el-radio-group>
            </label>
            <label v-if="showVideoCodec" class="option-field">
              <span>视频编码</span>
              <el-radio-group v-model="form.videoCodec">
                <el-radio-button label="h264">H.264</el-radio-button>
                <el-radio-button label="h265">H.265</el-radio-button>
                <el-radio-button label="av1">AV1</el-radio-button>
              </el-radio-group>
            </label>
          </div>
        </el-collapse-transition>
      </section>

      <section class="run-row">
        <div>
          <b>{{ files.length ? `${files.length} 个文件已加入队列` : '等待文件' }}</b>
          <small>转换期间可在任务中心查看状态；长文档和视频可能需要较长时间</small>
        </div>
        <el-button type="primary" size="large" :loading="loading" :disabled="!canRun" @click="runConversion">开始转换</el-button>
      </section>

      <div v-if="loading" class="running-note">
        <el-icon class="spin"><Loading /></el-icon>
        <span><b>FlyingMouse 正在本机处理文件</b><small>请保持应用运行，完成后结果会自动写入任务中心</small></span>
      </div>

      <section v-if="results.length || failures.length" class="result-section">
        <div class="result-head">
          <div><span class="step-index">03</span><div><b>转换结果</b><small>{{ results.length }} 个成功<span v-if="failures.length"> · {{ failures.length }} 个失败</span></small></div></div>
          <el-button v-if="form.outputDir" text type="primary" @click="reveal(form.outputDir)">打开输出目录</el-button>
        </div>
        <div class="result-list">
          <article v-for="item in results" :key="item.path">
            <span class="result-status">完成</span>
            <div><b>{{ item.fileName || item.path?.split(/[\\/]/).pop() }}</b><small>{{ item.path }}</small></div>
            <el-button text @click="openFile(item.path)">打开</el-button>
            <el-button text @click="reveal(item.path)">定位</el-button>
          </article>
          <article v-for="item in failures" :key="`failed-${item.input}`" class="failed">
            <span class="result-status">失败</span>
            <div><b>{{ item.input?.split(/[\\/]/).pop() || '文件转换失败' }}</b><small>{{ item.error }}</small></div>
          </article>
        </div>
        <el-alert v-if="warnings.length" class="warning-list" type="warning" :closable="false" :title="warnings.join('；')" />
      </section>
    </div>
  </section>
</template>

<style scoped>
.convert-page {
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
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.page-intro h2 {
  margin: 5px 0 7px;
  color: var(--ppx-text-primary);
  font-size: clamp(22px, 3vw, 29px);
  letter-spacing: -0.025em;
}
.page-intro p {
  max-width: 680px;
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12.5px;
  line-height: 1.6;
}
.engine-alert {
  margin-bottom: 16px;
}
.flow {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  background: var(--ppx-bg-surface);
  box-shadow: var(--ppx-shadow-sm);
  overflow: hidden;
}
.step-block {
  padding: clamp(17px, 2.5vw, 24px);
}
.step-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 31px;
  height: 25px;
  flex: 0 0 auto;
  border-radius: 7px;
  background: color-mix(in srgb, var(--accent) 12%, var(--ppx-bg-inset));
  color: var(--accent);
  font-size: 10px;
  font-weight: 800;
}
.step-head > div:nth-child(2),
.run-row > div,
.result-head > div > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.step-head b,
.run-row b,
.result-head b {
  color: var(--ppx-text-primary);
  font-size: 13.5px;
}
.step-head small,
.run-row small,
.result-head small {
  color: var(--ppx-text-muted);
  font-size: 11px;
}
.step-actions {
  display: flex;
  gap: 7px;
  margin-left: auto;
}
.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 156px;
  padding: 20px;
  border: 1px dashed var(--ppx-glass-border-hover);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-base);
  cursor: pointer;
  transition: border-color var(--ppx-transition-fast), background var(--ppx-transition-fast), transform var(--ppx-transition-fast);
}
.drop-zone:hover,
.drop-zone.active,
.drop-zone:focus-visible {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 5%, var(--ppx-bg-base));
  outline: none;
}
.drop-zone.active {
  transform: scale(0.995);
}
.drop-plus {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  margin-bottom: 10px;
  border-radius: 13px;
  background: color-mix(in srgb, var(--accent) 12%, var(--ppx-bg-inset));
  color: var(--accent);
}
.drop-zone b {
  color: var(--ppx-text-primary);
  font-size: 13.5px;
}
.drop-zone p {
  margin: 5px 0 0;
  color: var(--ppx-text-muted);
  font-size: 11.5px;
}
.route-line {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 34px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 11px clamp(17px, 2.5vw, 24px);
  border-top: 1px solid var(--ppx-glass-border);
  border-bottom: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-inset);
}
.route-line > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.route-line > div:last-child {
  text-align: right;
}
.route-line small {
  color: var(--ppx-text-muted);
  font-size: 9.5px;
  font-weight: 700;
  text-transform: uppercase;
}
.route-line b {
  overflow: hidden;
  color: var(--ppx-text-primary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.route-line > span {
  display: grid;
  place-items: center;
  color: var(--accent);
}
.analysis-alert {
  margin-bottom: 14px;
}
.option-grid,
.advanced-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.4fr);
  gap: 16px;
}
.option-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.option-field > span {
  color: var(--ppx-text-secondary);
  font-size: 11.5px;
  font-weight: 650;
}
.option-field > small {
  color: var(--ppx-text-muted);
  font-size: 10px;
}
.option-field :deep(.el-select) {
  width: 100%;
}
.path-field {
  display: flex;
  gap: 8px;
}
.advanced-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 9px 11px;
  border: none;
  border-radius: var(--ppx-radius-sm);
  background: var(--ppx-bg-inset);
  color: var(--ppx-text-secondary);
  cursor: pointer;
  font: inherit;
  font-size: 11.5px;
}
.advanced-toggle small {
  color: var(--accent);
  font: 10px var(--ppx-font-mono);
}
.advanced-grid {
  margin-top: 14px;
  padding: 15px;
  border-radius: var(--ppx-radius-sm);
  background: var(--ppx-bg-base);
}
.run-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px clamp(17px, 2.5vw, 24px);
  border-top: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-base);
}
.running-note {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px clamp(17px, 2.5vw, 24px);
  border-top: 1px solid var(--ppx-glass-border);
  color: var(--accent);
}
.running-note span {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.running-note b {
  color: var(--ppx-text-primary);
  font-size: 12px;
}
.running-note small {
  color: var(--ppx-text-muted);
  font-size: 10.5px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.result-section {
  padding: clamp(17px, 2.5vw, 24px);
  border-top: 1px solid var(--ppx-glass-border);
}
.result-head,
.result-head > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.result-list {
  margin-top: 13px;
  border-top: 1px solid var(--ppx-glass-border);
}
.result-list article {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 9px;
  min-height: 54px;
  border-bottom: 1px solid var(--ppx-glass-border);
}
.result-list article > div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.result-list article b {
  overflow: hidden;
  color: var(--ppx-text-primary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-list article small {
  overflow: hidden;
  color: var(--ppx-text-muted);
  font: 10px var(--ppx-font-mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-status {
  color: var(--el-color-success);
  font-size: 10.5px;
  font-weight: 700;
}
.result-list article.failed {
  grid-template-columns: 52px minmax(0, 1fr);
}
.failed .result-status {
  color: var(--el-color-danger);
}
.warning-list {
  margin-top: 12px;
}
@media (max-width: 700px) {
  .page-intro,
  .run-row {
    align-items: stretch;
    flex-direction: column;
  }
  .step-head {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .step-actions {
    width: 100%;
    margin-left: 43px;
  }
  .option-grid,
  .advanced-grid {
    grid-template-columns: 1fr;
  }
  .result-list article {
    grid-template-columns: 46px minmax(0, 1fr);
  }
  .result-list article .el-button {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
