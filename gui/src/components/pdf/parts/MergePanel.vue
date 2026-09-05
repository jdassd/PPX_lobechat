<template>
  <section class="panel">
    <header>
      <h4>将多个 PDF 合并</h4>
      <p>支持自定义顺序，生成单一归档文件</p>
    </header>
    <FileSelector v-model:files="form.files" label="待合并 PDF" button-text="添加 PDF" description="按队列顺序合并；页码留空表示全部页面" @select="selectPdf">
      <template #options="{ file }">
        <el-input v-model="file.pageSpec" size="small" placeholder="页码：1-3,5,8" :aria-label="file.filename + ' 页码'" style="width: 180px" />
      </template>
    </FileSelector>
    <el-form label-width="110px" class="mt24">
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="可选" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="例如：合并结果.pdf" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :disabled="!form.files.length" :loading="shared.loading" @click="runMerge"> 合并 PDF </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-scrollbar max-height="120px">
        <div class="result-list">
          <el-tag type="success" effect="light" @click="openPath(form.output)">
            {{ form.output }}
          </el-tag>
        </div>
      </el-scrollbar>
    </div>
  </section>
</template>

<script setup>
import { useDraft, mergeFileQueue } from '../../../utils/workspace'
import FileSelector from '../../shared/FileSelector.vue'
import { inject } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickPdf, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const form = useDraft('pdf/parts/MergePanel/form', {
  files: [],
  outputDir: '',
  outputName: '合并结果.pdf',
  output: ''
})

const selectPdf = async () => {
  const result = await pickPdf()
  if (!result.length) return
  form.files = mergeFileQueue(
    form.files,
    result.map((item) => ({ ...item, pageSpec: item.pageSpec || '' }))
  )
}

const selectDir = async () => {
  const dir = await pickDir(form.outputDir || '')
  if (dir) {
    form.outputDir = dir
  }
}

const runMerge = async () => {
  if (!form.files.length) {
    ElMessage.warning('请至少选择两个 PDF')
    return
  }
  const res = await callApi('pdf_merge', {
    files: form.files.map((item) => ({
      path: item.path,
      pageSpec: item.pageSpec || ''
    })),
    outputDir: form.outputDir,
    outputName: form.outputName
  })
  if (res) {
    form.output = res.output
  }
}
</script>

<style scoped>
.merge-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mt24 {
  margin-top: 24px;
}
</style>
