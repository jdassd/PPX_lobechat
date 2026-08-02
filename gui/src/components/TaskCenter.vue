<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { CircleCheck, CircleClose, Clock, Download, FolderOpened, Loading, RefreshRight, Search, VideoPause, VideoPlay, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { featureById, toolById } from '@/config/tools'
import { callApi } from '@/utils/pyapi'
import { clearFinishedTasks, hydrateBackendTasks, queuePaused, tasks } from '@/utils/taskCenter'

const emit = defineEmits(['open'])
const query = ref('')
const statusFilter = ref('all')
const toolFilter = ref('all')
const page = ref(1)
const pageSize = ref(20)
const selectedIds = ref([])
const backendStats = ref(null)
const refreshing = ref(false)
let refreshTimer = null

const taskStats = computed(() => {
  if (backendStats.value) return backendStats.value
  const counts = tasks.value.reduce((output, task) => ({ ...output, [task.status]: (output[task.status] || 0) + 1 }), {})
  const decisive = (counts.success || 0) + (counts.failed || 0)
  const durations = tasks.value.filter((task) => task.startedAt && task.endedAt).map((task) => Math.max(0, (task.endedAt - task.startedAt) / 1000))
  return {
    active: (counts.queued || 0) + (counts.running || 0),
    attention: (counts.failed || 0) + (counts.interrupted || 0) + (counts.canceled || 0),
    successRate: decisive ? Math.round(((counts.success || 0) * 1000) / decisive) / 10 : 0,
    averageDurationSeconds: durations.length ? durations.reduce((total, item) => total + item, 0) / durations.length : 0
  }
})
const toolOptions = computed(() => {
  const ids = [...new Set(tasks.value.map((task) => task.tool).filter(Boolean))]
  return ids.map((id) => ({ value: id, label: toolById(id)?.name || id }))
})
const filteredTasks = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return tasks.value.filter((task) => {
    if (statusFilter.value !== 'all' && task.status !== statusFilter.value) return false
    if (toolFilter.value !== 'all' && task.tool !== toolFilter.value) return false
    if (!keyword) return true
    return `${task.label || ''} ${task.message || ''} ${task.output || ''} ${task.method || ''}`.toLowerCase().includes(keyword)
  })
})
const pagedTasks = computed(() => {
  const offset = (page.value - 1) * pageSize.value
  return filteredTasks.value.slice(offset, offset + pageSize.value)
})
const selectedTasks = computed(() => tasks.value.filter((task) => selectedIds.value.includes(task.id)))
const selectedActive = computed(() => selectedTasks.value.filter((task) => ['queued', 'running'].includes(task.status)))
const selectedRetryable = computed(() => selectedTasks.value.filter((task) => ['failed', 'interrupted', 'canceled'].includes(task.status) && task.retryable !== false))
const allVisibleSelected = computed(() => pagedTasks.value.length > 0 && pagedTasks.value.every((task) => selectedIds.value.includes(task.id)))

const statusMeta = {
  queued: { label: '排队中', type: 'info', icon: Clock },
  running: { label: '处理中', type: 'primary', icon: Loading },
  success: { label: '已完成', type: 'success', icon: CircleCheck },
  failed: { label: '失败', type: 'danger', icon: CircleClose },
  interrupted: { label: '已中断', type: 'warning', icon: WarningFilled },
  canceled: { label: '已取消', type: 'info', icon: CircleClose }
}

