<template>
  <section class="panel">
    <header>
      <h4>为 PDF 自动生成目录</h4>
      <p>根据每页标题自动推断目录，并生成一份带目录的 PDF</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="保存带目录的 PDF" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="如：带目录版.pdf" />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.saveText">同时导出目录为 .txt</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runGenerateToc">
          生成目录
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-tag type="success" effect="plain" @click="openPath(form.output)">
        {{ form.output }}
      </el-tag>
      <p v-if="form.textOutput" class="result-title" style="margin-top: 8px">
        目录文本已另存为：
        <a class="link" @click.prevent="openPath(form.textOutput)">{{ form.textOutput }}</a>
      </p>
    </div>
    <div v-if="form.preview" class="result-block">
      <p class="result-title">目录预览</p>
      <el-input
        v-model="form.preview"
        type="textarea"
        :rows="8"
        readonly
      />
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
  outputDir: '',
  outputName: '带目录版.pdf',
  saveText: false,
  preview: '',
  output: '',
  textOutput: ''
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

const runGenerateToc = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_generate_toc', {
    filePath: form.file.path,
    outputDir: form.outputDir,
    outputName: form.outputName,
    saveText: form.saveText
  })
  if (res) {
    form.output = res.output || ''
    form.preview = res.tocText || ''
    form.textOutput = res.textOutput || ''
    if (res.output) {
      form.outputDir = res.output.split(/[\\/]/).slice(0, -1).join('/') || form.outputDir
    }
  }
}
</script>
