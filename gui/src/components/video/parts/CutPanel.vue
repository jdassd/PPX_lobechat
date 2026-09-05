<script setup>
import VideoInspection from '../../shared/VideoInspection.vue'
import { useDraft } from '../../../utils/workspace'
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = useDraft('video/parts/CutPanel/form', {
  file: null,
  start: '00:00:00',
  end: '',
  outputDir: '',
  result: '',
  duration: 0,
  rangeStart: 0,
  rangeEnd: 0,
  previewStart: 0,
  segment: false,
  previewUrl: ''
})

const cutVideoRef = ref(null)

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

const cutRange = computed({
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

const onCutLoadedMetadata = () => {
  const video = cutVideoRef.value
  if (!video) return
  const duration = form.duration || (Number.isFinite(video.duration) ? video.duration : 0)
  form.duration = duration
  const start = parseTimeToSeconds(form.start)
  const endRaw = parseTimeToSeconds(form.end)
  const end = endRaw && endRaw > 0 ? endRaw : duration
  form.rangeStart = Math.max(0, Math.min(start, duration))
  form.rangeEnd = Math.max(form.rangeStart, Math.min(end, duration))
}

const onCutRangeChange = (val) => {
  if (!cutVideoRef.value || !Array.isArray(val) || !val.length) return
  if (!form.segment) cutVideoRef.value.currentTime = val[0] || 0
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
      filePath: path,
      start: form.start,
      duration: 15
    })
    if (ok && res.preview) {
      form.previewUrl = res.preview
      form.duration = res.duration || 0
      form.previewStart = res.previewStart || 0
      form.segment = !!res.segment
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

const runCut = async () => {
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
    } = await pyCall('video_cut', {
      filePath: form.file.path,
      start: form.start,
      end: form.end,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.file || ''
      ElMessage.success(message || '截取完成')
    } else {
      ElMessage.error(message || '截取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '截取失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>截取片段</h4>
      <p>按起止时间精确截取，重新编码后保存为副本</p>
    </header>
    <div v-if="form.file" class="video-preview-block">
      <p v-if="form.segment">当前预览从 {{ secondsToTime(form.previewStart) }} 起的最多 15 秒；滑块设置使用完整视频时长。</p>
      <el-button size="small" @click="loadVideoPreview">预览所选起点后的片段</el-button>
      <video ref="cutVideoRef" class="video-preview" :src="form.previewUrl" controls @loadedmetadata="onCutLoadedMetadata" />
      <el-slider v-if="form.duration" v-model="cutRange" :min="0" :max="form.duration" :step="1" range class="video-range-slider" @change="onCutRangeChange" />
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
        <el-button type="primary" :loading="loading" @click="runCut">截取</el-button>
      </el-form-item>
    </el-form>
    <VideoInspection :file="form.file" />
    <el-alert v-if="form.result" type="success" :closable="false" show-icon>
      <template #title>
        输出文件：<a class="link" @click.prevent="openFile(form.result)">{{ form.result }}</a>
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