const formatTime = (value) => {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value))
}
const duration = (task) => {
  if (!task.startedAt) return '尚未开始'
  if (!task.endedAt) return task.status === 'queued' ? '等待执行' : '进行中'
  const seconds = Math.max(0, Math.round((task.endedAt - task.startedAt) / 1000))
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}
const formatAverage = (value) => {
  const seconds = Math.max(0, Number(value || 0))
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} 秒`
  return `${Math.floor(seconds / 60)} 分 ${Math.round(seconds % 60)} 秒`
}

const refreshTasks = async (notify = false) => {
  if (refreshing.value) return
  refreshing.value = true
  try {
    const result = await callApi('task_list', { limit: 200 })
    if (result.ok) {
      hydrateBackendTasks(result.data.tasks || [], result.data.paused)
      backendStats.value = result.data.stats || null
      const knownIds = new Set(tasks.value.map((task) => task.id))
      selectedIds.value = selectedIds.value.filter((id) => knownIds.has(id))
      if (notify) ElMessage.success('任务状态已刷新')
    }
  } catch {
    // 旧版后端仍可使用前端本地任务记录。
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  refreshTasks()
  refreshTimer = window.setInterval(() => refreshTasks(), 1200)
})
onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})

watch([query, statusFilter, toolFilter, pageSize], () => {
  page.value = 1
})
watch(
  () => filteredTasks.value.length,
  (total) => {
    page.value = Math.min(page.value, Math.max(1, Math.ceil(total / pageSize.value)))
  }
)

const openTask = (task) => emit('open', { tool: task.tool, feature: task.feature })
const openOutput = async (task) => {
  if (!task.output) return
  const result = await callApi('system_pyOpenFile', task.output)
  if (!result.ok) ElMessage.error(result.message || '无法打开输出')
}
const cancelTask = async (task) => {
  const result = await callApi('task_cancel', { id: task.id })
  if (result.ok) {
    ElMessage.success(result.message || '已请求取消')
    await refreshTasks()
  } else ElMessage.error(result.message || '取消失败')
}
const retryTask = async (task) => {
  const result = await callApi('task_retry', { id: task.id })
  if (result.ok) {
    ElMessage.success('任务已重新加入队列')
    await refreshTasks()
  } else ElMessage.error(result.message || '重试失败')
}
const toggleTaskSelection = (task, checked) => {
  selectedIds.value = checked ? [...new Set([...selectedIds.value, task.id])] : selectedIds.value.filter((id) => id !== task.id)
}
const toggleVisibleSelection = (checked) => {
  const visibleIds = pagedTasks.value.map((task) => task.id)
  selectedIds.value = checked ? [...new Set([...selectedIds.value, ...visibleIds])] : selectedIds.value.filter((id) => !visibleIds.includes(id))
}
const runBatchAction = async (action) => {
  const candidates = action === 'cancel' ? selectedActive.value : selectedRetryable.value
  if (!candidates.length) return ElMessage.warning(action === 'cancel' ? '所选任务中没有活动任务' : '所选任务中没有可重试任务')
  const label = action === 'cancel' ? '取消' : '重试'
  try {
    await ElMessageBox.confirm(`将批量${label} ${candidates.length} 个任务，是否继续？`, `批量${label}`, {
      confirmButtonText: `批量${label}`,
      cancelButtonText: '返回',
      type: action === 'cancel' ? 'warning' : 'info'
    })
  } catch {
    return
  }
  const method = action === 'cancel' ? 'task_batch_cancel' : 'task_batch_retry'
  const result = await callApi(method, { ids: candidates.map((task) => task.id) })
  if (!result.ok) return ElMessage.error(result.message || `批量${label}失败`)
  if (result.data.failed) ElMessage.warning(result.message)
  else ElMessage.success(result.message)
  selectedIds.value = []
  await refreshTasks()
}
const toggleQueue = async () => {
  const result = await callApi(queuePaused.value ? 'task_queue_resume' : 'task_queue_pause')
  if (result.ok) {
    queuePaused.value = !queuePaused.value
    ElMessage.success(result.message)
    await refreshTasks()
  } else ElMessage.error(result.message || '操作失败')
}
const clearTasks = async () => {
  if (!tasks.value.length) return
  try {
    await ElMessageBox.confirm('将清除所有已完成、失败、中断和取消的任务记录；活动任务会保留。', '清除任务记录', { confirmButtonText: '清除记录', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  try {
    await callApi('task_clear')
  } catch {
    // 后端不可用时仍清理本地缓存。
  }
  clearFinishedTasks()
  selectedIds.value = []
  backendStats.value = null
}
const exportTasks = () => {
  const payload = { exportedAt: new Date().toISOString(), version: 1, tasks: tasks.value }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `ppx-tasks-${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(link.href)
}
</script>

