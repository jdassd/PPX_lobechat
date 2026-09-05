<script setup>
import { mergeFileQueue, useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import FileSelector from '@/components/shared/FileSelector.vue'
import ResultTable from '@/components/shared/ResultTable.vue'
import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const props = defineProps({ supportedFormats: { type: Object, required: true } })
const loading = ref(false)
const form = useDraft('image/parts/BatchRenamePanel/form', { files: [], mode: 'sequence', prefix: 'img_', suffix: '', digits: 3, startIndex: 1, pattern: '{name}_{index}', copyMode: false, outputDir: '', operations: [], skipped: [] })
const transactionId = ref('')
const undo = async () => {
  const response = await callApi('image_batch_rename_undo', { transactionId: transactionId.value })
  if (response.ok) {
    ElMessage.success(response.message)
    if (!response.data.skipped?.length) transactionId.value = ''
  } else ElMessage.error(response.message)
}
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
const execute = async (dryRun) => {
  if (!ready() || !form.files.length) {
    if (!form.files.length) ElMessage.warning('请先选择图片')
    return
  }
  loading.value = true
  try {
    const result = await callApi('image_batch_rename', {
      files: form.files.map((item) => item?.path || item),
      mode: form.mode,
      prefix: form.prefix,
      suffix: form.suffix,
      digits: form.digits,
      startIndex: form.startIndex,
      pattern: form.pattern,
      copyMode: form.copyMode,
      outputDir: form.outputDir,
      dryRun,
      conflictPolicy: 'skip'
    })
    if (!result.ok) return ElMessage.error(result.message || '重命名失败')
    form.operations = result.data.operations || []
    if (!dryRun) transactionId.value = result.data.transactionId || ''
    form.skipped = result.data.skipped || []
    form.outputDir = result.data.outputDir || form.outputDir
    ElMessage.success(result.message || (dryRun ? '预演完成' : '重命名完成'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>图片批量命名</h4>
      <p>先预演名称映射，确认后再安全执行；冲突文件会跳过</p>
    </header>
    <FileSelector label="图片列表" v-model:files="form.files" removable @select="selectFiles" @remove="removeFile" />
    <el-form :model="form" label-width="120px" class="form-block">
      <el-form-item label="命名方式"
        ><el-radio-group v-model="form.mode"><el-radio-button label="sequence">序号</el-radio-button><el-radio-button label="timestamp">时间戳</el-radio-button><el-radio-button label="custom">自定义</el-radio-button></el-radio-group></el-form-item
      >
      <el-form-item v-if="form.mode !== 'custom'" label="前缀/后缀"
        ><div class="field-row"><el-input v-model="form.prefix" placeholder="前缀" /><el-input v-model="form.suffix" placeholder="后缀" /></div
      ></el-form-item>
      <el-form-item v-else label="名称模板"><el-input v-model="form.pattern" placeholder="{name}_{index}" /></el-form-item>
      <el-form-item label="序号"
        ><div class="field-row"><el-input-number v-model="form.startIndex" :min="0" /><el-input-number v-model="form.digits" :min="1" :max="8" /></div
      ></el-form-item>
      <el-form-item label="输出方式"><el-switch v-model="form.copyMode" active-text="复制到新目录" inactive-text="原地改名" /></el-form-item>
      <el-form-item v-if="form.copyMode" label="输出目录"
        ><div class="field-row"><el-input v-model="form.outputDir" readonly placeholder="自动创建" /><el-button @click="selectDir">选择</el-button></div></el-form-item
      >
      <el-form-item><el-button :loading="loading" @click="execute(true)">预演</el-button><el-button type="primary" :loading="loading" @click="execute(false)">确认执行</el-button></el-form-item>
    </el-form>
    <el-button v-if="transactionId" @click="undo">撤销本次重命名</el-button>
    <ResultTable
      title="名称映射"
      :description="form.skipped.length ? `${form.skipped.length} 个冲突已跳过` : ''"
      :items="form.operations"
      :columns="[
        { prop: 'from', label: '原文件' },
        { prop: 'to', label: '新文件' }
      ]"
    />
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}
</style>
