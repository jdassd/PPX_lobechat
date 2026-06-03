<template>
  <section class="panel">
    <header>
      <h4>导出 PDF 文本内容</h4>
      <p>支持纯文本、Markdown、HTML、Blocks 等模式</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button label="plain">纯文本</el-radio-button>
          <el-radio-button label="markdown">Markdown</el-radio-button>
          <el-radio-button label="html">HTML</el-radio-button>
          <el-radio-button label="blocks">Blocks</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="页码区间">
        <div class="field-row">
          <el-input-number v-model="form.startPage" :min="1" />
          <span class="range-sep">至</span>
          <el-input-number v-model="form.endPage" :min="1" />
        </div>
      </el-form-item>
      <el-form-item label="自定义页码">
        <el-input
          v-model="form.pageSpec"
          placeholder="可选，例如：1-3,5"
        />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="保存提取文本" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.saveFile">保存为 .txt</el-checkbox>
      </el-form-item>
      <el-form-item>
      <el-button type="primary" :loading="shared.loading" @click="runExtractText">开始提取</el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.preview" class="result-block">
      <p class="result-title">文本预览</p>
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

const { callApi, pickPdf, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const form = reactive({
  file: null,
  mode: 'plain',
  startPage: 1,
  endPage: 1,
  pageSpec: '',
  outputDir: '',
  saveFile: false,
  preview: '',
  segments: []
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

const runExtractText = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_extract_text', {
    filePath: form.file.path,
    pageSpec: form.pageSpec,
    startPage: form.startPage,
    endPage: form.endPage,
    textMode: form.mode,
    saveFile: form.saveFile,
    outputDir: form.outputDir
  })
  if (res) {
    form.preview = res.preview || ''
    form.segments = res.segments || []
    if (res.output) {
      form.outputDir = res.output.split(/[\\/]/).slice(0, -1).join('/') || form.outputDir
    }
  }
}
</script>

<style scoped>
.range-sep {
  color: var(--ppx-text-muted);
}
</style>
