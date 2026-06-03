<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = reactive({
  file: null,
  mode: 'time',
  interval: 5,
  imageFormat: 'png',
  outputDir: '',
  generatedDir: '',
  result: []
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

const openFramesDir = () => {
  const dir = form.generatedDir || form.outputDir
  if (dir) {
    openFile(dir)
  }
}

const runFrames = async () => {
  if (!ensurePyReady()) return
  if (!form.file) {
    ElMessage.warning('请先选择视频文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('video_extract_frames', {
      filePath: form.file.path,
      mode: form.mode,
      interval: form.interval,
      imageFormat: form.imageFormat,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.files || []
      form.generatedDir = res.outputDir || form.outputDir
      ElMessage.success(message || '帧图已导出')
    } else {
      ElMessage.error(message || '导出失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '导出失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>按时间 / 帧提取图片</h4>
      <p>支持每 N 秒或每 N 帧保存，自动保存到目录</p>
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
          <el-radio-button label="time">每 N 秒</el-radio-button>
          <el-radio-button label="frame">每 N 帧</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item :label="form.mode === 'time' ? '间隔 (秒)' : '间隔 (帧)'">
        <el-input-number v-model="form.interval" :min="1" :max="3600" />
      </el-form-item>
      <el-form-item label="图片格式">
        <el-select v-model="form.imageFormat" style="width: 200px">
          <el-option label="PNG" value="png" />
          <el-option label="JPG" value="jpg" />
        </el-select>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runFrames">开始导出</el-button>
      </el-form-item>
    </el-form>
    <el-table
      v-if="form.result.length"
      :data="form.result"
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
      v-if="form.result.length"
      type="primary"
      link
      @click="openFramesDir"
    >
      打开输出目录
    </el-button>
  </section>
</template>

<style scoped>
.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
