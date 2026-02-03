<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const toFileUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('file://')) {
    return path
  }
  const normalized = path.replace(/\\/g, '/')
  if (/^[a-zA-Z]:\//.test(normalized)) {
    return `file:///${normalized}`
  }
  return normalized
}

const parseTimeToSeconds = (value) => {
  if (!value && value !== 0) return 0
  if (typeof value === 'number') {
    return value >= 0 ? value : 0
  }
  const text = String(value).trim()
  if (!text) return 0
  const parts = text.split(':').map((item) => Number.parseFloat(item || '0'))
  if (!parts.length || parts.some((n) => Number.isNaN(n) || n < 0)) {
    return 0
  }
  let seconds = 0
  if (parts.length === 1) {
    seconds = parts[0]
  } else if (parts.length === 2) {
    seconds = parts[0] * 60 + parts[1]
  } else {
    seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
  }
  return seconds >= 0 ? seconds : 0
}

const secondsToTime = (value) => {
  const total = Math.max(0, Math.floor(value || 0))
  const h = String(Math.floor(total / 3600)).padStart(2, '0')
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0')
  const s = String(total % 60).padStart(2, '0')
  return `${h}:${m}:${s}`
}

const state = reactive({
  loading: false,
  activeTab: 'convert',
  convert: {
    file: null,
    targetFormat: 'mp4',
    qualityPreset: 'medium',
    preset: 'medium',
    videoCodec: 'libx264',
    audioCodec: 'aac',
    outputDir: '',
    result: ''
  },
  compress: {
    file: null,
    mode: 'preset',
    bitrate: '1500k',
    targetSizeMB: 20,
    preset: 'balanced',
    ffPreset: 'medium',
    outputDir: '',
    result: ''
  },
  cut: {
    file: null,
    start: '00:00:00',
    end: '',
    outputDir: '',
    result: '',
    duration: 0,
    rangeStart: 0,
    rangeEnd: 0,
    previewUrl: ''
  },
  audio: {
    file: null,
    audioFormat: 'mp3',
    quality: 'medium',
    outputDir: '',
    result: '',
    start: '00:00:00',
    end: '',
    duration: 0,
    rangeStart: 0,
    rangeEnd: 0,
    previewUrl: ''
  },
  frames: {
    file: null,
    mode: 'time',
    interval: 5,
    imageFormat: 'png',
    outputDir: '',
    generatedDir: '',
    result: []
  },
  info: {
    file: null,
    data: null
  },
  concat: {
    files: [],
    reencode: false,
    targetFormat: 'mp4',
    preset: 'medium',
    outputDir: '',
    result: ''
  }
})

const cutVideoRef = ref(null)
const audioVideoRef = ref(null)

const cutRange = computed({
  get: () => {
    const duration = state.cut.duration || 0
    const start = Math.max(0, Math.min(state.cut.rangeStart || 0, duration))
    const endRaw = state.cut.rangeEnd || duration
    const end = Math.max(start, Math.min(endRaw, duration))
    return [start, end]
  },
  set: (val) => {
    if (!Array.isArray(val) || val.length < 2) return
    const duration = state.cut.duration || 0
    let [start, end] = val
    start = Math.max(0, Math.min(start ?? 0, duration))
    end = Math.max(start, Math.min(end ?? duration, duration))
    state.cut.rangeStart = start
    state.cut.rangeEnd = end
    state.cut.start = secondsToTime(start)
    if (!duration || Math.abs(end - duration) < 0.5) {
      state.cut.end = ''
    } else {
      state.cut.end = secondsToTime(end)
    }
  }
})

const audioRange = computed({
  get: () => {
    const duration = state.audio.duration || 0
    const start = Math.max(0, Math.min(state.audio.rangeStart || 0, duration))
    const endRaw = state.audio.rangeEnd || duration
    const end = Math.max(start, Math.min(endRaw, duration))
    return [start, end]
  },
  set: (val) => {
    if (!Array.isArray(val) || val.length < 2) return
    const duration = state.audio.duration || 0
    let [start, end] = val
    start = Math.max(0, Math.min(start ?? 0, duration))
    end = Math.max(start, Math.min(end ?? duration, duration))
    state.audio.rangeStart = start
    state.audio.rangeEnd = end
    state.audio.start = secondsToTime(start)
    if (!duration || Math.abs(end - duration) < 0.5) {
      state.audio.end = ''
    } else {
      state.audio.end = secondsToTime(end)
    }
  }
})

