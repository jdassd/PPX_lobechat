<script setup>
import { computed, reactive, ref } from 'vue'
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
  operation: 'rotate90',
  angle: 0,
  flipHorizontal: false,
  flipVertical: false,
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

const rotatePreviewUrl = computed(() => {
  const first = form.files[0]
  if (!first) return ''
  const path = first.path || first
  if (!path) return ''
  return toFileUrl(path)
})

const rotatePreviewStyle = computed(() => {
  const transforms = []
  const op = form.operation
  if (op === 'rotate90') {
    transforms.push('rotate(90deg)')
  } else if (op === 'rotate180') {
    transforms.push('rotate(180deg)')
  } else if (op === 'rotate270') {
    transforms.push('rotate(270deg)')
  } else if (op === 'mirror') {
    transforms.push('scaleX(-1)')
  } else if (op === 'flip') {
    transforms.push('scaleY(-1)')
  } else if (op === 'custom') {
    if (form.angle) {
      transforms.push(`rotate(${form.angle}deg)`)
    }
    if (form.flipHorizontal) {
      transforms.push('scaleX(-1)')
    }
    if (form.flipVertical) {
      transforms.push('scaleY(-1)')
    }
  }
  if (!transforms.length) return {}
  return {
    transform: transforms.join(' '),
    transformOrigin: '50% 50%',
    transition: 'transform 0.2s ease-out'
  }
})

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

const runRotate = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const payload = {
      files: pickPaths(form.files),
      operation: form.operation,
      angle: form.angle,
      flipHorizontal: form.flipHorizontal,
      flipVertical: form.flipVertical,
      outputDir: form.outputDir
    }
    const { ok, data: res, message } = await pyCall('image_rotate_flip', payload)
    if (ok) {
      form.result = res.files || []
      form.generatedDir = res.outputDir || form.outputDir
      ElMessage.success(message || '处理完成')
    } else {
      ElMessage.error(message || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>方向调整</h4>
      <p>旋转 90/180/270°，或镜像 / 垂直翻转</p>
    </header>
    <FileSelector
      label="图片列表"
      :files="form.files"
      :removable="true"
      @select="selectImages"
      @remove="removeFile"
    />
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="操作">
        <el-select v-model="form.operation" style="width: 240px">
          <el-option label="旋转 90°" value="rotate90" />
          <el-option label="旋转 180°" value="rotate180" />
          <el-option label="旋转 270°" value="rotate270" />
          <el-option label="水平镜像" value="mirror" />
          <el-option label="垂直翻转" value="flip" />
          <el-option label="自定义角度 / 翻转" value="custom" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.operation === 'custom'" label="旋转角度">
        <el-slider v-model="form.angle" :min="-180" :max="180" show-input />
      </el-form-item>
      <el-form-item v-if="form.operation === 'custom'" label="翻转">
        <el-checkbox v-model="form.flipHorizontal">水平</el-checkbox>
        <el-checkbox v-model="form.flipVertical">垂直</el-checkbox>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runRotate">开始处理</el-button>
      </el-form-item>
    </el-form>
    <ResultTable
      v-if="form.result.length"
      title="处理结果"
      :items="form.result.map((path) => ({ path }))"
      :columns="[{ label: '文件路径', prop: 'path' }]"
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
