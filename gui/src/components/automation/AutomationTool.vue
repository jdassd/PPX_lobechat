<script setup>
import { computed, reactive, ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

import PreviewPanel from '../shared/PreviewPanel.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const statusTimer = ref(null)

const state = reactive({
  loading: false,
  activeTab: 'record',
  record: {
    active: false,
    recordMouse: true,
    recordKeyboard: true,
    captureMove: true,
    moveInterval: 80,
    count: 0,
    duration: 0
  },
  playback: {
    running: false,
    loop: 1,
    speed: 1,
    startDelay: 1,
    autoScale: true,
    status: null
  },
  macro: {
    payload: null,
    text: '',
    outputDir: '',
    fileName: 'macro.json'
  },
  image: {
    file: null,
    confidence: 0.9,
    grayscale: true,
    timeout: 5,
    interval: 0.5,
    clicks: 1,
    button: 'left',
    lastResult: null
  }
})

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风鍐呬娇鐢?)
    return false
  }
  return true
}

const refreshRecordStatus = async () => {
  if (!ensurePyReady()) return
  try {
    const res = await window.pywebview.api.automation_record_status()
    if (res?.code === 0) {
      state.record.active = !!res.active
      state.record.count = res.count || 0
      state.record.duration = res.duration || 0
    }
  } catch (error) {
    // ignore
  }
}

const startRecord = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_record_start({
      recordMouse: state.record.recordMouse,
      recordKeyboard: state.record.recordKeyboard,
      captureMove: state.record.captureMove,
      moveInterval: state.record.moveInterval
    })
    if (res?.code === 0) {
      state.record.active = true
      state.record.count = 0
      state.record.duration = 0
      ElMessage.success(res.msg || '宸插紑濮嬪綍鍒?)
    } else {
      ElMessage.error(res?.msg || '鍚姩褰曞埗澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍚姩褰曞埗澶辫触')
  } finally {
    state.loading = false
  }
}

const stopRecord = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_record_stop()
    if (res?.code === 0) {
      state.record.active = false
      state.record.count = res.actions?.length || 0
      state.record.duration = res.duration || 0
      state.macro.payload = res.macro || { actions: res.actions || [] }
      state.macro.text = JSON.stringify(state.macro.payload, null, 2)
      ElMessage.success(res.msg || '褰曞埗瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鍋滄褰曞埗澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍋滄褰曞埗澶辫触')
  } finally {
    state.loading = false
  }
}

const parseMacroText = () => {
  try {
    if (!state.macro.text.trim()) {
      throw new Error('鑴氭湰涓虹┖')
    }
    const parsed = JSON.parse(state.macro.text)
    const actions = Array.isArray(parsed) ? parsed : parsed.actions
    if (!Array.isArray(actions)) {
      throw new Error('鑴氭湰鏍煎紡涓嶆纭?)
    }
    state.macro.payload = Array.isArray(parsed) ? { actions: parsed } : parsed
    ElMessage.success('鑴氭湰瑙ｆ瀽鎴愬姛')
  } catch (error) {
    ElMessage.error(error?.message || '鑴氭湰瑙ｆ瀽澶辫触')
  }
}

const clearMacro = () => {
  state.macro.payload = null
  state.macro.text = ''
}

const chooseMacroDir = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.macro.outputDir)
  if (dir) {
    state.macro.outputDir = dir
  }
}

