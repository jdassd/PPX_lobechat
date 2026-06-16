<template>
  <section class="panel">
    <header>
      <h4>合并 Word 文档</h4>
      <p>支持自定义顺序，将多个 .docx 合并为单一文件（保留各文档样式）</p>
    </header>
    <div class="merge-toolbar">
      <el-button @click="selectDocx">添加 Word</el-button>
      <el-button text type="danger" @click="clearMerge">清空列表</el-button>
    </div>
    <el-table v-if="form.files.length" :data="form.files" size="small" border>
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="filename" label="文件名" />
      <el-table-column label="操作" width="180">
        <template #default="scope">
          <el-button link type="primary" @click="moveMerge(scope.$index, -1)" :disabled="scope.$index === 0">上移</el-button>
          <el-button link type="primary" @click="moveMerge(scope.$index, 1)" :disabled="scope.$index === form.files.length - 1">下移</el-button>
          <el-button link type="danger" @click="removeMerge(scope.$index)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="请先添加需要合并的 Word" />
    <el-form label-width="120px" class="mt24">
      <el-form-item label="文档间分页">
        <el-switch v-model="form.pageBreak" />
        <span class="hint">开启后每个文档从新的一页开始</span>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="可选" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="例如：合并结果.docx" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :disabled="!form.files.length" :loading="shared.loading" @click="runMerge">
          合并 Word
        </el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.output" class="result-block">
      <p class="result-title">输出文件</p>
      <el-scrollbar max-height="120px">
        <div class="result-list">
          <el-tag type="success" effect="light" @click="openPath(form.output)">{{ form.output }}</el-tag>
        </div>
      </el-scrollbar>
    </div>
  </section>
</template>

<script setup>
import { inject, reactive } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickDocx, pickDir } = inject('wordApi')
const shared = inject('wordShared')

const form = reactive({
  files: [],
  pageBreak: true,
  outputDir: '',
  outputName: '合并结果.docx',
  output: ''
})

const selectDocx = async () => {
  const result = await pickDocx()
  if (!result.length) return
  const existing = new Set(form.files.map((item) => item.path))
  result.forEach((item) => {
    if (!existing.has(item.path)) {
      form.files.push({ ...item })
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
  if (form.files.length < 2) {
    ElMessage.warning('请至少选择两个 Word')
    return
  }
  const res = await callApi('word_merge', {
    files: form.files.map((item) => ({ path: item.path })),
    pageBreak: form.pageBreak,
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
.hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}
</style>
