<template>
  <section class="panel">
    <header>
      <h4>拆分 Word 文档（输出多个文件）</h4>
      <p>将一个 .docx 拆分为多个文件，可按真实页码、段落数、分页符或标题拆分（100% 保留原格式）</p>
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
      <el-form-item label="拆分方式">
        <el-radio-group v-model="form.mode">
          <el-radio-button value="pages">按页数</el-radio-button>
          <el-radio-button value="paragraphs">按段落数</el-radio-button>
          <el-radio-button value="pagebreak">按分页符</el-radio-button>
          <el-radio-button value="heading">按标题</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.mode === 'pages'" label="每个文件页数">
        <el-input-number v-model="form.pagesPerFile" :min="1" :max="500" />
        <span class="hint">按真实分页计算，需本机安装 LibreOffice</span>
      </el-form-item>
      <el-form-item v-if="form.mode === 'paragraphs'" label="每个文件段落数">
        <el-input-number v-model="form.paragraphsPerFile" :min="1" :max="500" />
      </el-form-item>
      <el-form-item v-if="form.mode === 'heading'" label="标题级别">
        <el-select v-model="form.headingLevel" style="width: 140px">
          <el-option v-for="lv in 6" :key="lv" :label="`${lv} 级标题`" :value="lv" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.mode === 'pagebreak'">
        <el-alert type="info" :closable="false" show-icon title="在文档中手动插入的“分页符 / 分节符”处切割" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空则与源文件同级" readonly />
          <el-button @click="selectDir">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="shared.loading" @click="runSplit">开始拆分</el-button>
      </el-form-item>
    </el-form>
    <div v-if="form.result.length" class="result-block">
      <p class="result-title">拆分结果</p>
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
import { inject, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, openPath, pickDocx, pickDir } = inject('wordApi')
const shared = inject('wordShared')

const form = reactive({
  file: null,
  mode: 'pages',
  pagesPerFile: 1,
  paragraphsPerFile: 10,
  headingLevel: 1,
  outputDir: '',
  result: []
})
const totalPages = ref(0)

const refreshPageCount = async () => {
  totalPages.value = 0
  if (!form.file || form.mode !== 'pages') return
  const res = await callApi('word_page_count', { filePath: form.file.path })
  if (res) totalPages.value = res.pages || 0
}

watch(() => form.mode, refreshPageCount)

const selectDocx = async () => {
  const result = await pickDocx()
  if (!result.length) return
  form.file = result[0]
  refreshPageCount()
}

const selectDir = async () => {
  const dir = await pickDir(form.outputDir || '')
  if (dir) {
    form.outputDir = dir
  }
}

const runSplit = async () => {
  if (!form.file) {
    ElMessage.warning('请选择 Word 文件')
    return
  }
  const res = await callApi('word_split', {
    filePath: form.file.path,
    mode: form.mode,
    pagesPerFile: form.pagesPerFile,
    paragraphsPerFile: form.paragraphsPerFile,
    headingLevel: form.headingLevel,
    outputDir: form.outputDir
  })
  if (res) {
    form.result = res.files || []
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