const exportMacro = async () => {
  if (!ensurePyReady()) return
  if (!state.macro.payload && state.macro.text.trim()) {
    parseMacroText()
  }
  if (!state.macro.payload) {
    ElMessage.warning('璇峰厛褰曞埗鎴栧姞杞借剼鏈?)
    return
  }
  if (!state.macro.outputDir) {
    ElMessage.warning('璇烽€夋嫨杈撳嚭鐩綍')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_save_macro({
      outputDir: state.macro.outputDir,
      fileName: state.macro.fileName || 'macro.json',
      macro: state.macro.payload
    })
    if (res?.code === 0) {
      ElMessage.success(res.msg || '淇濆瓨鎴愬姛')
    } else {
      ElMessage.error(res?.msg || '淇濆瓨澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '淇濆瓨澶辫触')
  } finally {
    state.loading = false
  }
}

const importMacro = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['JSON 鏂囦欢 (*.json)'])
  if (!files?.length) return
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_load_macro({
      path: files[0].path
    })
    if (res?.code === 0) {
      state.macro.payload = res.macro || { actions: res.actions || [] }
      state.macro.text = JSON.stringify(state.macro.payload, null, 2)
      ElMessage.success(res.msg || '鍔犺浇瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鍔犺浇澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍔犺浇澶辫触')
  } finally {
    state.loading = false
  }
}

const fetchPlaybackStatus = async () => {
  if (!ensurePyReady()) return
  try {
    const res = await window.pywebview.api.automation_playback_status()
    if (res?.code === 0) {
      state.playback.status = res
      state.playback.running = !!res.active
      if (!res.active && res.error) {
        ElMessage.error(res.error)
      }
      if (!res.active) {
        stopStatusTimer()
      }
    }
  } catch (error) {
    // ignore
  }
}

const startStatusTimer = () => {
  if (statusTimer.value) return
  statusTimer.value = setInterval(fetchPlaybackStatus, 1000)
}

const stopStatusTimer = () => {
  if (statusTimer.value) {
    clearInterval(statusTimer.value)
    statusTimer.value = null
  }
}

const startPlayback = async () => {
  if (!ensurePyReady()) return
  if (!state.macro.payload && state.macro.text.trim()) {
    parseMacroText()
  }
  if (!state.macro.payload || !state.macro.payload.actions?.length) {
    ElMessage.warning('璇峰厛褰曞埗鎴栧姞杞借剼鏈?)
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_play_macro({
      macro: state.macro.payload,
      loop: state.playback.loop,
      speed: state.playback.speed,
      startDelay: state.playback.startDelay,
      autoScale: state.playback.autoScale
    })
    if (res?.code === 0) {
      state.playback.running = true
      ElMessage.success(res.msg || '鍥炴斁宸插惎鍔?)
      startStatusTimer()
    } else {
      ElMessage.error(res?.msg || '鍥炴斁鍚姩澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍥炴斁鍚姩澶辫触')
  } finally {
    state.loading = false
  }
}

const stopPlayback = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_stop_playback()
    if (res?.code === 0) {
      state.playback.running = false
      ElMessage.success(res.msg || '宸插仠姝㈠洖鏀?)
      stopStatusTimer()
    } else {
      ElMessage.error(res?.msg || '鍋滄澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍋滄澶辫触')
  } finally {
    state.loading = false
  }
}

const selectImage = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog([
    '鍥剧墖鏂囦欢 (*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp)'
  ])
  if (files?.length) {
    state.image.file = files[0]
  }
}

const runFindImage = async () => {
  if (!ensurePyReady()) return
  if (!state.image.file?.path) {
    ElMessage.warning('璇峰厛閫夋嫨鍥剧墖')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_find_image({
      image: state.image.file.path,
      confidence: state.image.confidence,
      grayscale: state.image.grayscale,
      timeout: state.image.timeout,
      interval: state.image.interval
    })
    state.image.lastResult = res
    if (res?.code === 0) {
      ElMessage.success(res.msg || '瀹氫綅鎴愬姛')
    } else {
      ElMessage.error(res?.msg || '瀹氫綅澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '瀹氫綅澶辫触')
  } finally {
    state.loading = false
  }
}

const runClickImage = async () => {
  if (!ensurePyReady()) return
  if (!state.image.file?.path) {
    ElMessage.warning('璇峰厛閫夋嫨鍥剧墖')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.automation_click_image({
      image: state.image.file.path,
      confidence: state.image.confidence,
      grayscale: state.image.grayscale,
      timeout: state.image.timeout,
      interval: state.image.interval,
      clicks: state.image.clicks,
      button: state.image.button
    })
    state.image.lastResult = res
    if (res?.code === 0) {
      ElMessage.success(res.msg || '鐐瑰嚮鎴愬姛')
    } else {
      ElMessage.error(res?.msg || '鐐瑰嚮澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鐐瑰嚮澶辫触')
  } finally {
    state.loading = false
  }
}

const appendImageStep = () => {
  if (!state.image.file?.path) {
    ElMessage.warning('璇峰厛閫夋嫨鍥剧墖')
    return
  }
  if (!state.macro.payload) {
    state.macro.payload = { actions: [] }
  }
  const action = {
    type: 'image_click',
    imagePath: state.image.file.path,
    confidence: state.image.confidence,
    grayscale: state.image.grayscale,
    timeout: state.image.timeout,
    interval: state.image.interval,
    clicks: state.image.clicks,
    button: state.image.button
  }
  state.macro.payload.actions = state.macro.payload.actions || []
  state.macro.payload.actions.push(action)
  state.macro.text = JSON.stringify(state.macro.payload, null, 2)
  ElMessage.success('宸插姞鍏ヨ剼鏈楠?)
}

onUnmounted(() => {
  stopStatusTimer()
})
</script>

<template>
  <el-drawer v-model="visibleProxy" size="72%" append-to-body custom-class="automation-drawer">
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">AUTOMATION</p>
          <h3>鑷姩鍖栧綍鍒朵笌鍥惧儚璇嗗埆</h3>
          <p class="sub">褰曞埗榧犳爣/閿洏杞ㄨ抗锛屽洖鏀捐剼鏈紝鏀寔鍥剧墖瀹氫綅涓庣偣鍑?/p>
        </div>
      </div>
    </template>

    <div class="automation-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="褰曞埗 / 鍥炴斁" name="record">
          <section class="panel">
            <header>
              <h4>褰曞埗璁剧疆</h4>
              <p>鏀寔榧犳爣杞ㄨ抗銆佺偣鍑汇€佹粴杞笌閿洏鎸夐敭浜嬩欢鐨勫綍鍒?/p>
            </header>
            <el-form :model="state.record" label-width="140px" class="form-gap">
              <el-form-item label="褰曞埗鍐呭">
                <el-checkbox v-model="state.record.recordMouse">榧犳爣</el-checkbox>
                <el-checkbox v-model="state.record.recordKeyboard">閿洏</el-checkbox>
              </el-form-item>
              <el-form-item label="璁板綍杞ㄨ抗">
                <el-switch v-model="state.record.captureMove" />
                <span class="form-hint">璁板綍榧犳爣绉诲姩杞ㄨ抗</span>
              </el-form-item>
              <el-form-item label="杞ㄨ抗閲囨牱闂撮殧">
                <el-input-number v-model="state.record.moveInterval" :min="20" :max="1000" :step="10" />
                <span class="form-hint">鍗曚綅姣锛屾暟鍊艰秺灏忚秺绮剧粏</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" :disabled="state.record.active" @click="startRecord">
                  寮€濮嬪綍鍒?                </el-button>
                <el-button :disabled="!state.record.active" @click="stopRecord">鍋滄褰曞埗</el-button>
                <el-button text @click="refreshRecordStatus">鍒锋柊鐘舵€?/el-button>
              </el-form-item>
            </el-form>
            <el-alert
              type="info"
              :closable="false"
              show-icon
            >
              <template #title>
                褰曞埗涓彲鎿嶄綔浠绘剰搴旂敤锛屽畬鎴愬悗鍥炲埌鏈潰鏉跨偣鍑烩€滃仠姝㈠綍鍒垛€?              </template>
            </el-alert>
            <div class="record-summary">
              <el-tag type="info" effect="plain">鍔ㄤ綔鏁帮細{{ state.record.count }}</el-tag>
              <el-tag type="info" effect="plain">鏃堕暱锛歿{ state.record.duration }} 绉?/el-tag>
            </div>
          </section>

          <section class="panel">
            <header>
              <h4>鑴氭湰缂栬緫涓庣鐞?/h4>
              <p>鏀寔瀵煎叆/瀵煎嚭 JSON 鑴氭湰锛屼篃鍙洿鎺ョ紪杈?/p>
            </header>
            <div class="macro-toolbar">
              <el-button @click="importMacro">瀵煎叆鑴氭湰</el-button>
              <el-button @click="parseMacroText">瑙ｆ瀽鑴氭湰</el-button>
              <el-button @click="clearMacro">娓呯┖</el-button>
            </div>
            <el-input
              v-model="state.macro.text"
              type="textarea"
              :rows="10"
              placeholder="杩欓噷鏄剼鏈?JSON"
            />
            <div class="macro-save">
              <div class="field-row">
                <el-input v-model="state.macro.outputDir" placeholder="閫夋嫨杈撳嚭鐩綍" readonly />
                <el-button @click="chooseMacroDir">鐩綍</el-button>
              </div>
              <el-input v-model="state.macro.fileName" placeholder="鏂囦欢鍚嶏紙.json锛? />
              <el-button type="primary" :loading="state.loading" @click="exportMacro">瀵煎嚭鑴氭湰</el-button>
            </div>
          </section>

          <section class="panel">
            <header>
              <h4>鍥炴斁璁剧疆</h4>
              <p>寤鸿鍏堝皢鐩爣绐楀彛缃簬鍓嶅彴锛屽苟纭繚鍒嗚鲸鐜囦竴鑷存垨寮€鍚嚜鍔ㄧ缉鏀?/p>
            </header>
            <el-form :model="state.playback" label-width="140px" class="form-gap">
              <el-form-item label="寰幆娆℃暟">
                <el-input-number v-model="state.playback.loop" :min="1" :max="999" />
              </el-form-item>
              <el-form-item label="閫熷害鍊嶇巼">
                <el-input-number v-model="state.playback.speed" :min="0.2" :max="8" :step="0.1" />
              </el-form-item>
              <el-form-item label="鍚姩寤惰繜">
                <el-input-number v-model="state.playback.startDelay" :min="0" :max="60" :step="0.5" />
                <span class="form-hint">鍗曚綅绉掞紝鐣欏嚭鍒囨崲绐楀彛鏃堕棿</span>
              </el-form-item>
              <el-form-item label="鑷姩缂╂斁">
                <el-switch v-model="state.playback.autoScale" />
                <span class="form-hint">灞忓箷鍒嗚鲸鐜囧彉鍖栨椂鑷姩缂╂斁鍧愭爣</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" :disabled="state.playback.running" @click="startPlayback">
                  寮€濮嬪洖鏀?                </el-button>
                <el-button :disabled="!state.playback.running" @click="stopPlayback">鍋滄鍥炴斁</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              type="warning"
              :closable="false"
              show-icon
            >
              <template #title>
                PyAutoGUI 榛樿鍚敤鈥滅Щ鍒板乏涓婅绱ф€ュ仠姝⑩€濓紝鎵ц涓娉ㄦ剰瀹夊叏
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鍥惧儚璇嗗埆" name="image">
          <section class="panel">
            <header>
              <h4>鍥剧墖瀹氫綅涓庣偣鍑?/h4>
              <p>涓婁紶鐩爣鎴浘锛岃嚜鍔ㄥ湪灞忓箷涓畾浣嶅苟鐐瑰嚮</p>
            </header>
            <el-form :model="state.image" label-width="140px" class="form-gap">
              <el-form-item label="鐩爣鍥剧墖">
                <div class="field-row">
                  <el-input :model-value="state.image.file?.path || ''" placeholder="灏氭湭閫夋嫨" readonly />
                  <el-button @click="selectImage">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鐩镐技搴﹂槇鍊?>
                <el-input-number v-model="state.image.confidence" :min="0.5" :max="1" :step="0.05" />
                <span class="form-hint">闇€瑕?OpenCV 鏀寔</span>
              </el-form-item>
              <el-form-item label="鐏板害鍖归厤">
                <el-switch v-model="state.image.grayscale" />
              </el-form-item>
              <el-form-item label="瓒呮椂 / 闂撮殧">
                <el-input-number v-model="state.image.timeout" :min="1" :max="60" :step="1" />
                <el-input-number v-model="state.image.interval" :min="0.1" :max="2" :step="0.1" />
                <span class="form-hint">鍗曚綅绉掞紙瓒呮椂 / 閲嶈瘯闂撮殧锛?/span>
              </el-form-item>
              <el-form-item label="鐐瑰嚮鍙傛暟">
                <el-input-number v-model="state.image.clicks" :min="1" :max="5" />
                <el-select v-model="state.image.button" style="width: 120px">
                  <el-option label="宸﹂敭" value="left" />
                  <el-option label="鍙抽敭" value="right" />
                  <el-option label="涓敭" value="middle" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runFindImage">浠呭畾浣?/el-button>
                <el-button :loading="state.loading" @click="runClickImage">瀹氫綅骞剁偣鍑?/el-button>
                <el-button @click="appendImageStep">鍔犲叆鑴氭湰</el-button>
              </el-form-item>
            </el-form>
            <PreviewPanel v-if="state.image.lastResult" title="璇嗗埆缁撴灉" :content="state.image.lastResult" />
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
.form-gap {
  margin-top: 12px;
}

.form-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.record-summary {
  margin-top: 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.macro-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.macro-save {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>

