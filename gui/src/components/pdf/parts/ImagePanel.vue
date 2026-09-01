<template>
  <section class="panel">
    <header>
      <h4>输出每页高清图片</h4>
      <p>逐页导出为图片，方便二次排版或打印</p>
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
        <div class="field-row field-wrap">
          <el-radio-group v-model="form.dpiPreset">
            <el-radio-button label="ultra">超清</el-radio-button>
            <el-radio-button label="high">高清</el-radio-button>
            <el-radio-button label="standard">标清</el-radio-button>
            <el-radio-button label="custom">自定义</el-radio-button>
          </el-radio-group>
          <el-input-number
            v-model="form.dpi"
            :min="96"
            :max="600"
            :step="10"
            :disabled="form.dpiPreset !== 'custom'"
          />
        </div>
        <p class="dpi-hint">
          DPI 越高，导出图片越清晰，文件体积也会更大。推荐：超清 400 DPI，高清 300 DPI，标清 200 DPI。
        </p>
      </el-form-item>
      <el-form-item label="图片格式">
        <el-select v-model="form.format" style="width: 160px">
          <el-option label="PNG" value="png" />
          <el-option label="JPG" value="jpg" />
          <el-option label="GIF" value="gif" />
          <el-option label="SVG" value="svg" />
          <el-option label="TIFF" value="tiff" />
          <el-option label="WEBP" value="webp" />
        </el-select>
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
          @click="runConvertImages"
        >
          开始转换
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.result.length" class="result-block">
      <p class="result-title">已生成图片</p>
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
import { inject, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickPdf, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const toImageDpiPresetMap = {
  ultra: 400,
  high: 300,
  standard: 200
}

const form = reactive({
  file: null,
  outputDir: '',
  dpiPreset: 'ultra',
  dpi: 400,
  format: 'png',
  result: []
})

watch(
  () => form.dpiPreset,
  (preset) => {
    if (preset === 'custom') return
    const target = toImageDpiPresetMap[preset]
    if (target) {
      form.dpi = target
    }
  }
)

watch(
  () => form.dpi,
  (value) => {
    if (form.dpiPreset === 'custom') return
    const presetValue = toImageDpiPresetMap[form.dpiPreset]
    if (presetValue && value !== presetValue) {
      form.dpiPreset = 'custom'
    }
  }
)

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

const runConvertImages = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 PDF 文件')
    return
  }
  const res = await callApi('pdf_convert_to_images', {
    filePath: form.file.path,
    outputDir: form.outputDir,
    dpi: form.dpi,
    format: form.format
  })
  if (res) {
    form.result = res.files || []
  }
}
</script>
