<script setup>
import { reactive, ref, watch } from 'vue'
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
  targetFormat: 'png',
  quality: 90,
  keepName: true,
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

const runFormatConvert = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const payload = {
      files: pickPaths(form.files),
      targetFormat: form.targetFormat,
      quality: form.quality,
      keepName: form.keepName,
      outputDir: form.outputDir
    }
    const { ok, data: res, message } = await pyCall('image_format_convert', payload)
    if (ok) {
      form.result = res.files || []
      form.generatedDir = res.outputDir || form.outputDir
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

// 当支持格式列表更新后，确保已选目标格式仍然合法
watch(
  () => props.supportedFormats.convert,
  (options) => {
    if (!options?.length) return
    const allowed = new Set(options.map((item) => item.value))
    if (!allowed.has(form.targetFormat)) {
      form.targetFormat = options[0].value
    }
  },
  { immediate: true }
)
</script>

<template>
  <section class="panel">
    <header>
      <h4>批量格式转换</h4>
      <p>常见图片格式互转，可用格式随当前环境自动适配</p>
    </header>
    <FileSelector
      label="源文件"
      :files="form.files"
      :removable="true"
      @select="selectImages"
      @remove="removeFile"
    />
    <el-form :model="form" label-width="110px" class="form-block">
      <el-form-item label="目标格式">
        <el-select v-model="form.targetFormat" style="width: 200px">
          <el-option
            v-for="item in supportedFormats.convert"
            :key="`convert-format-${item.value}`"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="画质 / 质量">
        <el-slider v-model="form.quality" :min="40" :max="100" show-input />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.keepName">保留原文件名</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runFormatConvert">开始转换</el-button>
      </el-form-item>
    </el-form>
    <ResultTable
      v-if="form.result.length"
      title="转换输出"
      :items="form.result.map((path) => ({ path }))"
      :columns="[{ label: '文件路径', prop: 'path' }]"
    >
      <template #actions>
        <el-button text type="primary" @click="openDir">
          打开目录
        </el-button>
      </template>
    </ResultTable>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
</style>
