<template>
  <section class="panel">
    <header>
      <h4>按固定页数拆分</h4>
      <p>每 N 页拆成一个文件，按章节批量导出</p>
    </header>
    <el-form :model="form" label-width="110px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="每个文件页数">
        <el-input-number v-model="form.pagesPerFile" :min="1" :max="50" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空则与源文件同级" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runSplit"> 开始拆分 </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.result.length" class="result-block">
      <p class="result-title">拆分结果</p>
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

const form = useDraft('pdf/parts/SplitPanel/form', {
  file: null,
  outputDir: '',
  pagesPerFile: 1,
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

const runSplit = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_split', {
    filePath: form.file.path,
    outputDir: form.outputDir,
    pagesPerFile: form.pagesPerFile
  })
  if (res) {
    form.result = res.files || []
  }
}
</script>
