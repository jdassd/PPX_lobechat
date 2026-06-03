<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = reactive({
  file: null,
  mode: 'preset',
  bitrate: '1500k',
  targetSizeMB: 20,
  preset: 'balanced',
  ffPreset: 'medium',
  outputDir: '',
  result: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectVideo = async () => {
  if (!ensurePyReady()) return
  const result = await callApiRaw('system_pyCreateFileDialog', videoFilter)
  if (result?.length) {
    form.file = result[0]
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

const runCompress = async () => {
  if (!ensurePyReady()) return
  if (!form.file) {
    ElMessage.warning('请先选择视频文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('video_compress', {
      filePath: form.file.path,
      mode: form.mode,
      bitrate: form.bitrate,
      targetSizeMB: form.targetSizeMB,
      preset: form.preset,
      ffPreset: form.ffPreset,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.file || ''
      ElMessage.success(message || '压缩完成')
    } else {
      ElMessage.error(message || '压缩失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '压缩失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>压缩模式</h4>
      <p>按码率、目标大小或预设压缩</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源视频">
        <div class="field-row">
          <el-input :model-value="form.file?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectVideo">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button label="preset">预设</el-radio-button>
          <el-radio-button label="bitrate">码率</el-radio-button>
          <el-radio-button label="size">目标大小</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.mode === 'bitrate'" label="码率">
        <el-input v-model="form.bitrate" placeholder="例如 1500k" />
      </el-form-item>
      <el-form-item v-else-if="form.mode === 'size'" label="目标大小 (MB)">
        <el-input-number v-model="form.targetSizeMB" :min="5" :max="5000" />
      </el-form-item>
      <template v-else>
        <el-form-item label="预设">
          <el-select v-model="form.preset" style="width: 200px">
            <el-option label="高清优先" value="high" />
            <el-option label="均衡" value="balanced" />
            <el-option label="体积最小" value="small" />
          </el-select>
        </el-form-item>
        <el-form-item label="FFmpeg 预设">
          <el-select v-model="form.ffPreset" style="width: 200px">
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
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runCompress">开始压缩</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="form.result"
      type="success"
      :closable="false"
      show-icon
    >
      <template #title>
        已输出：<a class="link" @click.prevent="openFile(form.result)">{{ form.result }}</a>
      </template>
    </el-alert>
  </section>
</template>

<style scoped>
.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
