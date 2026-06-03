<template>
  <el-dialog
    v-model="visible"
    class="system-center"
    :width="dialogWidth"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <template #title>
      <div class="dialog-title">
        <span>系统管理中心</span>
        <small>性能监控 · 传感器 · 启动项 · 进程 · 清理优化</small>
      </div>
    </template>

    <el-alert v-if="!apiReady" type="warning" show-icon class="helper-hint">
      请在桌面客户端内使用，浏览器预览无法访问本地系统信息。
    </el-alert>
    <el-alert v-else-if="status.error" type="error" show-icon class="helper-hint">
      {{ status.error }}
    </el-alert>

    <el-tabs v-model="activeTab" class="system-tabs">
      <el-tab-pane label="系统概览" name="overview">
        <OverviewPanel :status="status" @refresh="fetchSystemStatus" />
      </el-tab-pane>

      <el-tab-pane label="传感器" name="sensors">
        <SensorsPanel :status="status" />
      </el-tab-pane>

      <el-tab-pane label="开机启动项" name="startup">
        <StartupPanel :api-ready="apiReady" :visible="visible" />
      </el-tab-pane>

      <el-tab-pane label="进程管理" name="process">
        <ProcessPanel :api-ready="apiReady" :visible="visible" />
      </el-tab-pane>

      <el-tab-pane label="垃圾清理" name="junk">
        <JunkPanel :api-ready="apiReady" />
      </el-tab-pane>

      <el-tab-pane label="C盘专清" name="cDriveClean">
        <CDriveCleanPanel :api-ready="apiReady" :is-windows="isWindows" />
      </el-tab-pane>

      <el-tab-pane label="注册表清理" name="registry">
        <RegistryPanel :api-ready="apiReady" :is-windows="isWindows" />
      </el-tab-pane>

      <el-tab-pane label="磁盘空间分析" name="diskAnalyzer">
        <DiskAnalyzerPanel :api-ready="apiReady" :status="status" />
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { usePyReady } from '@/composables/useApiCall'
import { callApi as pyCall } from '@/utils/pyapi'
import OverviewPanel from './parts/OverviewPanel.vue'
import SensorsPanel from './parts/SensorsPanel.vue'
import StartupPanel from './parts/StartupPanel.vue'
import ProcessPanel from './parts/ProcessPanel.vue'
import JunkPanel from './parts/JunkPanel.vue'
import CDriveCleanPanel from './parts/CDriveCleanPanel.vue'
import RegistryPanel from './parts/RegistryPanel.vue'
import DiskAnalyzerPanel from './parts/DiskAnalyzerPanel.vue'

const isWindows = navigator.platform.toLowerCase().includes('win')

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const activeTab = ref('overview')
const windowSize = reactive({ width: 0, height: 0 })
const dialogWidth = computed(() => {
  if (windowSize.width < 480) return '95%'
  if (windowSize.width < 768) return '92%'
  if (windowSize.width < 1200) return '880px'
  return '980px'
})

const handleResize = () => {
  windowSize.width = window.innerWidth
  windowSize.height = window.innerHeight
}

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

// 统一就绪状态管理（替代原手写 pywebviewready 监听）
const { apiReady } = usePyReady()

// 系统状态为各子面板共享的轮询数据（概览/传感器展示、磁盘分析分区列表）。
const status = reactive({
  loading: false,
  error: '',
  updatedAt: '',
  uptime: { text: '' },
  load: { label: '' },
  cpu: { percent: 0, cores: 0, freq: '', tempLabel: '' },
  memory: { percent: 0, text: '', usedText: '' },
  swap: { text: '' },
  disks: [],
  gpus: [],
  sensors: {
    temperatures: [],
    fans: [],
    voltages: []
  }
})

let statusTimer = null

const fetchSystemStatus = async () => {
  if (!apiReady.value || !window.pywebview?.api?.system_getSystemStatus) {
    status.error = '当前客户端未暴露 system_getSystemStatus 接口'
    return
  }
  status.loading = true
  status.error = ''
  try {
    const { ok, data: res } = await pyCall('system_getSystemStatus')
    if (ok) {
      status.updatedAt = res.updatedAt || ''
      status.uptime = res.uptime || { text: '' }
      status.load = res.load || { label: '' }
      status.cpu = res.cpu || status.cpu
      status.memory = res.memory || status.memory
      status.swap = res.swap || status.swap
      status.disks = res.disks || []
      status.gpus = res.gpus || []
      status.sensors = res.sensors || status.sensors
    } else {
      const message = res?.message || '获取系统状态失败'
      status.error = message
      ElMessage.error(message)
    }
  } catch (error) {
    const message = error?.message || '获取系统状态失败'
    status.error = message
    ElMessage.error(message)
  } finally {
    status.loading = false
  }
}

const startStatusPolling = () => {
  if (statusTimer) return
  fetchSystemStatus()
  statusTimer = window.setInterval(fetchSystemStatus, 4000)
}

const stopStatusPolling = () => {
  if (statusTimer) {
    window.clearInterval(statusTimer)
    statusTimer = null
  }
}

watch(
  () => visible.value,
  (show) => {
    if (show && apiReady.value) {
      startStatusPolling()
    } else {
      stopStatusPolling()
    }
  }
)

watch(
  () => apiReady.value,
  (ready) => {
    if (ready && visible.value) {
      startStatusPolling()
    }
  }
)
</script>

<style scoped>
.system-center :deep(.el-dialog__body) {
  padding-top: 0;
}

.dialog-title {
  display: flex;
  flex-direction: column;
}

.dialog-title small {
  color: var(--ppx-text-muted);
  margin-top: 2px;
  font-size: 12px;
}

.helper-hint {
  margin-bottom: 12px;
}
</style>
