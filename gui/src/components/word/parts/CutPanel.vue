<template>
  <section class="panel">
    <header>
      <h4>切割 Word 文档（保留指定页码）</h4>
      <p>按真实页码剔除其余内容，只保留指定范围，输出单个文件（100% 保留原格式，需本机安装 LibreOffice）</p>
    </header>
    <el-form :model="form" label-width="120px">
      <el-form-item label="源 Word">
        <div class="field-row">
          <el-button @click="selectDocx">选择 Word</el-button>
          <span v-if="form.file" class="file-chip">{{ form.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
          <el-tag v-if="totalPages" type="success" effect="plain">共 {{ totalPages }} 页</el-tag>
        </div>
      </el-form-item>
      <el-form-item label="切割方式">
        <el-radio-group v-model="form.mode">
          <el-radio-button value="range">连续范围</el-radio-button>
          <el-radio-button value="custom">自定义页码</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.mode === 'range'" label="保留页码">
        <div class="field-row">
          <el-input-number v-model="form.startPage" :min="1" :max="totalPages || 9999" />
          <span>至</span>
          <el-input-number v-model="form.endPage" :min="1" :max="totalPages || 9999" />
        </div>
      </el-form-item>
      <el-form-item v-else label="保留页码">
        <el-input v-model="form.pageSpec" placeholder="如 1-3,5,8" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空则与源文件同级" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="form.outputName" placeholder="可选，例如：节选.docx" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runCut">开始切割</el-button>
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
import { inject, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickDocx, pickDir } = inject('wordApi')
const shared = inject('wordShared')

const form = reactive({
  file: null,
  mode: 'range',
  startPage: 1,
  endPage: 1,
  pageSpec: '',
  outputDir: '',
  outputName: '',
  output: ''
})
const totalPages = ref(0)

const selectDocx = async () => {
  const result = await pickDocx()
  if (!result.length) return
  form.file = result[0]
  totalPages.value = 0
  const res = await callApi('word_page_count', { filePath: form.file.path })
  if (res) {
    totalPages.value = res.pages || 0
    if (totalPages.value) form.endPage = totalPages.value
  }
}

const selectDir = async () => {
  const dir = await pickDir(form.outputDir || '')
  if (dir) {
    form.outputDir = dir
  }
}

const runCut = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 Word 文件')
    return
  }
  if (form.mode === 'custom' && !form.pageSpec.trim()) {
    ElMessage.warning('请填写要保留的页码')
    return
  }
  const res = await callApi('word_cut', {
    filePath: form.file.path,
    mode: form.mode,
    startPage: form.startPage,
    endPage: form.endPage,
    pageSpec: form.pageSpec,
    outputDir: form.outputDir,
    outputName: form.outputName
  })
  if (res) {
    form.output = res.output
  }
}
</script>

<style scoped>
.hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}
</style>
