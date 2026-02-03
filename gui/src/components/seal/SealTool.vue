<template>
  <el-drawer
    v-model="visibleProxy"
    size="80%"
    append-to-body
    custom-class="seal-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">SEAL WORKSHOP</p>
          <h3>鍏珷鐢熸垚鍣?/h3>
          <p class="sub">鑷畾涔夋枃瀛椼€佸瓧鍙枫€侀鑹蹭笌绾圭悊锛岃緭鍑洪€忔槑 PNG</p>
        </div>
      </div>
    </template>
    <div class="seal-tool">
      <section v-if="state.locked" class="panel lock-panel">
        <header>
          <h4>鏁忔劅鍔熻兘璁块棶纭</h4>
          <p>鍏珷鐢熸垚娑夊強浼佷笟鍙婁釜浜烘晱鎰熶俊鎭紝璇疯緭鍏ヨ闂瘑鐮佸悗缁х画鎿嶄綔銆?/p>
        </header>
        <el-form label-width="110px">
          <el-form-item label="璁块棶瀵嗙爜">
            <el-input
              v-model="state.password"
              type="password"
              autocomplete="off"
              placeholder="璇疯緭鍏ヨ闂瘑鐮?
              show-password
              @keyup.enter="unlockSeal"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="unlockSeal">瑙ｉ攣鍏珷鐢熸垚</el-button>
          </el-form-item>
          <el-alert
            v-if="state.passwordError"
            type="error"
            :closable="false"
            show-icon
          >
            {{ state.passwordError }}
          </el-alert>
        </el-form>
      </section>
      <section v-else class="panel config-panel">
        <header>
          <h4>妯℃澘涓庢枃瀛?/h4>
          <p>鐩墠鎻愪緵鍦嗗舰浼佷笟鍏珷妯℃澘锛屽彲鑷敱璋冩暣鍐呭涓庢牱寮?/p>
        </header>
        <el-form :model="state.form" label-width="110px" class="form-grid">
          <el-form-item label="妯℃澘">
            <el-radio-group v-model="state.template">
              <el-radio-button label="round">鍦嗗舰鍏珷</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="涓婄幆鏂囧瓧">
            <el-input v-model="state.form.topText" placeholder="绀轰緥锛氭煇鏌愮鎶€鏈夐檺鍏徃" />
          </el-form-item>
          <el-form-item label="涓績鏂囧瓧">
            <el-input v-model="state.form.middleText" placeholder="绀轰緥锛氬叕绔?/ 涓撶敤绔? />
          </el-form-item>
          <el-form-item label="涓嬬幆鏂囧瓧">
            <el-input v-model="state.form.bottomText" placeholder="绀轰緥锛氱粺涓€绀句細淇＄敤浠ｇ爜" />
          </el-form-item>
          <el-form-item label="鍗扮珷棰滆壊">
            <div class="field-row">
              <el-color-picker v-model="state.form.color" show-alpha :predefine="predefinedColors" />
              <el-input-number v-model="state.form.alpha" :min="60" :max="255" controls-position="right" />
              <span class="hint">閫忔槑搴?/span>
            </div>
          </el-form-item>
        </el-form>

        <header class="mt40">
          <h4>缁嗚妭鍙傛暟</h4>
          <p>鎸夐渶寰皟灏衡绩銆佹弿杈广€佸瓧浣撲笌鏄熷窘</p>
        </header>
        <div class="param-grid">
          <div class="param-card">
            <p class="label">澶栫幆鍗婂緞 (px)</p>
            <el-slider v-model="state.form.outerRadius" :min="160" :max="320" :step="10" show-input />
          </div>
          <div class="param-card">
            <p class="label">鍦嗙幆杈硅窛</p>
            <el-slider v-model="state.form.edge" :min="4" :max="24" :step="1" show-input />
          </div>
          <div class="param-card">
            <p class="label">鎻忚竟绮楃粏</p>
            <el-slider v-model="state.form.border" :min="8" :max="32" :step="1" show-input />
          </div>
          <div class="param-card">
            <p class="label">浜旀槦灏哄</p>
            <el-slider v-model="state.form.starRadius" :min="40" :max="160" :step="2" show-input />
            <el-switch v-model="state.form.starEnabled" size="small" active-text="鏄剧ず浜旇鏄? />
          </div>
        </div>

        <el-divider />

        <div class="typography-grid">
          <div>
            <p class="title">涓婄幆鏂囧瓧</p>
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
            <p class="title">涓績鏂囧瓧</p>
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
            <p class="title">涓嬬幆鏂囧瓧</p>
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
          <el-form-item label="绾圭悊鍥剧墖">
            <div class="field-row">
              <el-input v-model="state.form.texturePath" placeholder="鍙€夛紝涓哄嵃绔犲鍔犵焊绾硅川鎰? readonly />
              <el-button @click="selectTexture">閫夋嫨</el-button>
              <el-button text type="danger" @click="clearTexture" :disabled="!state.form.texturePath">娓呴櫎</el-button>
            </div>
          </el-form-item>
          <el-form-item label="杈撳嚭鐩綍">
            <div class="field-row">
              <el-input v-model="state.outputDir" placeholder="鐣欑┖鍒欒緭鍑哄埌 static/seals" readonly />
              <el-button @click="selectOutputDir">閫夋嫨</el-button>
            </div>
          </el-form-item>
          <el-form-item label="鏂囦欢鍚?>
            <el-input v-model="state.outputName" placeholder="绀轰緥锛氫紒涓氬叕绔?png" />
          </el-form-item>
        </el-form>

        <div class="actions">
          <el-button @click="resetDefaults">鎭㈠榛樿妯℃澘</el-button>
          <el-button type="primary" :loading="state.loading" @click="runPreview">鐢熸垚棰勮</el-button>
          <el-button type="danger" :loading="state.loading" @click="runExport">瀵煎嚭 PNG</el-button>
        </div>
      </section>

      <section v-if="!state.locked" class="panel preview-panel">
        <header>
          <h4>瀹炴椂棰勮</h4>
          <p>鎵€鏈夊弬鏁拌皟鏁村悗鍙珛鍗虫煡鐪嬮€忔槑 PNG 缁撴灉</p>
        </header>
        <div class="preview-stage">
          <div v-if="state.preview" class="preview-box">
            <img :src="state.preview" alt="seal preview" />
          </div>
          <el-empty v-else description="灏氭湭鐢熸垚棰勮" />
        </div>
        <el-descriptions :column="1" border size="small" class="meta">
          <el-descriptions-item label="鐢诲竷灏哄">
            {{ canvasSize }} px
          </el-descriptions-item>
          <el-descriptions-item label="棰滆壊 / 閫忔槑搴?>
            {{ state.form.color }} / {{ state.form.alpha }}
          </el-descriptions-item>
          <el-descriptions-item label="鏈€杩戣緭鍑?>
            <template v-if="state.resultPath">
              <el-link type="primary" @click="openOutput">{{ state.resultPath }}</el-link>
            </template>
            <span v-else>鏃?/span>
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
const SEAL_UNLOCK_PASSWORD = 'Jd_251114'

