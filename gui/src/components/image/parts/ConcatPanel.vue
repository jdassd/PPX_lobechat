<script setup>
import { mergeFileQueue, useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import FileSelector from '@/components/shared/FileSelector.vue'
import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const props = defineProps({ supportedFormats: { type: Object, required: true } })
const loading = ref(false)
const form = useDraft('image/parts/ConcatPanel/form', { files: [], direction: 'horizontal', columns: 2, spacing: 0, align: 'center', background: '#ffffff', outputFormat: 'png', quality: 90, outputName: '', outputDir: '', result: '' })
const ready = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const selectFiles = async () => {
  if (!ready()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (files?.length) form.files = mergeFileQueue(form.files, files)
}
const selectDir = async () => {
  if (!ready()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) form.outputDir = dir
}
const removeFile = (file) => (form.files = form.files.filter((item) => item !== file))
const run = async () => {
  if (!ready() || form.files.length < 2) {
    if (form.files.length < 2) ElMessage.warning('请至少选择两张图片')
    return
  }
  loading.value = true
  try {
    const result = await callApi('image_concat', { ...form, files: form.files.map((item) => item?.path || item), result: undefined })
    if (!result.ok) return ElMessage.error(result.message || '拼接失败')
    form.result = result.data.file || ''
    form.outputDir = result.data.outputDir || form.outputDir
    ElMessage.success(result.message || '图片拼接完成')
  } finally {
    loading.value = false
  }
}
const openPath = (path) => path && callApiRaw('system_pyOpenFile', path)
</script>

<template>
  <section class="panel">
    <header>
      <h4>图片拼接</h4>
      <p>按横向、纵向或网格布局生成一张长图</p>
    </header>
    <FileSelector label="图片列表" v-model:files="form.files" removable @select="selectFiles" @remove="removeFile" />
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="布局"
        ><el-radio-group v-model="form.direction"><el-radio-button label="horizontal">横向</el-radio-button><el-radio-button label="vertical">纵向</el-radio-button><el-radio-button label="grid">网格</el-radio-button></el-radio-group></el-form-item
      >
      <el-form-item v-if="form.direction === 'grid'" label="网格列数"><el-input-number v-model="form.columns" :min="1" :max="12" /></el-form-item>
      <el-form-item label="间距"><el-input-number v-model="form.spacing" :min="0" :max="300" /></el-form-item>
      <el-form-item label="对齐"
        ><el-select v-model="form.align" style="width: 220px"><el-option label="居中" value="center" /><el-option label="起始" value="start" /><el-option label="末端" value="end" /></el-select
      ></el-form-item>
      <el-form-item label="背景色"><el-color-picker v-model="form.background" /></el-form-item>
      <el-form-item label="输出格式"
        ><el-select v-model="form.outputFormat" style="width: 220px"><el-option v-for="item in supportedFormats.raster" :key="item.value" :label="item.label" :value="item.value" /></el-select
      ></el-form-item>
      <el-form-item label="输出名称"><el-input v-model="form.outputName" placeholder="可选" /></el-form-item>
      <el-form-item label="输出目录"
        ><div class="field-row"><el-input v-model="form.outputDir" readonly placeholder="自动创建" /><el-button @click="selectDir">选择</el-button></div></el-form-item
      >
      <el-form-item><el-button type="primary" :loading="loading" @click="run">生成拼接图</el-button></el-form-item>
    </el-form>
    <el-alert v-if="form.result" type="success" :closable="false" show-icon
      ><template #title
        >已输出：<a class="link" @click.prevent="openPath(form.result)">{{ form.result }}</a></template
      ></el-alert
    >
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
.link {
  color: var(--accent);
  cursor: pointer;
}
</style>
