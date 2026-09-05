<script setup>
import ImageEffectPreview from '../../shared/ImageEffectPreview.vue'
import { mergeFileQueue, useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import FileSelector from '@/components/shared/FileSelector.vue'
import ResultTable from '@/components/shared/ResultTable.vue'
import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const props = defineProps({ supportedFormats: { type: Object, required: true } })
const loading = ref(false)
const form = useDraft('image/parts/RotateFlipPanel/form', { files: [], operation: 'rotate90', angle: 0, flipHorizontal: false, flipVertical: false, outputDir: '', results: [] })

const ensureReady = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const selectFiles = async () => {
  if (!ensureReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (files?.length) form.files = mergeFileQueue(form.files, files)
}
const selectDir = async () => {
  if (!ensureReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) form.outputDir = dir
}
const removeFile = (file) => {
  form.files = form.files.filter((item) => item !== file)
}
const run = async () => {
  if (!ensureReady() || !form.files.length) {
    if (!form.files.length) ElMessage.warning('请先选择图片')
    return
  }
  loading.value = true
  try {
    const result = await callApi('image_rotate_flip', {
      files: form.files.map((item) => item?.path || item),
      operation: form.operation,
      angle: form.angle,
      flipHorizontal: form.flipHorizontal,
      flipVertical: form.flipVertical,
      outputDir: form.outputDir
    })
    if (!result.ok) {
      ElMessage.error(result.message || '处理失败')
      return
    }
    form.results = (result.data.files || []).map((path) => ({ path }))
    form.outputDir = result.data.outputDir || form.outputDir
    ElMessage.success(result.message || '处理完成')
  } finally {
    loading.value = false
  }
}
const openPath = (path) => path && callApiRaw('system_pyOpenFile', path)
</script>

<template>
  <section class="panel">
    <header>
      <h4>旋转与翻转</h4>
      <p>批量旋转、镜像或按自定义角度翻转图片</p>
    </header>
    <FileSelector label="待处理图片" v-model:files="form.files" removable @select="selectFiles" @remove="removeFile" />
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="处理方式">
        <el-select v-model="form.operation" style="width: 240px"> <el-option label="顺时针 90°" value="rotate90" /><el-option label="旋转 180°" value="rotate180" /><el-option label="旋转 270°" value="rotate270" /> <el-option label="水平镜像" value="mirror" /><el-option label="垂直翻转" value="flip" /><el-option label="自定义" value="custom" /> </el-select>
      </el-form-item>
      <template v-if="form.operation === 'custom'">
        <el-form-item label="角度"><el-input-number v-model="form.angle" :min="-360" :max="360" /></el-form-item>
        <el-form-item label="附加翻转"><el-checkbox v-model="form.flipHorizontal">水平</el-checkbox><el-checkbox v-model="form.flipVertical">垂直</el-checkbox></el-form-item>
      </template>
      <el-form-item label="输出目录"
        ><div class="field-row"><el-input v-model="form.outputDir" readonly placeholder="自动创建" /><el-button @click="selectDir">选择</el-button></div></el-form-item
      >
      <el-form-item><el-button type="primary" :loading="loading" @click="run">开始处理</el-button></el-form-item>
    </el-form>
    <ImageEffectPreview method="image_rotate_flip" :options="form" />
    <ResultTable title="输出结果" :items="form.results" :columns="[{ prop: 'path', label: '文件' }]">
      <template #actions><el-button v-if="form.outputDir" text type="primary" @click="openPath(form.outputDir)">打开目录</el-button></template>
    </ResultTable>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
</style>
