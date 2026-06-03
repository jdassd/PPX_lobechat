<template>
  <section class="panel">
    <header>
      <h4>将图片集合导出为 PDF</h4>
      <p>支持 1/2/4 图布局，自定义纸张与边距</p>
    </header>
    <p class="image-pdf-hint">与图片工具中的「图片转 PDF」功能等价，这里仅提供一个快捷入口。</p>
    <div class="field-row">
      <el-button @click="addImagePdfFiles">添加图片</el-button>
      <el-button text type="danger" :disabled="!form.files.length" @click="clearImagePdf">
        清空
      </el-button>
    </div>
    <el-table
      v-if="form.files.length"
      :data="form.files"
      border
      size="small"
      style="margin: 12px 0"
    >
      <el-table-column type="index" width="50" label="#" />
      <el-table-column prop="filename" label="文件名" />
      <el-table-column label="操作" width="160">
        <template #default="scope">
          <el-button link type="primary" @click="moveImagePdfFile(scope.$index, -1)" :disabled="scope.$index === 0">上移</el-button>
          <el-button link type="primary" @click="moveImagePdfFile(scope.$index, 1)" :disabled="scope.$index === form.files.length - 1">下移</el-button>
          <el-button link type="danger" @click="removeImagePdfFile(scope.$index)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-form :model="form" label-width="140px" class="form-gap">
      <el-form-item label="纸张尺寸">
        <el-select v-model="form.pageSize" style="width: 200px">
          <el-option label="A4" value="a4" />
          <el-option label="A5" value="a5" />
          <el-option label="Letter" value="letter" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      <div v-if="form.pageSize === 'custom'" class="field-row">
        <el-form-item label="宽 (px)">
          <el-input-number v-model="form.customWidth" :min="600" :max="6000" />
        </el-form-item>
        <el-form-item label="高 (px)">
          <el-input-number v-model="form.customHeight" :min="600" :max="6000" />
        </el-form-item>
      </div>
      <el-form-item label="每页布局">
        <el-radio-group v-model="form.perPage">
          <el-radio-button :label="1">1 / 页</el-radio-button>
          <el-radio-button :label="2">2 / 页</el-radio-button>
          <el-radio-button :label="4">4 / 页</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="边距 (px)">
        <el-input-number v-model="form.margin" :min="10" :max="200" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空自动创建" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="如：图片合集.pdf" />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :loading="shared.loading"
          :disabled="!form.files.length"
          @click="runImagesToPdf"
        >
          生成 PDF
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-tag type="info" effect="plain" @click="openPath(form.output)">
        {{ form.output }}
      </el-tag>
    </div>
  </section>
</template>

<script setup>
import { inject, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickImages, pickDir } = inject('pdfApi')
const shared = inject('pdfShared')

const form = reactive({
  files: [],
  pageSize: 'a4',
  customWidth: 2480,
  customHeight: 3508,
  perPage: 1,
  margin: 40,
  outputDir: '',
  outputName: '图片合集.pdf',
  output: ''
})

const selectDir = async () => {
  const dir = await pickDir(form.outputDir || '')
  if (dir) {
    form.outputDir = dir
  }
}

const addImagePdfFiles = async () => {
  const files = await pickImages()
  if (files?.length) {
    form.files.push(...files)
  }
}

const removeImagePdfFile = (index) => {
  form.files.splice(index, 1)
}

const moveImagePdfFile = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= form.files.length) return
  const list = form.files
  const current = list[index]
  list.splice(index, 1)
  list.splice(target, 0, current)
}

const clearImagePdf = () => {
  form.files.splice(0, form.files.length)
}

const runImagesToPdf = async () => {
  if (!form.files.length) {
    ElMessage.warning('请先选择图片')
    return
  }
  const res = await callApi('pdf_images_to_pdf', {
    images: form.files.map((item) => item.path),
    pageSize: form.pageSize,
    customWidth: form.customWidth,
    customHeight: form.customHeight,
    perPage: form.perPage,
    margin: form.margin,
    outputDir: form.outputDir,
    outputName: form.outputName
  })
  if (res) {
    form.output = res.output
  }
}
</script>

<style scoped>
.image-pdf-hint {
  margin: 4px 0 12px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>