const makeDefaultForm = () => ({
  topText: '鏌愭煇绉戞妧鏈夐檺鍏徃',
  middleText: '鍏珷',
  bottomText: '缁熶竴绀句細淇＄敤浠ｇ爜',
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
  outputName: '浼佷笟鍏珷.png',
  resultPath: '',
  locked: true,
  password: '',
  passwordError: ''
})

const canvasSize = computed(() => (state.form.outerRadius + state.form.edge) * 2)

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && !state.locked && !state.preview) {
      runPreview()
    }
  }
)

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风涓娇鐢?)
    return false
  }
  if (!window.pywebview.api.seal_generate) {
    ElMessage.error('褰撳墠瀹㈡埛绔己灏戝叕绔犵敓鎴愯兘鍔?)
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
    ElMessage.error(res?.msg || '鐢熸垚澶辫触')
    return null
  } catch (error) {
    ElMessage.error(error?.message || '鎵ц澶辫触')
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
  const result = await window.pywebview.api.system_pyCreateFileDialog(['鍥剧墖鏂囦欢 (*.png;*.jpg;*.jpeg;*.webp)'])
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

const unlockSeal = () => {
  if (!state.password) {
    state.passwordError = '璇疯緭鍏ヨ闂瘑鐮?
    ElMessage.warning('璇疯緭鍏ヨ闂瘑鐮?)
    return
  }
  if (state.password === SEAL_UNLOCK_PASSWORD) {
    state.locked = false
    state.passwordError = ''
    const needPreview = !state.preview && props.modelValue
    state.password = ''
    if (needPreview) {
      runPreview()
    }
  } else {
    state.passwordError = '瀵嗙爜閿欒锛屾棤娉曡闂叕绔犵敓鎴?
    ElMessage.error('瀵嗙爜閿欒')
  }
}

const resetDefaults = () => {
  Object.assign(state.form, makeDefaultForm())
  state.preview = ''
  state.resultPath = ''
  if (props.modelValue && !state.locked) {
    runPreview()
  }
}
</script>

<style scoped>
/* 浣跨敤鍏ㄥ眬娣辩┖鐜荤拑涓婚鏍峰紡 */

.seal-tool {
  display: grid;
  grid-template-columns: 1.4fr 0.6fr;
  gap: 20px;
}

/* 琛ㄥ崟鍖哄煙 */
.form-grid {
  margin-bottom: 12px;
}

.field-row.compact {
  gap: 8px;
}

.field-row .hint {
  color: var(--ppx-text-muted);
  font-size: 12px;
}

/* 鍙傛暟缃戞牸 */
.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.param-card {
  padding: 14px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-glass-bg);
  transition: all var(--ppx-transition-fast);
}

.param-card:hover {
  border-color: var(--ppx-glass-border-hover);
}

.param-card .label {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--ppx-text-secondary);
}

/* 鎺掔増缃戞牸 */
.typography-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.typography-grid .title {
  margin: 0 0 8px;
  font-weight: 600;
  color: var(--ppx-text-secondary);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

/* 棰勮鍖哄煙 */
.preview-stage {
  min-height: 320px;
  border-radius: var(--ppx-radius-lg);
  border: 1px dashed var(--ppx-glass-border);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  margin-bottom: 18px;
  background-image: linear-gradient(45deg, var(--ppx-glass-bg) 25%, transparent 25%),
                    linear-gradient(-45deg, var(--ppx-glass-bg) 25%, transparent 25%),
                    linear-gradient(45deg, transparent 75%, var(--ppx-glass-bg) 75%),
                    linear-gradient(-45deg, transparent 75%, var(--ppx-glass-bg) 75%);
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

/* 鍝嶅簲寮忓竷灞€ */
@media (max-width: 1440px) {
  .seal-tool {
    gap: 16px;
  }

  .preview-stage {
    min-height: 280px;
  }
}

@media (max-width: 1200px) {
  .seal-tool {
    grid-template-columns: 1.2fr 0.8fr;
    gap: 14px;
  }

  .param-grid {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
  }

  .preview-stage {
    min-height: 240px;
  }

  .preview-box {
    max-width: 280px;
    max-height: 280px;
  }
}

@media (max-width: 1024px) {
  .seal-tool {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .param-grid {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  }

  .typography-grid {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }

  .actions {
    margin-top: 14px;
    gap: 10px;
  }
}

@media (max-width: 768px) {
  .seal-tool {
    gap: 12px;
  }

  .param-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .typography-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .preview-stage {
    min-height: 200px;
    padding: 12px;
  }

  .preview-box {
    max-width: 220px;
    max-height: 220px;
  }

  .actions {
    flex-wrap: wrap;
    margin-top: 12px;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .param-card {
    padding: 10px;
  }

  .param-grid {
    gap: 8px;
  }

  .typography-grid {
    gap: 10px;
  }

  .preview-stage {
    min-height: 160px;
    padding: 8px;
  }

  .preview-box {
    max-width: 180px;
    max-height: 180px;
  }

  .actions {
    margin-top: 10px;
    gap: 6px;
  }
}
</style>