const onCutLoadedMetadata = () => {
  const video = cutVideoRef.value
  if (!video) return
  const duration = Number.isFinite(video.duration) ? video.duration : 0
  state.cut.duration = duration
  const start = parseTimeToSeconds(state.cut.start)
  const endRaw = parseTimeToSeconds(state.cut.end)
  const end = endRaw && endRaw > 0 ? endRaw : duration
  state.cut.rangeStart = Math.max(0, Math.min(start, duration))
  state.cut.rangeEnd = Math.max(state.cut.rangeStart, Math.min(end, duration))
}

const onAudioLoadedMetadata = () => {
  const video = audioVideoRef.value
  if (!video) return
  const duration = Number.isFinite(video.duration) ? video.duration : 0
  state.audio.duration = duration
  const start = parseTimeToSeconds(state.audio.start)
  const endRaw = parseTimeToSeconds(state.audio.end)
  const end = endRaw && endRaw > 0 ? endRaw : duration
  state.audio.rangeStart = Math.max(0, Math.min(start, duration))
  state.audio.rangeEnd = Math.max(state.audio.rangeStart, Math.min(end, duration))
}

const onCutRangeChange = (val) => {
  if (!cutVideoRef.value || !Array.isArray(val) || !val.length) return
  cutVideoRef.value.currentTime = val[0] || 0
}

const onAudioRangeChange = (val) => {
  if (!audioVideoRef.value || !Array.isArray(val) || !val.length) return
  audioVideoRef.value.currentTime = val[0] || 0
}

watch(
  () => state.cut.start,
  (value) => {
    const duration = state.cut.duration || 0
    let start = parseTimeToSeconds(value)
    if (duration && start > duration) start = duration
    state.cut.rangeStart = start
  }
)

watch(
  () => state.cut.end,
  (value) => {
    const duration = state.cut.duration || 0
    if (!value) {
      state.cut.rangeEnd = duration
      return
    }
    let end = parseTimeToSeconds(value)
    if (duration) {
      if (end < state.cut.rangeStart) end = state.cut.rangeStart
      if (end > duration) end = duration
    }
    state.cut.rangeEnd = end
  }
)

watch(
  () => state.audio.start,
  (value) => {
    const duration = state.audio.duration || 0
    let start = parseTimeToSeconds(value)
    if (duration && start > duration) start = duration
    state.audio.rangeStart = start
  }
)

watch(
  () => state.audio.end,
  (value) => {
    const duration = state.audio.duration || 0
    if (!value) {
      state.audio.rangeEnd = duration
      return
    }
    let end = parseTimeToSeconds(value)
    if (duration) {
      if (end < state.audio.rangeStart) end = state.audio.rangeStart
      if (end > duration) end = duration
    }
    state.audio.rangeEnd = end
  }
)

const loadVideoPreview = async (target) => {
  if (!ensurePyReady()) return
  const file = state[target]?.file
  if (!file) return
  const path = file.path || file.filename
  if (!path) return
  try {
    const res = await window.pywebview.api.video_preview({
      filePath: path
    })
    if (res?.code === 0 && res.preview) {
      state[target].previewUrl = res.preview
    } else {
      state[target].previewUrl = ''
      if (res?.msg) {
        ElMessage.error(res.msg)
      }
    }
  } catch (error) {
    state[target].previewUrl = ''
    ElMessage.error(error?.message || '视频预览失败')
  }
}

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectVideo = async (target) => {
  if (!ensurePyReady()) return
  const result = await window.pywebview.api.system_pyCreateFileDialog(videoFilter)
  if (result?.length) {
    const file = result[0]
    state[target].file = file
    if (target === 'cut') {
      state.cut.previewUrl = ''
      state.cut.duration = 0
      state.cut.rangeStart = 0
      state.cut.rangeEnd = 0
      state.cut.start = '00:00:00'
      state.cut.end = ''
      await loadVideoPreview('cut')
    }
    if (target === 'audio') {
      state.audio.previewUrl = ''
      state.audio.duration = 0
      state.audio.rangeStart = 0
      state.audio.rangeEnd = 0
      state.audio.start = '00:00:00'
      state.audio.end = ''
      await loadVideoPreview('audio')
    }
  }
}

const selectConcatFiles = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(videoFilter)
  if (files?.length) {
    state.concat.files.push(...files)
  }
}

const removeConcatFile = (index) => {
  state.concat.files.splice(index, 1)
}

