<script setup>
import VideoInspection from '../../shared/VideoInspection.vue'
import FileSelector from '../../shared/FileSelector.vue'
import { mergeFileQueue, useDraft } from '../../../utils/workspace'
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)
const inspection = ref(null)
const inspecting = ref(false)

const form = useDraft('video/parts/ConcatPanel/form', {
  files: [],
  reencode: false,
  targetFormat: 'mp4',
  preset: 'medium',
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

const selectConcatFiles = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', videoFilter)
  if (files?.length) {
    form.files = mergeFileQueue(form.files, files)
  }
}

watch(
  () => form.files.map((file) => file.path || file).join('\n'),
  () => {
    inspection.value = null
  }
)
const inspectConcat = async () => {
  inspecting.value = true
  try {
    const response = await pyCall('video_concat_preview', { files: form.files.map((file) => file.path || file) })
    if (!response.ok) throw new Error(response.message)
    inspection.value = response.data
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    inspecting.value = false
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

const runConcat = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请至少选择两个视频')
    return
  }
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('video_concat', {
      files: form.files.map((file) => file.path || file),
      reencode: form.reencode,
      targetFormat: form.targetFormat,
      preset: form.preset,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.file || ''
      ElMessage.success(message || '合成完成')
    } else {
      ElMessage.error(message || '合成失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '合成失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>多视频拼接</h4>
      <p>支持直接无损合并或重新编码输出，保持自定义排序</p>
    </header>
    <FileSelector v-model:files="form.files" label="待拼接视频" description="按列表顺序拼接，可拖动调整顺序" @select="selectConcatFiles" />
    <el-button :loading="inspecting" :disabled="form.files.length < 2" @click="inspectConcat">检查拼接兼容性</el-button>
    <el-alert v-if="inspection" :type="inspection.compatible ? 'success' : 'warning'" :title="inspection.msg" :closable="false" />
    <el-form :model="form" label-width="140px" class="form-block">
      <el-form-item label="输出格式">
        <div class="field-row">
          <el-select v-model="form.targetFormat" style="width: 160px">
            <el-option label="MP4" value="mp4" />
            <el-option label="MOV" value="mov" />
            <el-option label="MKV" value="mkv" />
          </el-select>
          <el-switch v-model="form.reencode" active-text="重新编码（兼容不同参数）" />
        </div>
      </el-form-item>
      <el-form-item v-if="form.reencode" label="编码预设">
        <el-select v-model="form.preset" style="width: 200px">
          <el-option label="更好画质" value="slow" />
          <el-option label="平衡" value="medium" />
          <el-option label="更快" value="fast" />
        </el-select>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空自动创建" readonly />
          <el-button @click="selectDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" :disabled="form.files.length < 2" @click="runConcat"> 开始合成 </el-button>
      </el-form-item>
    </el-form>
    <VideoInspection :file="form.files[0]" />
    <el-alert v-if="form.result" type="success" :closable="false" show-icon>
      <template #title>
        已输出：<a class="link" @click.prevent="openFile(form.result)">{{ form.result }}</a>
      </template>
    </el-alert>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
