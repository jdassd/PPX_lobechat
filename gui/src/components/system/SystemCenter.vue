<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#3b7de0">
    <el-alert v-if="!apiReady" type="warning" show-icon class="helper-hint" :closable="false">
      请在桌面客户端内使用，浏览器预览无法访问本地系统信息。
    </el-alert>
    <el-alert v-else-if="status.error" type="error" show-icon class="helper-hint" :closable="false">
      {{ status.error }}
    </el-alert>

    <OverviewPanel v-show="activeTab === 'overview'" :status="status" @refresh="fetchSystemStatus" />
    <SensorsPanel v-show="activeTab === 'sensors'" :status="status" />
    <StartupPanel v-show="activeTab === 'startup'" :api-ready="apiReady" :visible="activeTab === 'startup'" />
    <ProcessPanel v-show="activeTab === 'process'" :api-ready="apiReady" :visible="activeTab === 'process'" />
    <JunkPanel v-show="activeTab === 'junk'" :api-ready="apiReady" />
    <CDriveCleanPanel v-show="activeTab === 'cDriveClean'" :api-ready="apiReady" :is-windows="isWindows" />
    <RegistryPanel v-show="activeTab === 'registry'" :api-ready="apiReady" :is-windows="isWindows" />
    <DiskAnalyzerPanel v-show="activeTab === 'diskAnalyzer'" :api-ready="apiReady" :status="status" />
  </ToolWorkspace>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { usePyReady } from '@/composables/useApiCall'
import { callApi as pyCall } from '@/utils/pyapi'
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import OverviewPanel from './parts/OverviewPanel.vue'
import SensorsPanel from './parts/SensorsPanel.vue'
import StartupPanel from './parts/StartupPanel.vue'
import ProcessPanel from './parts/ProcessPanel.vue'
import JunkPanel from './parts/JunkPanel.vue'
import CDriveCleanPanel from './parts/CDriveCleanPanel.vue'
import RegistryPanel from './parts/RegistryPanel.vue'
import DiskAnalyzerPanel from './parts/DiskAnalyzerPanel.vue'

const isWindows = navigator.platform.toLowerCase().includes('win')

const TABS = [
  { name: 'overview', label: '系统概览' },
  { name: 'sensors', label: '传感器' },
  { name: 'startup', label: '开机启动项' },
  { name: 'process', label: '进程管理' },
  { name: 'junk', label: '垃圾清理' },
  { name: 'cDriveClean', label: 'C盘专清' },
  { name: 'registry', label: '注册表清理' },
  { name: 'diskAnalyzer', label: '磁盘空间分析' },
]

const activeTab = ref('overview')

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

onMounted(() => {
  if (apiReady.value) startStatusPolling()
})

onUnmounted(stopStatusPolling)

watch(
  () => apiReady.value,
  (ready) => {
    if (ready) startStatusPolling()
  }
)
</script>

<style scoped>
.helper-hint {
  margin-bottom: 12px;
}
</style>
