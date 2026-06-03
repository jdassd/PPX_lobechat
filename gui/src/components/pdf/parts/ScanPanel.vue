<template>
  <section class="panel">
    <header>
      <h4>模拟扫描件效果</h4>
      <p>自动添加纸纹、微倾角和杂点，便于归档或走传统流程</p>
    </header>
    <el-form :model="form" label-width="110px">
      <el-form-item label="源 PDF">
        <div class="field-row">
          <el-button @click="selectPdf">选择 PDF</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="分辨率 (DPI)">
        <el-input-number v-model="form.dpi" :min="120" :max="400" />
      </el-form-item>
      <el-form-item label="图片格式">
        <el-select v-model="form.format" style="width: 160px">
          <el-option label="JPG" value="jpg" />
          <el-option label="PNG" value="png" />
        </el-select>
      </el-form-item>
      <el-form-item label="纸张纹理">
        <el-switch v-model="form.texture" />
      </el-form-item>
      <el-form-item label="轻微倾斜">
        <el-switch v-model="form.tilt" />
      </el-form-item>
      <el-form-item label="噪点强度">
        <el-slider v-model="form.noise" :min="0" :max="10" :step="0.5" show-input />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空则与源文件同级" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :loading="shared.loading"
          @click="runScanEffect"
        >
          生成扫描件
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.result.length" class="result-block">
      <p class="result-title">输出图片</p>
      <el-scrollbar max-height="160px">
        <div class="result-list">
          <el-tag
            v-for="file in form.result"
            :key="file"
            type="info"
            effect="plain"
            @click="openPath(file)"
          >
            {{ file }}
          </el-tag>
        </div>
      </el-scrollbar>
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
  dpi: 200,
  format: 'jpg',
  tilt: true,
  texture: true,
  noise: 6,
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

const runScanEffect = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_convert_to_scan', {
    filePath: form.file.path,
    outputDir: form.outputDir,
    dpi: form.dpi,
    format: form.format,
    tilt: form.tilt,
    texture: form.texture,
    noise: form.noise
  })
  if (res) {
    form.result = res.files || []
  }
}
</script>
