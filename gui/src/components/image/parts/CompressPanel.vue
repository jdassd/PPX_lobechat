<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

import FileSelector from '../../shared/FileSelector.vue'
import ResultTable from '../../shared/ResultTable.vue'

const props = defineProps({
  supportedFormats: {
    type: Object,
    required: true
  }
})

const loading = ref(false)

const form = reactive({
  files: [],
  mode: 'quality',
  quality: 80,
  targetSizeKB: 512,
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

const selectImages = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (files?.length) {
    form.files = files
  }
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) {
    form.outputDir = dir
  }
}

const removeFile = (file) => {
  form.files = form.files.filter((item) => item !== file)
}

const pickPaths = (files = []) => files.map((item) => item?.path || item)

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const openDir = () => {
  const dir = form.outputDir || form.generatedDir
  if (dir) {
    openPath(dir)
    return
  }
  const fallback = form.result?.[0]
  if (fallback) {
    openPath(fallback)
  }
}

const runCompress = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const payload = {
      files: pickPaths(form.files),
      mode: form.mode,
      quality: form.quality,
      targetSizeKB: form.targetSizeKB,
      outputDir: form.outputDir
    }
    const { ok, data: res, message } = await pyCall('image_batch_compress', payload)
    if (ok) {
      form.result = res.items || []
      form.generatedDir = res.outputDir || form.outputDir
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
      <h4>体积压缩</h4>
      <p>按质量或目标体积压缩，文件更小、清晰度可控</p>
    </header>
    <FileSelector
      label="图片列表"
      :files="form.files"
      :removable="true"
      @select="selectImages"
      @remove="removeFile"
    />
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="压缩模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button label="quality">按质量</el-radio-button>
          <el-radio-button label="size">目标体积</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.mode === 'quality'" label="质量">
        <el-slider v-model="form.quality" :min="40" :max="95" show-input />
      </el-form-item>
      <el-form-item v-else label="目标大小 (KB)">
        <el-input-number v-model="form.targetSizeKB" :min="32" :max="8192" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runCompress">开始压缩</el-button>
      </el-form-item>
    </el-form>
    <ResultTable
      v-if="form.result.length"
      title="压缩结果"
      :items="form.result"
      :columns="[
        { label: '原文件', prop: 'source' },
        { label: '输出文件', prop: 'output' },
        { label: '原大小', prop: 'originalSize', width: 120 },
        { label: '新大小', prop: 'compressedSize', width: 120 }
      ]"
    >
      <template #actions>
        <el-button text type="primary" @click="openDir">打开目录</el-button>
      </template>
    </ResultTable>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
</style>
