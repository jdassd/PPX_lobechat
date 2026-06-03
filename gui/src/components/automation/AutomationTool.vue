<script setup>
import { computed, reactive, ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

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
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端内使用')
    return false
  }
  return true
}

const refreshRecordStatus = async () => {
  if (!ensurePyReady()) return
  try {
    const { ok, data: res } = await pyCall('automation_record_status')
    if (ok) {
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
    const { ok, message } = await pyCall('automation_record_start', {
      recordMouse: state.record.recordMouse,
      recordKeyboard: state.record.recordKeyboard,
      captureMove: state.record.captureMove,
      moveInterval: state.record.moveInterval
    })
    if (ok) {
      state.record.active = true
      state.record.count = 0
      state.record.duration = 0
      ElMessage.success(message || '已开始录制')
    } else {
      ElMessage.error(message || '启动录制失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '启动录制失败')
  } finally {
    state.loading = false
  }
}

const stopRecord = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const { ok, data: res, message } = await pyCall('automation_record_stop')
    if (ok) {
      state.record.active = false
      state.record.count = res.actions?.length || 0
      state.record.duration = res.duration || 0
      state.macro.payload = res.macro || { actions: res.actions || [] }
      state.macro.text = JSON.stringify(state.macro.payload, null, 2)
      ElMessage.success(message || '录制完成')
    } else {
      ElMessage.error(message || '停止录制失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '停止录制失败')
  } finally {
    state.loading = false
  }
}

const parseMacroText = () => {
  try {
    if (!state.macro.text.trim()) {
      throw new Error('脚本为空')
    }
    const parsed = JSON.parse(state.macro.text)
    const actions = Array.isArray(parsed) ? parsed : parsed.actions
    if (!Array.isArray(actions)) {
      throw new Error('脚本格式不正确')
    }
    state.macro.payload = Array.isArray(parsed) ? { actions: parsed } : parsed
    ElMessage.success('脚本解析成功')
  } catch (error) {
    ElMessage.error(error?.message || '脚本解析失败')
  }
}

const clearMacro = () => {
  state.macro.payload = null
  state.macro.text = ''
}

const chooseMacroDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', state.macro.outputDir)
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
    ElMessage.warning('请先录制或加载脚本')
    return
  }
  if (!state.macro.outputDir) {
    ElMessage.warning('请选择输出目录')
    return
  }
  state.loading = true
  try {
    const { ok, message } = await pyCall('automation_save_macro', {
      outputDir: state.macro.outputDir,
      fileName: state.macro.fileName || 'macro.json',
      macro: state.macro.payload
    })
    if (ok) {
      ElMessage.success(message || '保存成功')
    } else {
      ElMessage.error(message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '保存失败')
  } finally {
    state.loading = false
  }
}

const importMacro = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', ['JSON 文件 (*.json)'])
  if (!files?.length) return
  state.loading = true
  try {
    const { ok, data: res, message } = await pyCall('automation_load_macro', {
      path: files[0].path
    })
    if (ok) {
      state.macro.payload = res.macro || { actions: res.actions || [] }
      state.macro.text = JSON.stringify(state.macro.payload, null, 2)
      ElMessage.success(message || '加载完成')
    } else {
      ElMessage.error(message || '加载失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '加载失败')
  } finally {
    state.loading = false
  }
}

const fetchPlaybackStatus = async () => {
  if (!ensurePyReady()) return
  try {
    const { ok, data: res } = await pyCall('automation_playback_status')
    if (ok) {
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
    ElMessage.warning('请先录制或加载脚本')
    return
  }
  state.loading = true
  try {
    const { ok, message } = await pyCall('automation_play_macro', {
      macro: state.macro.payload,
      loop: state.playback.loop,
      speed: state.playback.speed,
      startDelay: state.playback.startDelay,
      autoScale: state.playback.autoScale
    })
    if (ok) {
      state.playback.running = true
      ElMessage.success(message || '回放已启动')
      startStatusTimer()
    } else {
      ElMessage.error(message || '回放启动失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '回放启动失败')
  } finally {
    state.loading = false
  }
}

const stopPlayback = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const { ok, message } = await pyCall('automation_stop_playback')
    if (ok) {
      state.playback.running = false
      ElMessage.success(message || '已停止回放')
      stopStatusTimer()
    } else {
      ElMessage.error(message || '停止失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '停止失败')
  } finally {
    state.loading = false
  }
}

const selectImage = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', [
    '图片文件 (*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp)'
  ])
  if (files?.length) {
    state.image.file = files[0]
  }
}

const runFindImage = async () => {
  if (!ensurePyReady()) return
  if (!state.image.file?.path) {
    ElMessage.warning('请先选择图片')
    return
  }
  state.loading = true
  try {
    const { ok, data: res, message } = await pyCall('automation_find_image', {
      image: state.image.file.path,
      confidence: state.image.confidence,
      grayscale: state.image.grayscale,
      timeout: state.image.timeout,
      interval: state.image.interval
    })
    state.image.lastResult = res
    if (ok) {
      ElMessage.success(message || '定位成功')
    } else {
      ElMessage.error(message || '定位失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '定位失败')
  } finally {
    state.loading = false
  }
}

const runClickImage = async () => {
  if (!ensurePyReady()) return
  if (!state.image.file?.path) {
    ElMessage.warning('请先选择图片')
    return
  }
  state.loading = true
  try {
    const { ok, data: res, message } = await pyCall('automation_click_image', {
      image: state.image.file.path,
      confidence: state.image.confidence,
      grayscale: state.image.grayscale,
      timeout: state.image.timeout,
      interval: state.image.interval,
      clicks: state.image.clicks,
      button: state.image.button
    })
    state.image.lastResult = res
    if (ok) {
      ElMessage.success(message || '点击成功')
    } else {
      ElMessage.error(message || '点击失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '点击失败')
  } finally {
    state.loading = false
  }
}

const appendImageStep = () => {
  if (!state.image.file?.path) {
    ElMessage.warning('请先选择图片')
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
  ElMessage.success('已加入脚本步骤')
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
          <h3>自动化录制与图像识别</h3>
          <p class="sub">录制鼠标/键盘轨迹，回放脚本，支持图片定位与点击</p>
        </div>
      </div>
    </template>

    <div class="automation-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="录制 / 回放" name="record">
          <section class="panel">
            <header>
              <h4>录制设置</h4>
              <p>支持鼠标轨迹、点击、滚轮与键盘按键事件的录制</p>
            </header>
            <el-form :model="state.record" label-width="140px" class="form-gap">
              <el-form-item label="录制内容">
                <el-checkbox v-model="state.record.recordMouse">鼠标</el-checkbox>
                <el-checkbox v-model="state.record.recordKeyboard">键盘</el-checkbox>
              </el-form-item>
              <el-form-item label="记录轨迹">
                <el-switch v-model="state.record.captureMove" />
                <span class="form-hint">记录鼠标移动轨迹</span>
              </el-form-item>
              <el-form-item label="轨迹采样间隔">
                <el-input-number v-model="state.record.moveInterval" :min="20" :max="1000" :step="10" />
                <span class="form-hint">单位毫秒，数值越小越精细</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" :disabled="state.record.active" @click="startRecord">
                  开始录制
                </el-button>
                <el-button :disabled="!state.record.active" @click="stopRecord">停止录制</el-button>
                <el-button text @click="refreshRecordStatus">刷新状态</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              type="info"
              :closable="false"
              show-icon
            >
              <template #title>
                录制中可操作任意应用，完成后回到本面板点击“停止录制”
              </template>
            </el-alert>
            <div class="record-summary">
              <el-tag type="info" effect="plain">动作数：{{ state.record.count }}</el-tag>
              <el-tag type="info" effect="plain">时长：{{ state.record.duration }} 秒</el-tag>
            </div>
          </section>

          <section class="panel">
            <header>
              <h4>脚本编辑与管理</h4>
              <p>支持导入/导出 JSON 脚本，也可直接编辑</p>
            </header>
            <div class="macro-toolbar">
              <el-button @click="importMacro">导入脚本</el-button>
              <el-button @click="parseMacroText">解析脚本</el-button>
              <el-button @click="clearMacro">清空</el-button>
            </div>
            <el-input
              v-model="state.macro.text"
              type="textarea"
              :rows="10"
              placeholder="这里是脚本 JSON"
            />
            <div class="macro-save">
              <div class="field-row">
                <el-input v-model="state.macro.outputDir" placeholder="选择输出目录" readonly />
                <el-button @click="chooseMacroDir">目录</el-button>
              </div>
              <el-input v-model="state.macro.fileName" placeholder="文件名（.json）" />
              <el-button type="primary" :loading="state.loading" @click="exportMacro">导出脚本</el-button>
            </div>
          </section>

          <section class="panel">
            <header>
              <h4>回放设置</h4>
              <p>建议先将目标窗口置于前台，并确保分辨率一致或开启自动缩放</p>
            </header>
            <el-form :model="state.playback" label-width="140px" class="form-gap">
              <el-form-item label="循环次数">
                <el-input-number v-model="state.playback.loop" :min="1" :max="999" />
              </el-form-item>
              <el-form-item label="速度倍率">
                <el-input-number v-model="state.playback.speed" :min="0.2" :max="8" :step="0.1" />
              </el-form-item>
              <el-form-item label="启动延迟">
                <el-input-number v-model="state.playback.startDelay" :min="0" :max="60" :step="0.5" />
                <span class="form-hint">单位秒，留出切换窗口时间</span>
              </el-form-item>
              <el-form-item label="自动缩放">
                <el-switch v-model="state.playback.autoScale" />
                <span class="form-hint">屏幕分辨率变化时自动缩放坐标</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" :disabled="state.playback.running" @click="startPlayback">
                  开始回放
                </el-button>
                <el-button :disabled="!state.playback.running" @click="stopPlayback">停止回放</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              type="warning"
              :closable="false"
              show-icon
            >
              <template #title>
                PyAutoGUI 默认启用“移到左上角紧急停止”，执行中请注意安全
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="图像识别" name="image">
          <section class="panel">
            <header>
              <h4>图片定位与点击</h4>
              <p>上传目标截图，自动在屏幕中定位并点击</p>
            </header>
            <el-form :model="state.image" label-width="140px" class="form-gap">
              <el-form-item label="目标图片">
                <div class="field-row">
                  <el-input :model-value="state.image.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectImage">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="相似度阈值">
                <el-input-number v-model="state.image.confidence" :min="0.5" :max="1" :step="0.05" />
                <span class="form-hint">需要 OpenCV 支持</span>
              </el-form-item>
              <el-form-item label="灰度匹配">
                <el-switch v-model="state.image.grayscale" />
              </el-form-item>
              <el-form-item label="超时 / 间隔">
                <el-input-number v-model="state.image.timeout" :min="1" :max="60" :step="1" />
                <el-input-number v-model="state.image.interval" :min="0.1" :max="2" :step="0.1" />
                <span class="form-hint">单位秒（超时 / 重试间隔）</span>
              </el-form-item>
              <el-form-item label="点击参数">
                <el-input-number v-model="state.image.clicks" :min="1" :max="5" />
                <el-select v-model="state.image.button" style="width: 120px">
                  <el-option label="左键" value="left" />
                  <el-option label="右键" value="right" />
                  <el-option label="中键" value="middle" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runFindImage">仅定位</el-button>
                <el-button :loading="state.loading" @click="runClickImage">定位并点击</el-button>
                <el-button @click="appendImageStep">加入脚本</el-button>
              </el-form-item>
            </el-form>
            <PreviewPanel v-if="state.image.lastResult" title="识别结果" :content="state.image.lastResult" />
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