const moveConcatFile = (index, direction) => {
  const target = index + direction
  if (target < 0 || target >= state.concat.files.length) return
  const temp = state.concat.files[index]
  state.concat.files[index] = state.concat.files[target]
  state.concat.files[target] = temp
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const current = state[target].outputDir
  const dir = await window.pywebview.api.system_pySelectDirDialog(current)
  if (dir) {
    state[target].outputDir = dir
  }
}

const ensureFile = (target) => {
  if (!state[target].file) {
    ElMessage.warning('请先选择视频文件')
    return false
  }
  return true
}

const runConvert = async () => {
  if (!ensurePyReady() || !ensureFile('convert')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.video_format_convert({
      filePath: state.convert.file.path,
      targetFormat: state.convert.targetFormat,
      qualityPreset: state.convert.qualityPreset,
      preset: state.convert.preset,
      videoCodec: state.convert.videoCodec,
      audioCodec: state.convert.audioCodec,
      outputDir: state.convert.outputDir
    })
    if (res?.code === 0) {
      state.convert.result = res.file || ''
      ElMessage.success(res.msg || '转换完成')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const runCompress = async () => {
  if (!ensurePyReady() || !ensureFile('compress')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.video_compress({
      filePath: state.compress.file.path,
      mode: state.compress.mode,
      bitrate: state.compress.bitrate,
      targetSizeMB: state.compress.targetSizeMB,
      preset: state.compress.preset,
      ffPreset: state.compress.ffPreset,
      outputDir: state.compress.outputDir
    })
    if (res?.code === 0) {
      state.compress.result = res.file || ''
      ElMessage.success(res.msg || '压缩完成')
    } else {
      ElMessage.error(res?.msg || '压缩失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '压缩失败')
  } finally {
    state.loading = false
  }
}

const runCut = async () => {
  if (!ensurePyReady() || !ensureFile('cut')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.video_cut({
      filePath: state.cut.file.path,
      start: state.cut.start,
      end: state.cut.end,
      outputDir: state.cut.outputDir
    })
    if (res?.code === 0) {
      state.cut.result = res.file || ''
      ElMessage.success(res.msg || '截取完成')
    } else {
      ElMessage.error(res?.msg || '截取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '截取失败')
  } finally {
    state.loading = false
  }
}

const runConcat = async () => {
  if (!ensurePyReady()) return
  if (!state.concat.files.length) {
    ElMessage.warning('请至少选择两个视频')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.video_concat({
      files: state.concat.files.map((file) => file.path || file),
      reencode: state.concat.reencode,
      targetFormat: state.concat.targetFormat,
      preset: state.concat.preset,
      outputDir: state.concat.outputDir
    })
    if (res?.code === 0) {
      state.concat.result = res.file || ''
      ElMessage.success(res.msg || '合成完成')
    } else {
      ElMessage.error(res?.msg || '合成失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '合成失败')
  } finally {
    state.loading = false
  }
}

const runAudio = async () => {
  if (!ensurePyReady() || !ensureFile('audio')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.video_extract_audio({
      filePath: state.audio.file.path,
      audioFormat: state.audio.audioFormat,
      quality: state.audio.quality,
      start: state.audio.start,
      end: state.audio.end,
      outputDir: state.audio.outputDir
    })
    if (res?.code === 0) {
      state.audio.result = res.file || ''
      ElMessage.success(res.msg || '提取完成')
    } else {
      ElMessage.error(res?.msg || '提取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '提取失败')
  } finally {
    state.loading = false
  }
}

const runFrames = async () => {
  if (!ensurePyReady() || !ensureFile('frames')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.video_extract_frames({
      filePath: state.frames.file.path,
      mode: state.frames.mode,
      interval: state.frames.interval,
      imageFormat: state.frames.imageFormat,
      outputDir: state.frames.outputDir
    })
    if (res?.code === 0) {
      state.frames.result = res.files || []
      state.frames.generatedDir = res.outputDir || state.frames.outputDir
      ElMessage.success(res.msg || '帧图已导出')
    } else {
      ElMessage.error(res?.msg || '导出失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '导出失败')
  } finally {
    state.loading = false
  }
}

const runInfo = async () => {
  if (!ensurePyReady() || !ensureFile('info')) return
  state.loading = true
  try {
    const res = await window.pywebview.api.video_get_info({
      filePath: state.info.file.path
    })
    if (res?.code === 0) {
      state.info.data = res.info || null
      ElMessage.success(res.msg || '信息已获取')
    } else {
      ElMessage.error(res?.msg || '获取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '获取失败')
  } finally {
    state.loading = false
  }
}

const openFile = (file) => {
  if (!ensurePyReady() || !file) return
  window.pywebview.api.system_pyOpenFile(file)
}

const openFramesDir = () => {
  const dir = state.frames.generatedDir || state.frames.outputDir
  if (dir) {
    openFile(dir)
  }
}
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="70%"
    append-to-body
    custom-class="video-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">VIDEO STUDIO</p>
          <h3>视频处理工具</h3>
          <p class="sub">格式转换、压缩、截取、音频与帧图导出</p>
        </div>
      </div>
    </template>
    <div class="video-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="格式转换" name="convert">
          <section class="panel">
            <header>
              <h4>转换目标格式</h4>
              <p>选择常见容器与编码预设</p>
            </header>
            <el-form :model="state.convert" label-width="120px">
              <el-form-item label="源视频">
                <div class="field-row">
                  <el-input :model-value="state.convert.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectVideo('convert')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="目标格式">
                <el-select v-model="state.convert.targetFormat" style="width: 200px">
                  <el-option label="MP4" value="mp4" />
                  <el-option label="MOV" value="mov" />
                  <el-option label="AVI" value="avi" />
                  <el-option label="MKV" value="mkv" />
                  <el-option label="WebM" value="webm" />
                </el-select>
              </el-form-item>
              <el-form-item label="质量预设">
                <el-radio-group v-model="state.convert.qualityPreset">
                  <el-radio-button label="original">原画</el-radio-button>
                  <el-radio-button label="high">高清</el-radio-button>
                  <el-radio-button label="medium">均衡</el-radio-button>
                  <el-radio-button label="low">体积优先</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.convert.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('convert')">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runConvert">开始转换</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.convert.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已生成：<a class="link" @click.prevent="openFile(state.convert.result)">{{ state.convert.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="视频压缩" name="compress">
          <section class="panel">
            <header>
              <h4>压缩模式</h4>
              <p>按码率、目标大小或预设压缩</p>
            </header>
            <el-form :model="state.compress" label-width="120px">
              <el-form-item label="源视频">
                <div class="field-row">
                  <el-input :model-value="state.compress.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectVideo('compress')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="模式">
                <el-radio-group v-model="state.compress.mode">
                  <el-radio-button label="preset">预设</el-radio-button>
                  <el-radio-button label="bitrate">码率</el-radio-button>
                  <el-radio-button label="size">目标大小</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.compress.mode === 'bitrate'" label="码率">
                <el-input v-model="state.compress.bitrate" placeholder="例如 1500k" />
              </el-form-item>
              <el-form-item v-else-if="state.compress.mode === 'size'" label="目标大小 (MB)">
                <el-input-number v-model="state.compress.targetSizeMB" :min="5" :max="5000" />
              </el-form-item>
              <template v-else>
                <el-form-item label="预设">
                  <el-select v-model="state.compress.preset" style="width: 200px">
                    <el-option label="高清优先" value="high" />
                    <el-option label="均衡" value="balanced" />
                    <el-option label="体积最小" value="small" />
                  </el-select>
                </el-form-item>
                <el-form-item label="FFmpeg 预设">
                  <el-select v-model="state.compress.ffPreset" style="width: 200px">
                    <el-option label="极快（调试用）" value="ultrafast" />
                    <el-option label="很快（画质较低）" value="superfast" />
                    <el-option label="快速（体积较小）" value="fast" />
                    <el-option label="均衡（推荐）" value="medium" />
                    <el-option label="更好画质（编码更慢）" value="slow" />
                  </el-select>
                </el-form-item>
              </template>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.compress.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('compress')">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCompress">开始压缩</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.compress.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已输出：<a class="link" @click.prevent="openFile(state.compress.result)">{{ state.compress.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="视频截取" name="cut">
          <section class="panel">
            <header>
              <h4>截取片段</h4>
              <p>按起止时间截取，无需重新编码</p>
            </header>
            <div v-if="state.cut.file" class="video-preview-block">
              <video
                ref="cutVideoRef"
                class="video-preview"
                :src="state.cut.previewUrl"
                controls
                @loadedmetadata="onCutLoadedMetadata"
              />
              <el-slider
                v-if="state.cut.duration"
                v-model="cutRange"
                :min="0"
                :max="state.cut.duration"
                :step="1"
                range
                class="video-range-slider"
                @change="onCutRangeChange"
              />
              <div v-if="state.cut.duration" class="video-range-meta">
                <span>开始：{{ state.cut.start || '00:00:00' }}</span>
                <span>结束：{{ state.cut.end || '视频末尾' }}</span>
                <span>总长：{{ secondsToTime(state.cut.duration) }}</span>
              </div>
            </div>
            <el-form :model="state.cut" label-width="120px">
              <el-form-item label="源视频">
                <div class="field-row">
                  <el-input :model-value="state.cut.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectVideo('cut')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="开始时间">
                <el-input v-model="state.cut.start" placeholder="00:00:00" />
              </el-form-item>
              <el-form-item label="结束时间">
                <el-input v-model="state.cut.end" placeholder="可选，00:00:00" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.cut.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('cut')">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCut">截取</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.cut.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                输出文件：<a class="link" @click.prevent="openFile(state.cut.result)">{{ state.cut.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="音频提取" name="audio">
          <section class="panel">
            <header>
              <h4>视频转音频</h4>
              <p>输出 MP3 / WAV / AAC / FLAC，支持质量预设与时间截取</p>
            </header>
            <div v-if="state.audio.file" class="video-preview-block">
              <video
                ref="audioVideoRef"
                class="video-preview"
                :src="state.audio.previewUrl"
                controls
                @loadedmetadata="onAudioLoadedMetadata"
              />
              <el-slider
                v-if="state.audio.duration"
                v-model="audioRange"
                :min="0"
                :max="state.audio.duration"
                :step="1"
                range
                class="video-range-slider"
                @change="onAudioRangeChange"
              />
              <div v-if="state.audio.duration" class="video-range-meta">
                <span>开始：{{ state.audio.start || '00:00:00' }}</span>
                <span>结束：{{ state.audio.end || '视频末尾' }}</span>
                <span>总长：{{ secondsToTime(state.audio.duration) }}</span>
              </div>
            </div>
            <el-form :model="state.audio" label-width="120px">
              <el-form-item label="源视频">
                <div class="field-row">
                  <el-input :model-value="state.audio.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectVideo('audio')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="音频格式">
                <el-select v-model="state.audio.audioFormat" style="width: 200px">
                  <el-option label="MP3" value="mp3" />
                  <el-option label="WAV" value="wav" />
                  <el-option label="AAC" value="aac" />
                  <el-option label="FLAC" value="flac" />
                </el-select>
              </el-form-item>
              <el-form-item label="质量">
                <el-radio-group v-model="state.audio.quality">
                  <el-radio-button label="high">高质量</el-radio-button>
                  <el-radio-button label="medium">均衡</el-radio-button>
                  <el-radio-button label="low">小体积</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="开始时间">
                <el-input v-model="state.audio.start" placeholder="00:00:00" />
              </el-form-item>
              <el-form-item label="结束时间">
                <el-input v-model="state.audio.end" placeholder="可选，00:00:00" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.audio.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('audio')">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runAudio">提取音频</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.audio.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已输出：<a class="link" @click.prevent="openFile(state.audio.result)">{{ state.audio.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>        <el-tab-pane label="帧图导出" name="frames">
          <section class="panel">
            <header>
              <h4>按时间 / 帧提取图片</h4>
              <p>支持每 N 秒或每 N 帧保存，自动保存到目录</p>
            </header>
            <el-form :model="state.frames" label-width="120px">
              <el-form-item label="源视频">
                <div class="field-row">
                  <el-input :model-value="state.frames.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectVideo('frames')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="模式">
                <el-radio-group v-model="state.frames.mode">
                  <el-radio-button label="time">每 N 秒</el-radio-button>
                  <el-radio-button label="frame">每 N 帧</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item :label="state.frames.mode === 'time' ? '间隔 (秒)' : '间隔 (帧)'">
                <el-input-number v-model="state.frames.interval" :min="1" :max="3600" />
              </el-form-item>
              <el-form-item label="图片格式">
                <el-select v-model="state.frames.imageFormat" style="width: 200px">
                  <el-option label="PNG" value="png" />
                  <el-option label="JPG" value="jpg" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.frames.outputDir" placeholder="自动创建" readonly />
                  <el-button @click="selectDir('frames')">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runFrames">开始导出</el-button>
              </el-form-item>
            </el-form>
            <el-table
              v-if="state.frames.result.length"
              :data="state.frames.result"
              border
              size="small"
              style="margin-top: 12px"
            >
              <el-table-column label="示例文件" align="left">
                <template #default="scope">
                  <a class="link" @click.prevent="openFile(scope.row)">{{ scope.row }}</a>
                </template>
              </el-table-column>
            </el-table>
            <el-button
              v-if="state.frames.result.length"
              type="primary"
              link
              @click="openFramesDir"
            >
              打开输出目录
            </el-button>
          </section>
        </el-tab-pane>

        <el-tab-pane label="视频合成" name="concat">
          <section class="panel">
            <header>
              <h4>多视频拼接</h4>
              <p>支持直接无损合并或重新编码输出，保持自定义排序</p>
            </header>
            <div class="field-row">
              <el-button @click="selectConcatFiles">添加视频文件</el-button>
              <el-button text type="danger" :disabled="!state.concat.files.length" @click="state.concat.files = []">
                清空
              </el-button>
            </div>
            <el-table
              v-if="state.concat.files.length"
              :data="state.concat.files"
              border
              size="small"
              style="margin: 16px 0"
            >
              <el-table-column type="index" width="50" label="#" />
              <el-table-column label="文件名" prop="filename" show-overflow-tooltip />
              <el-table-column label="路径" show-overflow-tooltip>
                <template #default="scope">
                  {{ scope.row.path }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="scope">
                  <el-button text size="small" @click="moveConcatFile(scope.$index, -1)">上移</el-button>
                  <el-button text size="small" @click="moveConcatFile(scope.$index, 1)">下移</el-button>
                  <el-button text size="small" type="danger" @click="removeConcatFile(scope.$index)">移除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-alert v-else type="info" :closable="false" show-icon>
              <template #title>请选择至少两个视频文件</template>
            </el-alert>
            <el-form :model="state.concat" label-width="140px" class="form-block">
              <el-form-item label="输出格式">
                <div class="field-row">
                  <el-select v-model="state.concat.targetFormat" style="width: 160px">
                    <el-option label="MP4" value="mp4" />
                    <el-option label="MOV" value="mov" />
                    <el-option label="MKV" value="mkv" />
                  </el-select>
                  <el-switch
                    v-model="state.concat.reencode"
                    active-text="重新编码（兼容不同参数）"
                  />
                </div>
              </el-form-item>
              <el-form-item v-if="state.concat.reencode" label="编码预设">
                <el-select v-model="state.concat.preset" style="width: 200px">
                  <el-option label="更好画质" value="slow" />
                  <el-option label="平衡" value="medium" />
                  <el-option label="更快" value="fast" />
                </el-select>
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.concat.outputDir" placeholder="留空自动创建" readonly />
                  <el-button @click="selectDir('concat')">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  :loading="state.loading"
                  :disabled="state.concat.files.length < 2"
                  @click="runConcat"
                >
                  开始合成
                </el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.concat.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已输出：<a class="link" @click.prevent="openFile(state.concat.result)">{{ state.concat.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="视频信息" name="info">
          <section class="panel">
            <header>
              <h4>快速查看参数</h4>
              <p>显示时长、分辨率、码率、编码器等关键指标</p>
            </header>
            <el-form :model="state.info" label-width="120px">
              <el-form-item label="视频文件">
                <div class="field-row">
                  <el-input :model-value="state.info.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectVideo('info')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runInfo">获取信息</el-button>
              </el-form-item>
            </el-form>
            <el-descriptions
              v-if="state.info.data"
              :column="3"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-descriptions-item label="时长 (s)">{{ state.info.data.duration }}</el-descriptions-item>
              <el-descriptions-item label="分辨率">{{ state.info.data.width }}×{{ state.info.data.height }}</el-descriptions-item>
              <el-descriptions-item label="帧率">{{ state.info.data.fps }}</el-descriptions-item>
              <el-descriptions-item label="视频编码">{{ state.info.data.videoCodec }}</el-descriptions-item>
              <el-descriptions-item label="音频编码">{{ state.info.data.audioCodec }}</el-descriptions-item>
              <el-descriptions-item label="码率 (bps)">{{ state.info.data.bitrate }}</el-descriptions-item>
            </el-descriptions>
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 使用全局深空玻璃主题样式 */

/* 视频预览 */
.video-preview-block {
  margin-bottom: 16px;
}

.video-preview {
  width: 100%;
  max-height: 260px;
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-ink);
}

.video-range-slider {
  margin-top: 10px;
}

.video-range-meta {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ppx-text-muted);
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}

</style>


