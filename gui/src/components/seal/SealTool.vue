<template>
  <el-drawer
    v-model="visibleProxy"
    size="70%"
    append-to-body
    custom-class="seal-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">SEAL WORKSHOP</p>
          <h3>公章生成器</h3>
          <p class="sub">自定义文字、字号、颜色与纹理，输出透明 PNG</p>
        </div>
        <el-tag type="danger" size="large">Alpha</el-tag>
      </div>
    </template>
    <div class="seal-tool">
      <section class="panel config-panel">
        <header>
          <h4>模板与文字</h4>
          <p>目前提供圆形企业公章模板，可自由调整内容与样式</p>
        </header>
        <el-form :model="state.form" label-width="110px" class="form-grid">
          <el-form-item label="模板">
            <el-radio-group v-model="state.template">
              <el-radio-button label="round">圆形公章</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="上环文字">
            <el-input v-model="state.form.topText" placeholder="示例：某某科技有限公司" />
          </el-form-item>
          <el-form-item label="中心文字">
            <el-input v-model="state.form.middleText" placeholder="示例：公章 / 专用章" />
          </el-form-item>
          <el-form-item label="下环文字">
            <el-input v-model="state.form.bottomText" placeholder="示例：统一社会信用代码" />
          </el-form-item>
          <el-form-item label="印章颜色">
            <div class="field-row">
              <el-color-picker v-model="state.form.color" show-alpha :predefine="predefinedColors" />
              <el-input-number v-model="state.form.alpha" :min="60" :max="255" controls-position="right" />
              <span class="hint">透明度</span>
            </div>
          </el-form-item>
        </el-form>

        <header class="mt40">
          <h4>细节参数</h4>
          <p>按需微调尺⼨、描边、字体与星徽</p>
        </header>
        <div class="param-grid">
          <div class="param-card">
            <p class="label">外环半径 (px)</p>
            <el-slider v-model="state.form.outerRadius" :min="160" :max="320" :step="10" show-input />
          </div>
          <div class="param-card">
            <p class="label">圆环边距</p>
            <el-slider v-model="state.form.edge" :min="4" :max="24" :step="1" show-input />
          </div>
          <div class="param-card">
            <p class="label">描边粗细</p>
            <el-slider v-model="state.form.border" :min="8" :max="32" :step="1" show-input />
          </div>
          <div class="param-card">
            <p class="label">五星尺寸</p>
            <el-slider v-model="state.form.starRadius" :min="40" :max="160" :step="2" show-input />
            <el-switch v-model="state.form.starEnabled" size="small" active-text="显示五角星" />
          </div>
        </div>

        <el-divider />

        <div class="typography-grid">
          <div>
            <p class="title">上环文字</p>
            <div class="field-row">
              <el-input-number v-model="state.form.fontSizeTop" :min="24" :max="160" />
              <el-input-number v-model="state.form.topAngle" :min="120" :max="320" />
            </div>
            <div class="field-row compact">
              <el-input-number v-model="state.form.fontRatioTop" :step="0.05" :min="0.3" :max="1.2" />
              <el-input-number v-model="state.form.strokeTop" :min="0" :max="4" />
            </div>
          </div>
          <div>
            <p class="title">中心文字</p>
            <div class="field-row">
              <el-input-number v-model="state.form.fontSizeMiddle" :min="20" :max="120" />
              <el-input-number v-model="state.form.middleRadius" :min="60" :max="260" />
            </div>
            <div class="field-row compact">
              <el-input-number v-model="state.form.fontRatioMiddle" :step="0.05" :min="0.3" :max="1.2" />
              <el-input-number v-model="state.form.strokeMiddle" :min="0" :max="4" />
            </div>
          </div>
          <div>
            <p class="title">下环文字</p>
            <div class="field-row">
              <el-input-number v-model="state.form.fontSizeBottom" :min="12" :max="80" />
              <el-input-number v-model="state.form.bottomAngle" :min="40" :max="180" />
            </div>
            <div class="field-row compact">
              <el-input-number v-model="state.form.fontRatioBottom" :step="0.05" :min="0.3" :max="1.5" />
              <el-input-number v-model="state.form.strokeBottom" :min="0" :max="4" />
            </div>
          </div>
        </div>

        <el-divider />

        <el-form label-width="110px">
          <el-form-item label="纹理图片">
            <div class="field-row">
              <el-input v-model="state.form.texturePath" placeholder="可选，为印章增加纸纹质感" readonly />
              <el-button @click="selectTexture">选择</el-button>
              <el-button text type="danger" @click="clearTexture" :disabled="!state.form.texturePath">清除</el-button>
            </div>
          </el-form-item>
          <el-form-item label="输出目录">
            <div class="field-row">
              <el-input v-model="state.outputDir" placeholder="留空则输出到 static/seals" readonly />
              <el-button @click="selectOutputDir">选择</el-button>
            </div>
          </el-form-item>
          <el-form-item label="文件名">
            <el-input v-model="state.outputName" placeholder="示例：企业公章.png" />
          </el-form-item>
        </el-form>

        <div class="actions">
          <el-button @click="resetDefaults">恢复默认模板</el-button>
          <el-button type="primary" :loading="state.loading" @click="runPreview">生成预览</el-button>
          <el-button type="danger" :loading="state.loading" @click="runExport">导出 PNG</el-button>
        </div>
      </section>

      <section class="panel preview-panel">
        <header>
          <h4>实时预览</h4>
          <p>所有参数调整后可立即查看透明 PNG 结果</p>
        </header>
        <div class="preview-stage">
          <div v-if="state.preview" class="preview-box">
            <img :src="state.preview" alt="seal preview" />
          </div>
          <el-empty v-else description="尚未生成预览" />
        </div>
        <el-descriptions :column="1" border size="small" class="meta">
          <el-descriptions-item label="画布尺寸">
            {{ canvasSize }} px
          </el-descriptions-item>
          <el-descriptions-item label="颜色 / 透明度">
            {{ state.form.color }} / {{ state.form.alpha }}
          </el-descriptions-item>
          <el-descriptions-item label="最近输出">
            <template v-if="state.resultPath">
              <el-link type="primary" @click="openOutput">{{ state.resultPath }}</el-link>
            </template>
            <span v-else>无</span>
          </el-descriptions-item>
        </el-descriptions>
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const predefinedColors = ['#d4252c', '#c11f26', '#cf1b2c', '#bb1f2c', '#a2192e']

