<template>
  <section class="panel">
    <header>
      <h4>将多个 PDF 合并</h4>
      <p>支持自定义顺序，生成单一归档文件</p>
    </header>
    <div class="merge-toolbar">
      <el-button @click="selectPdf">添加 PDF</el-button>
      <el-button text type="danger" @click="clearMerge">清空列表</el-button>
    </div>
    <el-table
      v-if="form.files.length"
      :data="form.files"
      size="small"
      border
    >
      <el-table-column type="index" label="#" width="50" />
      <el-table-column label="页码选择" width="220">
        <template #default="scope">
          <el-input
            v-model="scope.row.pageSpec"
            size="small"
            placeholder="如 1-3,5,8"
          />
        </template>
      </el-table-column>
      <el-table-column prop="filename" label="文件名" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button link type="primary" @click="moveMerge(scope.$index, -1)" :disabled="scope.$index === 0">上移</el-button>
          <el-button link type="primary" @click="moveMerge(scope.$index, 1)" :disabled="scope.$index === form.files.length - 1">下移</el-button>
          <el-button link type="danger" @click="removeMerge(scope.$index)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="请先添加需要合并的 PDF" />
    <el-form label-width="110px" class="mt24">
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="可选" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="例如：合并结果.pdf" />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :disabled="!form.files.length"
          :loading="shared.loading"
          @click="runMerge"
        >
          合并 PDF
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-scrollbar max-height="120px">
        <div class="result-list">
          <el-tag
            type="success"
            effect="light"
            @click="openPath(form.output)"
          >
            {{ form.output }}
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
  files: [],
  outputDir: '',
  outputName: '合并结果.pdf',
  output: ''
})

const selectPdf = async () => {
  const result = await pickPdf()
  if (!result.length) return
  const existing = new Set(form.files.map((item) => item.path))
  result.forEach((item) => {
    if (!existing.has(item.path)) {
      const entry = { ...item }
      if (entry.pageSpec === undefined) {
        entry.pageSpec = ''
      }
      form.files.push(entry)
    }
  })
}

const selectDir = async () => {
  const dir = await pickDir(form.outputDir || '')
  if (dir) {
    form.outputDir = dir
  }
}

const moveMerge = (index, offset) => {
  const target = index + offset
  if (target < 0 || target >= form.files.length) return
  const list = form.files
  const item = list[index]
  list.splice(index, 1)
  list.splice(target, 0, item)
}

const removeMerge = (index) => {
  form.files.splice(index, 1)
}

const clearMerge = () => {
  form.files.splice(0, form.files.length)
}

const runMerge = async () => {
  if (!form.files.length) {
    ElMessage.warning('请至少选择两个 PDF')
    return
  }
  const res = await callApi('pdf_merge', {
    files: form.files.map((item) => ({
      path: item.path,
      pageSpec: item.pageSpec || ''
    })),
    outputDir: form.outputDir,
    outputName: form.outputName
  })
  if (res) {
    form.output = res.output
  }
}
</script>

<style scoped>
.merge-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.mt24 {
  margin-top: 24px;
}
</style>
