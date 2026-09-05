<script setup>
import { mergeFileQueue, useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

import FileSelector from '../../shared/FileSelector.vue'

const props = defineProps({
  supportedFormats: {
    type: Object,
    required: true
  }
})

const loading = ref(false)

const form = useDraft('image/parts/PdfPanel/form', {
  files: [],
  pageSize: 'a4',
  customWidth: 2480,
  customHeight: 3508,
  perPage: 1,
  margin: 40,
  outputName: '',
  outputDir: '',
  generatedDir: '',
  result: ''
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
    form.files = mergeFileQueue(form.files, files)
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

const runImagePdf = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const payload = {
      files: pickPaths(form.files),
      pageSize: form.pageSize,
      customWidth: form.customWidth,
      customHeight: form.customHeight,
      perPage: form.perPage,
      margin: form.margin,
      outputName: form.outputName,
      outputDir: form.outputDir
    }
    const { ok, data: res, message } = await pyCall('image_to_pdf', payload)
    if (ok) {
      form.result = res.file || ''
      form.generatedDir = res.outputDir || form.outputDir
      ElMessage.success(message || 'PDF 已生成')
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
      <h4>合成 PDF</h4>
      <p>拖入多张图片，设置纸张与排版后输出 PDF</p>
    </header>
    <FileSelector label="图片列表" v-model:files="form.files" :removable="true" @select="selectImages" @remove="removeFile" />
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="页面尺寸">
        <el-select v-model="form.pageSize" style="width: 220px">
          <el-option label="A4" value="a4" />
          <el-option label="A5" value="a5" />
          <el-option label="Letter" value="letter" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      <div v-if="form.pageSize === 'custom'" class="field-row">
        <el-form-item label="宽 (px)">
          <el-input-number v-model="form.customWidth" :min="600" :max="6000" />
        </el-form-item>
        <el-form-item label="高 (px)">
          <el-input-number v-model="form.customHeight" :min="600" :max="6000" />
        </el-form-item>
      </div>
      <el-form-item label="每页布局">
        <el-radio-group v-model="form.perPage">
          <el-radio-button :label="1">1 / 页</el-radio-button>
          <el-radio-button :label="2">2 / 页</el-radio-button>
          <el-radio-button :label="4">4 / 页</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="边距 (px)">
        <el-input-number v-model="form.margin" :min="10" :max="300" />
      </el-form-item>
      <el-form-item label="输出名称">
        <el-input v-model="form.outputName" placeholder="可选，例如 merge.pdf" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runImagePdf">生成 PDF</el-button>
      </el-form-item>
    </el-form>
    <el-alert v-if="form.result" type="success" :closable="false" show-icon>
      <template #title>
        已输出：
        <a class="link" @click.prevent="openPath(form.result)">{{ form.result }}</a>
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
