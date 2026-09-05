<template>
  <section class="panel">
    <header>
      <h4>导出 PDF 内嵌图片</h4>
      <p>可指定页码范围与输出格式，自动保存到目录</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="页码区间">
        <div class="field-row">
          <el-input-number v-model="form.startPage" :min="1" />
          <span class="range-sep">至</span>
          <el-input-number v-model="form.endPage" :min="1" />
        </div>
      </el-form-item>
      <el-form-item label="自定义页码">
        <el-input v-model="form.pageSpec" placeholder="可选：1-3,5" />
      </el-form-item>
      <el-form-item label="图片格式">
        <el-select v-model="form.format" style="width: 160px">
          <el-option label="PNG" value="png" />
          <el-option label="JPG" value="jpg" />
        </el-select>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runExtractImages"> 开始提取 </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.result.length" class="result-block">
      <p class="result-title">输出图片（部分）</p>
      <el-scrollbar max-height="160px">
        <div class="result-list">
          <el-tag v-for="file in form.result" :key="file" type="info" effect="plain" @click="openPath(file)">
            {{ file }}
          </el-tag>
        </div>
      </el-scrollbar>
    </div>
  </section>
</template>

<script setup>
import { useDraft } from '../../../utils/workspace'
import { inject } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickPdf, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const form = useDraft('pdf/parts/ExtractImagesPanel/form', {
  file: null,
  startPage: 1,
  endPage: 1,
  pageSpec: '',
  format: 'png',
  outputDir: '',
  result: []
})

const selectPdf = async () => {
  const result = await pickPdf()
  if (!result.length) return
  form.file = result[0]
}

const selectDir = async () => {
  const dir = await pickDir(form.outputDir || '')
  if (dir) {
    form.outputDir = dir
  }
}

const runExtractImages = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_extract_images', {
    filePath: form.file.path,
    pageSpec: form.pageSpec,
    startPage: form.startPage,
    endPage: form.endPage,
    format: form.format,
    outputDir: form.outputDir
  })
  if (res) {
    form.result = res.files || []
    form.outputDir = res.outputDir || form.outputDir
  }
}
</script>

<style scoped>
.range-sep {
  color: var(--ppx-text-muted);
}
</style>
