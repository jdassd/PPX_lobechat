<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = reactive({
  file: null,
  targetFormat: 'mp4',
  qualityPreset: 'medium',
  preset: 'medium',
  videoCodec: 'libx264',
  audioCodec: 'aac',
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

const runConvert = async () => {
  if (!ensurePyReady()) return
  if (!form.file) {
    ElMessage.warning('请先选择视频文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('video_format_convert', {
      filePath: form.file.path,
      targetFormat: form.targetFormat,
      qualityPreset: form.qualityPreset,
      preset: form.preset,
      videoCodec: form.videoCodec,
      audioCodec: form.audioCodec,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.file || ''
      ElMessage.success(message || '转换完成')
    } else {
      ElMessage.error(message || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>转换目标格式</h4>
      <p>选择常见容器与编码预设</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源视频">
        <div class="field-row">
          <el-input :model-value="form.file?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectVideo">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="目标格式">
        <el-select v-model="form.targetFormat" style="width: 200px">
          <el-option label="MP4" value="mp4" />
          <el-option label="MOV" value="mov" />
          <el-option label="AVI" value="avi" />
          <el-option label="MKV" value="mkv" />
          <el-option label="WebM" value="webm" />
        </el-select>
      </el-form-item>
      <el-form-item label="质量预设">
        <el-radio-group v-model="form.qualityPreset">
          <el-radio-button label="original">原画</el-radio-button>
          <el-radio-button label="high">高清</el-radio-button>
          <el-radio-button label="medium">均衡</el-radio-button>
          <el-radio-button label="low">体积优先</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runConvert">开始转换</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="form.result"
      type="success"
      :closable="false"
      show-icon
    >
      <template #title>
        已生成：<a class="link" @click.prevent="openFile(form.result)">{{ form.result }}</a>
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
