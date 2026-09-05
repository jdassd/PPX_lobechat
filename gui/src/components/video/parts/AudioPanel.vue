<script setup>
import VideoInspection from '../../shared/VideoInspection.vue'
import { useDraft } from '../../../utils/workspace'
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = useDraft('video/parts/AudioPanel/form', {
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
})

const audioVideoRef = ref(null)

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

const audioRange = computed({
  get: () => {
    const duration = form.duration || 0
    const start = Math.max(0, Math.min(form.rangeStart || 0, duration))
    const endRaw = form.rangeEnd || duration
    const end = Math.max(start, Math.min(endRaw, duration))
    return [start, end]
  },
  set: (val) => {
    if (!Array.isArray(val) || val.length < 2) return
    const duration = form.duration || 0
    let [start, end] = val
    start = Math.max(0, Math.min(start ?? 0, duration))
    end = Math.max(start, Math.min(end ?? duration, duration))
    form.rangeStart = start
    form.rangeEnd = end
    form.start = secondsToTime(start)
    if (!duration || Math.abs(end - duration) < 0.5) {
      form.end = ''
    } else {
      form.end = secondsToTime(end)
    }
  }
})

const onAudioLoadedMetadata = () => {
  const video = audioVideoRef.value
  if (!video) return
  const duration = Number.isFinite(video.duration) ? video.duration : 0
  form.duration = duration
  const start = parseTimeToSeconds(form.start)
  const endRaw = parseTimeToSeconds(form.end)
  const end = endRaw && endRaw > 0 ? endRaw : duration
  form.rangeStart = Math.max(0, Math.min(start, duration))
  form.rangeEnd = Math.max(form.rangeStart, Math.min(end, duration))
}

const onAudioRangeChange = (val) => {
  if (!audioVideoRef.value || !Array.isArray(val) || !val.length) return
  audioVideoRef.value.currentTime = val[0] || 0
}

watch(
  () => form.start,
  (value) => {
    const duration = form.duration || 0
    let start = parseTimeToSeconds(value)
    if (duration && start > duration) start = duration
    form.rangeStart = start
  }
)

watch(
  () => form.end,
  (value) => {
    const duration = form.duration || 0
    if (!value) {
      form.rangeEnd = duration
      return
    }
    let end = parseTimeToSeconds(value)
    if (duration) {
      if (end < form.rangeStart) end = form.rangeStart
      if (end > duration) end = duration
    }
    form.rangeEnd = end
  }
)

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const loadVideoPreview = async () => {
  if (!ensurePyReady()) return
  const file = form.file
  if (!file) return
  const path = file.path || file.filename
  if (!path) return
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('video_preview', {
      filePath: path
    })
    if (ok && res.preview) {
      form.previewUrl = res.preview
    } else {
      form.previewUrl = ''
      if (message) {
        ElMessage.error(message)
      }
    }
  } catch (error) {
    form.previewUrl = ''
    ElMessage.error(error?.message || '视频预览失败')
  }
}

const selectVideo = async () => {
  if (!ensurePyReady()) return
  const result = await callApiRaw('system_pyCreateFileDialog', videoFilter)
  if (result?.length) {
    form.file = result[0]
    form.previewUrl = ''
    form.duration = 0
    form.rangeStart = 0
    form.rangeEnd = 0
    form.start = '00:00:00'
    form.end = ''
    await loadVideoPreview()
  }
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) {
    form.outputDir = dir
  }
}

const openFile = (file) => {
  if (!ensurePyReady() || !file) return
  callApiRaw('system_pyOpenFile', file)
}

const runAudio = async () => {
  if (!ensurePyReady()) return
  if (!form.file) {
    ElMessage.warning('请先选择视频文件')
    return
  }
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('video_extract_audio', {
      filePath: form.file.path,
      audioFormat: form.audioFormat,
      quality: form.quality,
      start: form.start,
      end: form.end,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.file || ''
      ElMessage.success(message || '提取完成')
    } else {
      ElMessage.error(message || '提取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '提取失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>视频转音频</h4>
      <p>输出 MP3 / WAV / AAC / FLAC，支持质量预设与时间截取</p>
    </header>
    <div v-if="form.file" class="video-preview-block">
      <video ref="audioVideoRef" class="video-preview" :src="form.previewUrl" controls @loadedmetadata="onAudioLoadedMetadata" />
      <el-slider v-if="form.duration" v-model="audioRange" :min="0" :max="form.duration" :step="1" range class="video-range-slider" @change="onAudioRangeChange" />
      <div v-if="form.duration" class="video-range-meta">
        <span>开始：{{ form.start || '00:00:00' }}</span>
        <span>结束：{{ form.end || '视频末尾' }}</span>
        <span>总长：{{ secondsToTime(form.duration) }}</span>
      </div>
    </div>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源视频">
        <div class="field-row">
          <el-input :model-value="form.file?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectVideo">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="音频格式">
        <el-select v-model="form.audioFormat" style="width: 200px">
          <el-option label="MP3" value="mp3" />
          <el-option label="WAV" value="wav" />
          <el-option label="AAC" value="aac" />
          <el-option label="FLAC" value="flac" />
        </el-select>
      </el-form-item>
      <el-form-item label="质量">
        <el-radio-group v-model="form.quality">
          <el-radio-button label="high">高质量</el-radio-button>
          <el-radio-button label="medium">均衡</el-radio-button>
          <el-radio-button label="low">小体积</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="开始时间">
        <el-input v-model="form.start" placeholder="00:00:00" />
      </el-form-item>
      <el-form-item label="结束时间">
        <el-input v-model="form.end" placeholder="可选，00:00:00" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runAudio">提取音频</el-button>
      </el-form-item>
    </el-form>
    <VideoInspection :file="form.file" />
    <el-alert v-if="form.result" type="success" :closable="false" show-icon>
      <template #title>
        已输出：<a class="link" @click.prevent="openFile(form.result)">{{ form.result }}</a>
      </template>
    </el-alert>
  </section>
</template>

<style scoped>
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
