<script setup>
import { inject, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const { callApi, pickPdf, pickDir, openPath } = inject('pdfApi')
const shared = inject('pdfShared')
const output = ref('')
const form = reactive({
  filePath: '',
  sourcePassword: '',
  outputDir: '',
  outputName: '',
  watermarkText: '',
  watermarkOpacity: 0.18,
  watermarkSize: 34,
  watermarkRotation: 0,
  redactText: '',
  removeMetadata: true,
  userPassword: '',
  ownerPassword: '',
  allowPrint: true,
  allowCopy: false
})

const choosePdf = async () => {
  const selected = await pickPdf()
  if (!selected.length) return
  const file = selected[0]
  form.filePath = file.path
  form.outputDir = file.dir
  form.outputName = `${file.filename.replace(/\.pdf$/i, '')}_secure.pdf`
}
const chooseOutput = async () => {
  const directory = await pickDir(form.outputDir)
  if (directory) form.outputDir = directory
}
const execute = async () => {
  if (!form.filePath) return ElMessage.warning('请先选择 PDF')
  if (!form.watermarkText && !form.redactText && !form.removeMetadata && !form.userPassword && !form.ownerPassword) return ElMessage.warning('请至少选择一项安全处理')
  const result = await callApi('pdf_secure', { ...form })
  if (result?.output) output.value = result.output
}
</script>

<template>
  <section class="panel-card">
    <div class="panel-title">
      <div>
        <h3>PDF 安全副本</h3>
        <p>添加可见水印、永久遮盖指定文字、清理元数据，并可使用 AES-256 加密。</p>
      </div>
      <el-button @click="choosePdf">选择 PDF</el-button>
    </div>
    <el-alert title="“遮盖文字”会真正移除匹配区域内容；处理结果始终保存为新文件，不覆盖源文件。" type="warning" :closable="false" show-icon />
    <el-form label-position="top" class="secure-form">
      <div class="two-columns">
        <el-form-item label="源 PDF"><el-input v-model="form.filePath" /></el-form-item>
        <el-form-item label="源文件密码（如有）"><el-input v-model="form.sourcePassword" type="password" show-password /></el-form-item>
      </div>
      <el-divider content-position="left">水印与脱敏</el-divider>
      <div class="four-columns">
        <el-form-item label="可见水印文字"><el-input v-model="form.watermarkText" placeholder="留空则不添加" /></el-form-item>
        <el-form-item label="透明度"><el-slider v-model="form.watermarkOpacity" :min="0.05" :max="1" :step="0.05" /></el-form-item>
        <el-form-item label="字号"><el-input-number v-model="form.watermarkSize" :min="8" :max="120" /></el-form-item>
        <el-form-item label="旋转"
          ><el-select v-model="form.watermarkRotation"><el-option v-for="angle in [0, 90, 180, 270]" :key="angle" :label="`${angle}°`" :value="angle" /></el-select
        ></el-form-item>
      </div>
      <el-form-item label="永久遮盖所有匹配文字"><el-input v-model="form.redactText" placeholder="例如：身份证号；留空则不遮盖" /></el-form-item>
      <el-checkbox v-model="form.removeMetadata">清除标题、作者等文档元数据</el-checkbox>

      <el-divider content-position="left">打开密码与权限</el-divider>
      <div class="two-columns">
        <el-form-item label="打开密码"><el-input v-model="form.userPassword" type="password" show-password placeholder="留空则不加密" /></el-form-item>
        <el-form-item label="所有者密码"><el-input v-model="form.ownerPassword" type="password" show-password placeholder="用于更改权限" /></el-form-item>
      </div>
      <div class="permission-row"><el-checkbox v-model="form.allowPrint">允许打印</el-checkbox><el-checkbox v-model="form.allowCopy">允许复制文字</el-checkbox></div>

      <el-divider content-position="left">输出</el-divider>
      <div class="two-columns">
        <el-form-item label="输出目录"
          ><el-input v-model="form.outputDir"
            ><template #append><el-button @click="chooseOutput">选择</el-button></template></el-input
          ></el-form-item
        >
        <el-form-item label="输出文件名"><el-input v-model="form.outputName" /></el-form-item>
      </div>
      <div class="footer-actions"><el-button type="primary" :loading="shared.loading" @click="execute">生成安全副本</el-button><el-button v-if="output" @click="openPath(output)">打开结果</el-button></div>
    </el-form>
  </section>
</template>

<style scoped>
.panel-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 14px;
  padding: 18px;
  background: var(--ppx-bg-elevated);
}
.panel-title,
.footer-actions,
.permission-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.panel-title {
  justify-content: space-between;
  margin-bottom: 14px;
}
h3 {
  margin: 0 0 4px;
}
p {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}
.secure-form {
  margin-top: 16px;
}
.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.four-columns {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 12px;
}
.permission-row {
  margin-bottom: 8px;
}
.footer-actions {
  justify-content: flex-end;
}
@media (max-width: 850px) {
  .two-columns,
  .four-columns {
    grid-template-columns: 1fr;
  }
}
</style>