const makeDefaultForm = () => ({
  topText: '某某科技有限公司',
  middleText: '公章',
  bottomText: '统一社会信用代码',
  color: '#d4252c',
  alpha: 220,
  outerRadius: 240,
  edge: 8,
  border: 14,
  starRadius: 86,
  middleRadius: 150,
  starEnabled: true,
  fontSizeTop: 86,
  fontSizeMiddle: 60,
  fontSizeBottom: 32,
  fontRatioTop: 0.66,
  fontRatioMiddle: 0.7,
  fontRatioBottom: 1,
  topAngle: 270,
  middleAngle: 72,
  bottomAngle: 60,
  strokeTop: 2,
  strokeMiddle: 1,
  strokeBottom: 1,
  texturePath: ''
})

const state = reactive({
  template: 'round',
  form: makeDefaultForm(),
  preview: '',
  loading: false,
  outputDir: '',
  outputName: '企业公章.png',
  resultPath: ''
})

const canvasSize = computed(() => (state.form.outerRadius + state.form.edge) * 2)

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && !state.preview) {
      runPreview()
    }
  }
)

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  if (!window.pywebview.api.seal_generate) {
    ElMessage.error('当前客户端缺少公章生成能力')
    return false
  }
  return true
}

const buildPayload = (mode) => ({
  mode,
  template: state.template,
  topText: state.form.topText,
  middleText: state.form.middleText,
  bottomText: state.form.bottomText,
  color: state.form.color,
  alpha: state.form.alpha,
  outerRadius: state.form.outerRadius,
  edge: state.form.edge,
  border: state.form.border,
  starRadius: state.form.starRadius,
  starEnabled: state.form.starEnabled,
  middleRadius: state.form.middleRadius,
  fontSizeTop: state.form.fontSizeTop,
  fontSizeMiddle: state.form.fontSizeMiddle,
  fontSizeBottom: state.form.fontSizeBottom,
  fontRatioTop: state.form.fontRatioTop,
  fontRatioMiddle: state.form.fontRatioMiddle,
  fontRatioBottom: state.form.fontRatioBottom,
  topAngle: state.form.topAngle,
  middleAngle: state.form.middleAngle,
  bottomAngle: state.form.bottomAngle,
  strokeTop: state.form.strokeTop,
  strokeMiddle: state.form.strokeMiddle,
  strokeBottom: state.form.strokeBottom,
  texturePath: state.form.texturePath,
  outputDir: state.outputDir,
  outputName: state.outputName
})