<template>
  <div class="task-page">
    <header class="page-head">
      <div>
        <span class="eyebrow">V2.4 任务洞察</span>
        <h1>任务中心</h1>
        <p>队列、进度与结果保存在本机；可批量处理异常任务，并用成功率和耗时快速发现瓶颈。</p>
      </div>
      <div class="head-actions">
        <el-button :type="queuePaused ? 'success' : 'warning'" plain @click="toggleQueue"
          ><el-icon><VideoPlay v-if="queuePaused" /><VideoPause v-else /></el-icon>{{ queuePaused ? '继续队列' : '暂停队列' }}</el-button
        >
        <el-button :loading="refreshing" @click="refreshTasks(true)"
          ><el-icon><RefreshRight /></el-icon>刷新</el-button
        >
        <el-button :disabled="!tasks.length" @click="exportTasks"
          ><el-icon><Download /></el-icon>导出</el-button
        >
        <el-button :disabled="!tasks.length" @click="clearTasks">清理</el-button>
      </div>
    </header>

    <section class="stats" aria-label="任务统计">
      <div class="stat-card">
        <el-icon><Loading /></el-icon>
        <div>
          <b>{{ taskStats.active }}</b
          ><span>排队或处理中</span>
        </div>
      </div>
      <div class="stat-card success">
        <el-icon><CircleCheck /></el-icon>
        <div>
          <b>{{ taskStats.successRate }}%</b><span>任务成功率</span>
        </div>
      </div>
      <div class="stat-card">
        <el-icon><Clock /></el-icon>
        <div>
          <b>{{ formatAverage(taskStats.averageDurationSeconds) }}</b
          ><span>平均处理耗时</span>
        </div>
      </div>
      <div class="stat-card danger">
        <el-icon><WarningFilled /></el-icon>
        <div>
          <b>{{ taskStats.attention }}</b
          ><span>需要关注</span>
        </div>
      </div>
    </section>

    <section class="filters">
      <el-input v-model="query" clearable placeholder="搜索任务、输出路径或错误信息"
        ><template #prefix
          ><el-icon><Search /></el-icon></template
      ></el-input>
      <el-select v-model="statusFilter" style="width: 150px"><el-option label="全部状态" value="all" /><el-option v-for="(meta, key) in statusMeta" :key="key" :label="meta.label" :value="key" /></el-select>
      <el-select v-model="toolFilter" style="width: 170px"><el-option label="全部工具" value="all" /><el-option v-for="item in toolOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select>
    </section>

    <section class="batch-bar">
      <el-checkbox :model-value="allVisibleSelected" @change="toggleVisibleSelection">选择本页</el-checkbox>
      <span>已选 {{ selectedIds.length }} 项</span>
      <el-button size="small" :disabled="!selectedActive.length" @click="runBatchAction('cancel')">批量取消（{{ selectedActive.length }}）</el-button>
      <el-button size="small" type="primary" plain :disabled="!selectedRetryable.length" @click="runBatchAction('retry')">批量重试（{{ selectedRetryable.length }}）</el-button>
      <el-button v-if="selectedIds.length" size="small" text @click="selectedIds = []">取消选择</el-button>
    </section>

    <section class="task-list" aria-live="polite">
      <el-empty v-if="!pagedTasks.length" :description="tasks.length ? '没有符合筛选条件的任务' : '完成一次文件处理后，任务会显示在这里'"><el-button type="primary" @click="emit('open', 'home')">返回首页选择任务</el-button></el-empty>
      <article v-for="task in pagedTasks" v-else :key="task.id" class="task-card" :class="{ selected: selectedIds.includes(task.id) }">
        <el-checkbox :model-value="selectedIds.includes(task.id)" :aria-label="`选择任务 ${task.label}`" @change="toggleTaskSelection(task, $event)" />
        <div class="status-icon" :class="task.status">
          <el-icon><component :is="statusMeta[task.status]?.icon || Clock" /></el-icon>
        </div>
        <div class="task-main">
          <div class="task-title-row">
            <h3>{{ task.label }}</h3>
            <el-tag :type="statusMeta[task.status]?.type || 'info'" effect="plain" size="small">{{ statusMeta[task.status]?.label || task.status }}</el-tag>
          </div>
          <p class="task-meta">{{ toolById(task.tool)?.name || task.tool }} · {{ featureById(task.tool, task.feature)?.label || task.feature }} · {{ formatTime(task.startedAt) }} · {{ duration(task) }}</p>
          <p class="task-message">{{ task.message }}</p>
          <el-progress v-if="['queued', 'running'].includes(task.status)" :percentage="Number(task.progress || 0)" :stroke-width="5" :show-text="false" class="task-progress" />
          <p v-if="task.output" class="task-output" :title="task.output">{{ task.output }}</p>
        </div>
        <div class="task-actions">
          <el-button v-if="task.output" text type="primary" @click="openOutput(task)"
            ><el-icon><FolderOpened /></el-icon>打开输出</el-button
          >
          <el-button v-if="['queued', 'running'].includes(task.status)" text type="danger" @click="cancelTask(task)">取消</el-button>
          <el-button v-else-if="['failed', 'interrupted', 'canceled'].includes(task.status) && task.retryable !== false" text type="primary" @click="retryTask(task)"
            ><el-icon><RefreshRight /></el-icon>重试</el-button
          >
          <el-button text @click="openTask(task)"
            ><el-icon><RefreshRight /></el-icon>打开工具</el-button
          >
        </div>
      </article>
    </section>
    <div v-if="filteredTasks.length > pageSize" class="pagination-wrap">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="filteredTasks.length" />
    </div>
  </div>
