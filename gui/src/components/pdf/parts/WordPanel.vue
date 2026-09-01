<template>
  <section class="panel">
    <header>
      <h4>转换为可编辑 Word 文档</h4>
      <p>按页提取文本并生成 .docx，可在 Word 中继续编辑</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="文本模式">
        <el-radio-group v-model="form.textMode">
          <el-radio-button label="plain">纯文本</el-radio-button>
          <el-radio-button label="markdown">Markdown</el-radio-button>
          <el-radio-button label="html">HTML</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="保存生成的 .docx" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runPdfToWord">
          转换为 Word
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-tag type="success" effect="plain" @click="openPath(form.output)">
        {{ form.output }}
      </el-tag>
    </div>
  </section>
</template>

<script setup>
import { inject, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickPdf, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const form = reactive({
  file: null,
  textMode: 'plain',
  outputDir: '',
  output: ''
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

const runPdfToWord = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_to_word', {
    filePath: form.file.path,
    textMode: form.textMode,
    outputDir: form.outputDir
  })
  if (res) {
    form.output = res.output || ''
    if (res.outputDir) {
      form.outputDir = res.outputDir
    }
  }
}
</script>
