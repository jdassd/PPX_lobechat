<template>
  <section class="panel">
    <header>
      <h4>按需压缩 PDF</h4>
    </header>
    <el-form :model="form" label-width="110px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="压缩率">
        <div class="field-row field-wrap">
          <el-radio-group v-model="form.mode">
            <el-radio-button label="low">低（高清）</el-radio-button>
            <el-radio-button label="medium">中（均衡）</el-radio-button>
            <el-radio-button label="high">高（小体积）</el-radio-button>
            <el-radio-button label="custom">自定义</el-radio-button>
          </el-radio-group>
          <el-tag type="info" effect="plain">当前 DPI：{{ compressCurrentDpi }} DPI</el-tag>
        </div>
      </el-form-item>
      <el-form-item v-if="form.mode === 'custom'" label="自定义 DPI">
        <el-input-number v-model="form.customDpi" :min="72" :max="400" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="可选" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="例如：压缩结果.pdf" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runCompress"> 开始压缩 </el-button>
      </el-form-item>
    </el-form>
    <p class="dpi-hint">推荐：低≈280 DPI（高清打印）、中≈200 DPI（通用传输）、高≈130 DPI（快速分享）。DPI 越低文件越小，越高越清晰。</p>
    <div v-if="form.output" class="result-block">
      <p class="result-title">压缩后的 PDF</p>
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
import { useDraft } from '../../../utils/workspace'
import { computed, inject } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickPdf, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const compressModeDpiMap = {
  low: 280,
  medium: 200,
  high: 130
}

const form = useDraft('pdf/parts/CompressPanel/form', {
  file: null,
  mode: 'medium',
  customDpi: 200,
  outputDir: '',
  outputName: '压缩结果.pdf',
  output: ''
})

const compressCurrentDpi = computed(() => {
  if (form.mode === 'custom') {
    return form.customDpi || 200
  }
  return compressModeDpiMap[form.mode] || compressModeDpiMap.medium
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

const runCompress = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  if (form.mode === 'custom') {
    const dpi = Number(form.customDpi)
    if (!dpi) {
      ElMessage.warning('请输入自定义 DPI')
      return
    }
    if (dpi < 72 || dpi > 400) {
      ElMessage.warning('自定义 DPI 需在 72 - 400 之间')
      return
    }
  }
  const res = await callApi('pdf_compress', {
    filePath: form.file.path,
    mode: form.mode,
    customDpi: form.customDpi,
    outputDir: form.outputDir,
    outputName: form.outputName
  })
  if (res) {
    form.output = res.output
  }
}
</script>