</template>

<style scoped>
.task-page {
  height: 100%;
  overflow-y: auto;
  padding: 32px clamp(22px, 4vw, 46px) 48px;
  box-sizing: border-box;
}
.page-head {
  max-width: 1080px;
  margin: 0 auto 22px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.head-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
}
.eyebrow {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
h1 {
  margin: 5px 0 7px;
  color: var(--ppx-text-primary);
  font-size: 30px;
}
.page-head p {
  max-width: 650px;
  margin: 0;
  color: var(--ppx-text-muted);
}
.stats {
  max-width: 1080px;
  margin: 0 auto 14px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-surface);
  color: var(--accent);
}
.stat-card.success {
  color: var(--el-color-success);
}
.stat-card.danger {
  color: var(--el-color-danger);
}
.stat-card > .el-icon {
  font-size: 22px;
}
.stat-card div {
  display: flex;
  flex-direction: column;
}
.stat-card b {
  color: var(--ppx-text-primary);
  font-size: 22px;
  line-height: 1;
}
.stat-card span {
  margin-top: 5px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.filters {
  max-width: 1080px;
  margin: 0 auto 14px;
  display: flex;
  gap: 10px;
}
.filters .el-input {
  flex: 1;
}
.batch-bar {
  max-width: 1080px;
  min-height: 36px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.task-list {
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.task-card {
  display: grid;
  grid-template-columns: 24px 42px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-surface);
}
.task-card.selected {
  border-color: color-mix(in srgb, var(--accent) 60%, var(--ppx-glass-border));
  background: color-mix(in srgb, var(--accent) 6%, var(--ppx-bg-surface));
}
.status-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--ppx-bg-active);
  color: var(--accent);
}
.status-icon.success {
  color: var(--el-color-success);
}
.status-icon.failed {
  color: var(--el-color-danger);
}
.status-icon.interrupted {
  color: var(--el-color-warning);
}
.status-icon.running .el-icon {
  animation: spin 1.2s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
.task-main {
  min-width: 0;
}
.task-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.task-title-row h3 {
  margin: 0;
  color: var(--ppx-text-primary);
  font-size: 15px;
}
.task-meta,
.task-message,
.task-output {
  margin: 4px 0 0;
  font-size: 12px;
}
.task-meta {
  color: var(--ppx-text-muted);
}
.task-message {
  color: var(--ppx-text-secondary);
}
.task-progress {
  margin-top: 8px;
}
.task-output {
  overflow: hidden;
  color: var(--accent);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.pagination-wrap {
  max-width: 1080px;
  margin: 18px auto 0;
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 900px) {
  .page-head {
    flex-direction: column;
  }
  .head-actions {
    justify-content: flex-start;
  }
  .stats {
    grid-template-columns: 1fr;
  }
  .task-card {
    grid-template-columns: 24px 40px minmax(0, 1fr);
  }
  .task-actions {
    grid-column: 3;
    justify-content: flex-start;
  }
  .filters {
    flex-direction: column;
  }
  .filters .el-select {
    width: 100% !important;
  }
  .pagination-wrap {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