const callSealApi = async (mode) => {
  if (!ensurePyReady()) return null
  state.loading = true
  try {
    const res = await window.pywebview.api.seal_generate(buildPayload(mode))
    if (res?.code === 0) {
      if (res.preview) {
        state.preview = res.preview
      }
      if (res.output) {
        state.resultPath = res.output
      }
      if (res.msg) {
        ElMessage.success(res.msg)
      }
      return res
    }
    ElMessage.error(res?.msg || '生成失败')
    return null
  } catch (error) {
    ElMessage.error(error?.message || '执行失败')
    return null
  } finally {
    state.loading = false
  }
}

const runPreview = async () => {
  const result = await callSealApi('preview')
  if (!result && !state.preview) {
    state.preview = ''
  }
}

const runExport = async () => {
  const result = await callSealApi('export')
  if (result?.output) {
    state.resultPath = result.output
  }
}

const selectTexture = async () => {
  if (!ensurePyReady()) return
  const result = await window.pywebview.api.system_pyCreateFileDialog(['图片文件 (*.png;*.jpg;*.jpeg;*.webp)'])
  if (result?.length) {
    state.form.texturePath = result[0].path
  }
}

const clearTexture = () => {
  state.form.texturePath = ''
}

const selectOutputDir = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.outputDir || '')
  if (dir) {
    state.outputDir = dir
  }
}

const openOutput = () => {
  if (!state.resultPath || !ensurePyReady()) return
  window.pywebview.api.system_pyOpenFile(state.resultPath)
}

const resetDefaults = () => {
  Object.assign(state.form, makeDefaultForm())
  state.preview = ''
  state.resultPath = ''
  if (props.modelValue) {
    runPreview()
  }
}
</script>

<style scoped>
.seal-tool {
  display: grid;
  grid-template-columns: 1.3fr 0.7fr;
  gap: 24px;
}

.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-head h3 {
  margin: 4px 0;
  font-size: 24px;
}

.drawer-head .eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.2em;
  color: #9094a6;
}

.drawer-head .sub {
  margin: 0;
  color: #6c7185;
  font-size: 14px;
}

.panel {
  background: #fff;
  border-radius: 18px;
  padding: 22px;
  border: 1px solid #edf0f5;
}

.config-panel header,
.preview-panel header {
  margin-bottom: 16px;
}

.config-panel header h4,
.preview-panel header h4 {
  margin: 0;
}

.config-panel header p,
.preview-panel header p {
  margin: 6px 0 0;
  color: #7a8093;
}

.form-grid {
  margin-bottom: 12px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.field-row.compact {
  gap: 8px;
}

.field-row .hint {
  color: #a0a4b5;
  font-size: 12px;
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.param-card {
  padding: 14px;
  border: 1px solid #eef0f7;
  border-radius: 14px;
  background: #fdfdff;
}

.param-card .label {
  margin: 0 0 8px;
  font-size: 13px;
  color: #4d5366;
}

.typography-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.typography-grid .title {
  margin: 0 0 8px;
  font-weight: 600;
  color: #4d5366;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

.preview-stage {
  min-height: 320px;
  border-radius: 18px;
  border: 1px dashed #dcdfea;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  margin-bottom: 18px;
  background-image: linear-gradient(45deg, #f3f5fb 25%, transparent 25%), linear-gradient(-45deg, #f3f5fb 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f3f5fb 75%), linear-gradient(-45deg, transparent 75%, #f3f5fb 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}

.preview-box {
  max-width: 360px;
  max-height: 360px;
}

.preview-box img {
  width: 100%;
  height: auto;
  display: block;
}

.meta {
  margin-top: 12px;
}

.mt40 {
  margin-top: 40px;
}

@media (max-width: 1280px) {
  .seal-tool {
    grid-template-columns: 1fr;
  }
}
</style>
