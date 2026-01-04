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
        <small>性能监控 · 传感器 · 启动项 · 进程</small>
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
        <div class="overview-header">
          <div class="overview-meta">
            <div class="meta-item">
              <span class="meta-label">系统运行时间</span>
              <strong>{{ status.uptime.text || '未获取' }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">负载情况</span>
              <strong>{{ status.load.label || '未获取' }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">更新时间</span>
              <strong>{{ status.updatedAt || '--' }}</strong>
            </div>
          </div>
          <div class="overview-actions">
            <el-button type="primary" :loading="status.loading" @click="fetchSystemStatus">刷新</el-button>
          </div>
        </div>

        <div class="metric-grid">
          <div class="metric-card">
            <div class="metric-title">
              <span>CPU 负载</span>
              <el-tag size="small" effect="plain">{{ status.cpu.cores || 0 }} 核</el-tag>
            </div>
            <el-progress :percentage="status.cpu.percent" :stroke-width="10" />
            <div class="metric-foot">
              <span>频率 {{ status.cpu.freq || '--' }}</span>
              <span>温度 {{ status.cpu.tempLabel || '暂无' }}</span>
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-title">
              <span>内存占用</span>
              <el-tag size="small" effect="plain">{{ status.memory.text || '--' }}</el-tag>
            </div>
            <el-progress :percentage="status.memory.percent" :stroke-width="10" status="warning" />
            <div class="metric-foot">
              <span>已用 {{ status.memory.usedText || '--' }}</span>
              <span>交换区 {{ status.swap.text || '--' }}</span>
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-title">
              <span>磁盘占用</span>
              <el-tag size="small" effect="plain">{{ status.disks.length }} 分区</el-tag>
            </div>
            <div class="disk-list">
              <div v-for="disk in status.disks" :key="disk.mount" class="disk-item">
                <div class="disk-row">
                  <span class="disk-label">{{ disk.label }}</span>
                  <span class="disk-value">{{ disk.usedText }} / {{ disk.totalText }}</span>
                </div>
                <el-progress :percentage="disk.percent" :stroke-width="8" status="success" />
              </div>
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-title">
              <span>GPU 状态</span>
              <el-tag size="small" effect="plain">{{ status.gpus.length }} 设备</el-tag>
            </div>
            <div v-if="status.gpus.length" class="gpu-list">
              <div v-for="gpu in status.gpus" :key="gpu.name" class="gpu-item">
                <div class="gpu-header">
                  <strong>{{ gpu.name }}</strong>
                  <span>温度 {{ gpu.temperatureLabel || '暂无' }}</span>
                </div>
                <el-progress :percentage="gpu.utilization" :stroke-width="8" />
                <div class="gpu-foot">
                  <span>显存 {{ gpu.memoryUsedText }} / {{ gpu.memoryTotalText }}</span>
                  <span>风扇 {{ gpu.fanSpeedLabel || '暂无' }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-hint">未检测到 GPU 或驱动未暴露信息</div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="传感器" name="sensors">
        <div class="sensor-grid">
          <div class="sensor-panel">
            <div class="sensor-title">温度</div>
            <el-table :data="status.sensors.temperatures" size="small" border>
              <el-table-column prop="name" label="部件" min-width="120" />
              <el-table-column prop="label" label="传感器" min-width="140" />
              <el-table-column prop="value" label="当前" width="110">
                <template #default="{ row }">
                  {{ row.value }}°C
                </template>
              </el-table-column>
              <el-table-column prop="high" label="上限" width="110">
                <template #default="{ row }">
                  {{ row.high ?? '-' }}
                </template>
              </el-table-column>
            </el-table>
            <div v-if="!status.sensors.temperatures.length" class="empty-hint">当前系统未提供温度传感器数据</div>
          </div>

          <div class="sensor-panel">
            <div class="sensor-title">风扇转速</div>
            <el-table :data="status.sensors.fans" size="small" border>
              <el-table-column prop="name" label="部件" min-width="120" />
              <el-table-column prop="label" label="传感器" min-width="140" />
              <el-table-column prop="value" label="RPM" width="120" />
            </el-table>
            <div v-if="!status.sensors.fans.length" class="empty-hint">当前系统未提供风扇转速数据</div>
          </div>

          <div class="sensor-panel">
            <div class="sensor-title">电压</div>
            <el-table :data="status.sensors.voltages" size="small" border>
              <el-table-column prop="name" label="部件" min-width="120" />
              <el-table-column prop="label" label="传感器" min-width="140" />
              <el-table-column prop="value" label="电压" width="120">
                <template #default="{ row }">
                  {{ row.value }} V
                </template>
              </el-table-column>
            </el-table>
            <div v-if="!status.sensors.voltages.length" class="empty-hint">当前系统未提供电压数据</div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="开机启动项" name="startup">
        <div class="startup-form">
          <el-input v-model.trim="ruleForm.name" placeholder="名称" />
          <el-input v-model.trim="ruleForm.command" placeholder="启动命令" />
          <el-input v-model.trim="ruleForm.description" placeholder="备注" />
          <el-switch v-model="ruleForm.autoStart" active-text="开机启动" inactive-text="手动启动" />
          <el-button type="primary" :loading="startupLoading" @click="saveRule">保存</el-button>
          <el-button @click="resetRule">清空</el-button>
        </div>

        <el-table :data="startupRules" size="small" border class="startup-table">
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="command" label="命令" min-width="220" show-overflow-tooltip />
          <el-table-column prop="description" label="备注" min-width="160" show-overflow-tooltip />
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.isSystem" size="small" type="info">系统</el-tag>
              <el-tag v-else size="small" type="success">自定义</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="开机启动" width="120">
            <template #default="{ row }">
              <el-switch v-model="row.autoStart" :disabled="row.isSystem" @change="() => toggleRule(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <template v-if="!row.isSystem">
                <el-button size="small" text type="primary" @click="editRule(row)">编辑</el-button>
                <el-button size="small" text @click="runRule(row)">运行</el-button>
                <el-button size="small" text type="danger" @click="removeRule(row)">删除</el-button>
              </template>
              <template v-else>
                <el-button size="small" text @click="runRule(row)">运行</el-button>
                <el-button size="small" text type="info" @click="openStartupLocation(row)">打开位置</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="进程管理" name="process">
        <div class="toolbar">
          <el-input
            v-model.trim="filters.keyword"
            placeholder="进程名称 / 命令关键字"
            clearable
            class="keyword-input"
            @keyup.enter="fetchProcesses"
          />
          <el-input
            v-model="filters.port"
            placeholder="端口"
            clearable
            class="port-input"
            maxlength="5"
            @keyup.enter="fetchProcesses"
          />
          <el-select v-model="filters.limit" class="limit-select">
            <el-option v-for="count in limitOptions" :key="count" :label="`最多 ${count} 条`" :value="count" />
          </el-select>
          <el-button type="primary" @click="fetchProcesses">检索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
        <el-table
          :data="processRows"
          row-key="pid"
          height="360"
          border
          v-loading="processLoading"
          size="small"
          empty-text="暂无进程匹配结果"
        >
          <el-table-column prop="name" label="进程" min-width="170" show-overflow-tooltip />
          <el-table-column prop="pid" label="PID" width="90" />
          <el-table-column label="端口" min-width="150">
            <template #default="{ row }">
              <template v-if="row.ports?.length">
                <el-tag v-for="port in row.ports.slice(0, 4)" :key="port" size="small" effect="plain">
                  {{ port }}
                </el-tag>
                <span v-if="row.ports.length > 4" class="more-tag">+{{ row.ports.length - 4 }}</span>
              </template>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="memoryPercent" label="内存占用%" width="120">
            <template #default="{ row }">
              {{ row.memoryPercent?.toFixed ? row.memoryPercent.toFixed(2) : row.memoryPercent }}
            </template>
          </el-table-column>
          <el-table-column prop="createLabel" label="启动时间" min-width="160" show-overflow-tooltip />
          <el-table-column prop="cmdline" label="命令" min-width="210" show-overflow-tooltip />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button type="danger" text @click="killProcess(row)">强制结束</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-footer">
          <span>{{ processSummary }}</span>
          <el-button text type="primary" @click="fetchProcesses">刷新</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

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

const apiReady = ref(!!window.pywebview?.api)
if (!apiReady.value) {
  window.addEventListener(
    'pywebviewready',
    () => {
      apiReady.value = true
    },
    { once: true }
  )
}

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
    const res = await window.pywebview.api.system_getSystemStatus()
    if (res?.success) {
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
      loadStartupRules()
      fetchProcesses()
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
      loadStartupRules()
      fetchProcesses()
    }
  }
)

const startupRules = ref([])
const startupLoading = ref(false)
const ruleForm = reactive({
  id: '',
  name: '',
  command: '',
  description: '',
  autoStart: true
})

const loadStartupRules = async () => {
  if (!apiReady.value || !window.pywebview?.api?.system_listStartupRules) return
  startupLoading.value = true
  try {
    const res = await window.pywebview.api.system_listStartupRules()
    if (res?.success) {
      startupRules.value = res.rules || []
    } else {
      ElMessage.error(res?.message || '获取启动项失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '获取启动项失败')
  } finally {
    startupLoading.value = false
  }
}

const resetRule = () => {
  ruleForm.id = ''
  ruleForm.name = ''
  ruleForm.command = ''
  ruleForm.description = ''
  ruleForm.autoStart = true
}

const saveRule = async () => {
  if (!apiReady.value || !window.pywebview?.api?.system_saveStartupRule) {
    ElMessage.warning('当前环境不支持启动项管理')
    return
  }
  startupLoading.value = true
  try {
    const payload = {
      id: ruleForm.id || undefined,
      name: ruleForm.name,
      command: ruleForm.command,
      description: ruleForm.description,
      autoStart: ruleForm.autoStart
    }
    const res = await window.pywebview.api.system_saveStartupRule(payload)
    if (res?.success) {
      startupRules.value = res.rules || []
      resetRule()
      ElMessage.success('启动项已保存')
    } else {
      ElMessage.error(res?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '保存失败')
  } finally {
    startupLoading.value = false
  }
}

const editRule = (row) => {
  ruleForm.id = row.id
  ruleForm.name = row.name
  ruleForm.command = row.command
  ruleForm.description = row.description
  ruleForm.autoStart = !!row.autoStart
}

const toggleRule = async (row) => {
  if (!window.pywebview?.api?.system_saveStartupRule) return
  const res = await window.pywebview.api.system_saveStartupRule({
    id: row.id,
    name: row.name,
    command: row.command,
    description: row.description,
    autoStart: row.autoStart
  })
  if (res?.success) {
    startupRules.value = res.rules || []
  } else {
    ElMessage.error(res?.message || '更新启动项失败')
  }
}

const removeRule = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.name || '该启动项'} 吗？`, '删除启动项', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  const res = await window.pywebview.api.system_removeStartupRule({ id: row.id })
  if (res?.success) {
    startupRules.value = res.rules || []
    ElMessage.success('已删除')
  } else {
    ElMessage.error(res?.message || '删除失败')
  }
}

const runRule = async (row) => {
  if (!window.pywebview?.api?.system_runStartupRule) return
  // 系统启动项直接运行命令
  if (row.isSystem) {
    const res = await window.pywebview.api.system_runSystemStartup({ command: row.command, filePath: row.filePath })
    if (res?.success) {
      ElMessage.success(`已启动`)
    } else {
      ElMessage.error(res?.message || '启动失败')
    }
    return
  }
  const res = await window.pywebview.api.system_runStartupRule({ id: row.id })
  if (res?.success) {
    ElMessage.success(`已启动 PID ${res.pid}`)
  } else {
    ElMessage.error(res?.message || '启动失败')
  }
}

const openStartupLocation = async (row) => {
  if (!window.pywebview?.api?.system_openStartupLocation) return
  const res = await window.pywebview.api.system_openStartupLocation({
    source: row.source,
    regKey: row.regKey,
    filePath: row.filePath
  })
  if (!res?.success) {
    ElMessage.error(res?.message || '打开位置失败')
  }
}

const filters = reactive({
  keyword: '',
  port: '',
  limit: 200
})
const limitOptions = [50, 100, 200, 500]
const processRows = ref([])
const processLoading = ref(false)
const processStats = reactive({ total: 0, hasMore: false })

const normalizePort = (value) => {
  const digits = String(value ?? '').replace(/[^\d]/g, '')
  return digits.slice(0, 5)
}

const buildPayload = () => {
  const payload = { limit: filters.limit }
  if (filters.keyword.trim()) {
    payload.keyword = filters.keyword.trim()
  }
  const portValue = normalizePort(filters.port)
  filters.port = portValue
  if (portValue) {
    payload.port = Number(portValue)
  }
  return payload
}

const fetchProcesses = async () => {
  if (!apiReady.value || !window.pywebview?.api?.system_listProcesses) {
    return
  }
  processLoading.value = true
  try {
    const res = await window.pywebview.api.system_listProcesses(buildPayload())
    if (res?.success) {
      processRows.value = Array.isArray(res.items) ? res.items : []
      processStats.total = typeof res.total === 'number' ? res.total : processRows.value.length
      processStats.hasMore = !!res.hasMore
    } else {
      ElMessage.error(res?.message || '获取进程列表失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '获取进程列表失败')
  } finally {
    processLoading.value = false
  }
}

const resetFilters = () => {
  filters.keyword = ''
  filters.port = ''
  fetchProcesses()
}

const killProcess = async (row) => {
  if (!apiReady.value || !window.pywebview?.api?.system_killProcess) {
    ElMessage.warning('当前环境不支持结束进程')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要强制结束 ${row.name || '该进程'} (PID ${row.pid}) 吗？`,
      '强制结束进程',
      {
        confirmButtonText: '结束',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }
  const res = await window.pywebview.api.system_killProcess(row.pid)
  if (res?.success) {
    ElMessage.success(`已结束 PID ${row.pid}`)
    fetchProcesses()
  } else {
    ElMessage.error(res?.message || '结束进程失败')
  }
}

const processSummary = computed(() => {
  if (!processStats.total) return '暂无进程数据'
  if (processStats.hasMore) {
    return `已展示 ${processRows.value.length}/${processStats.total} 条，建议进一步筛选`
  }
  return `共 ${processStats.total} 条记录`
})
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

.system-tabs {
  margin-top: 4px;
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.overview-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.2);
  min-width: 160px;
}

.meta-label {
  font-size: 11px;
  color: var(--ppx-text-muted);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metric-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ppx-text-primary);
}

.metric-foot {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.disk-list,
.gpu-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.disk-row,
.gpu-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}

.disk-label {
  font-weight: 600;
}

.gpu-foot {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.empty-hint {
  font-size: 12px;
  color: var(--ppx-text-muted);
  margin-top: 8px;
}

.sensor-grid {
  display: grid;
  gap: 16px;
}

.sensor-panel {
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 16px;
  padding: 16px;
}

.sensor-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  margin-bottom: 10px;
}

.startup-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}

.startup-table {
  margin-top: 6px;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.keyword-input {
  flex: 1;
  min-width: 150px;
}

.port-input {
  width: 120px;
}

.limit-select {
  width: 140px;
}

.more-tag {
  margin-left: 6px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 13px;
  color: var(--ppx-text-secondary);
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 900px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .startup-form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .toolbar {
    flex-direction: column;
  }

  .keyword-input,
  .port-input,
  .limit-select {
    width: 100%;
  }

  :deep(.el-button) {
    width: 100%;
  }
}
</style>
