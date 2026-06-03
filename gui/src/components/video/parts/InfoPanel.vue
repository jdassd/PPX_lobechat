<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = reactive({
  file: null,
  data: null
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

const runInfo = async () => {
  if (!ensurePyReady()) return
  if (!form.file) {
    ElMessage.warning('请先选择视频文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('video_get_info', {
      filePath: form.file.path
    })
    if (ok) {
      form.data = res.info || null
      ElMessage.success(message || '信息已获取')
    } else {
      ElMessage.error(message || '获取失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '获取失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>快速查看参数</h4>
      <p>显示时长、分辨率、码率、编码器等关键指标</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="视频文件">
        <div class="field-row">
          <el-input :model-value="form.file?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectVideo">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runInfo">获取信息</el-button>
      </el-form-item>
    </el-form>
    <el-descriptions
      v-if="form.data"
      :column="3"
      border
      size="small"
      style="margin-top: 16px"
    >
      <el-descriptions-item label="时长 (s)">{{ form.data.duration }}</el-descriptions-item>
      <el-descriptions-item label="分辨率">{{ form.data.width }}×{{ form.data.height }}</el-descriptions-item>
      <el-descriptions-item label="帧率">{{ form.data.fps }}</el-descriptions-item>
      <el-descriptions-item label="视频编码">{{ form.data.videoCodec }}</el-descriptions-item>
      <el-descriptions-item label="音频编码">{{ form.data.audioCodec }}</el-descriptions-item>
      <el-descriptions-item label="码率 (bps)">{{ form.data.bitrate }}</el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<style scoped>
</style>
