<template>
  <section class="panel">
    <header>
      <h4>按页码摘取页面</h4>
      <p>按页码区间或列表摘取页面，生成一份新 PDF</p>
    </header>
    <el-form :model="form" label-width="110px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="form.mode">
          <el-radio-button label="range">区间</el-radio-button>
          <el-radio-button label="custom">指定页码</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.mode === 'range'" label="起止页">
        <div class="field-row">
          <el-input-number v-model="form.startPage" :min="1" />
          <span class="range-sep">至</span>
          <el-input-number v-model="form.endPage" :min="1" />
        </div>
      </el-form-item>
      <el-form-item v-else label="页码列表">
        <el-input v-model="form.pageSpec" placeholder="示例：1-3,5,8；支持用分号或换行分隔多个区间" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item v-if="form.mode === 'custom'">
        <el-checkbox v-model="form.multi"> 按多个区间分别导出多个 PDF 文件 </el-checkbox>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="可选" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="例如：摘录.pdf" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runCut"> 生成新 PDF </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output || form.outputs.length" class="result-block">
      <p class="result-title">生成文件</p>
      <el-scrollbar max-height="120px">
        <div class="result-list">
          <el-tag v-for="file in form.outputs.length ? form.outputs : [form.output]" :key="file" type="success" effect="light" @click="openPath(file)">
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

const form = useDraft('pdf/parts/CutPanel/form', {
  file: null,
  outputDir: '',
  outputName: '摘录.pdf',
  mode: 'range',
  startPage: 1,
  endPage: 1,
  pageSpec: '',
  multi: false,
  output: '',
  outputs: []
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

const runCut = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  if (form.mode === 'custom' && !form.pageSpec.trim()) {
    ElMessage.warning('请输入页码集合')
    return
  }
  const payload = {
    filePath: form.file.path,
    outputDir: form.outputDir,
    outputName: form.outputName,
    mode: form.mode,
    startPage: form.startPage,
    endPage: form.endPage,
    pageSpec: form.pageSpec
  }
  const useMulti = form.mode === 'custom' && form.multi && form.pageSpec.trim().length > 0
  const apiName = useMulti ? 'pdf_multi_cut' : 'pdf_cut'
  const res = await callApi(apiName, payload)
  if (res) {
    if (res.files && Array.isArray(res.files) && res.files.length) {
      form.outputs = res.files
      form.output = res.files[0]
    } else {
      form.outputs = []
      form.output = res.output
    }
  }
}
</script>

<style scoped>
.range-sep {
  color: var(--ppx-text-muted);
}
</style>
