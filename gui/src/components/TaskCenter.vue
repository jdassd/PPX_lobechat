<script setup>
import { computed } from 'vue'
import { CircleCheck, CircleClose, Clock, FolderOpened, Loading, RefreshRight, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { featureById, toolById } from '@/config/tools'
import { callApi } from '@/utils/pyapi'
import { clearFinishedTasks, runningTasks, tasks } from '@/utils/taskCenter'

const emit = defineEmits(['open'])

const completedCount = computed(() => tasks.value.filter((item) => item.status === 'success').length)
const failedCount = computed(() => tasks.value.filter((item) => ['failed', 'interrupted'].includes(item.status)).length)

const statusMeta = {
  running: { label: '处理中', type: 'primary', icon: Loading },
  success: { label: '已完成', type: 'success', icon: CircleCheck },
  failed: { label: '失败', type: 'danger', icon: CircleClose },
  interrupted: { label: '已中断', type: 'warning', icon: WarningFilled }
}

const formatTime = (value) => {
  if (!value) return ''
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value))
}

const duration = (task) => {
  if (!task.endedAt) return '进行中'
  const seconds = Math.max(0, Math.round((task.endedAt - task.startedAt) / 1000))
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

const openTask = (task) => emit('open', { tool: task.tool, feature: task.feature })

const openOutput = async (task) => {
  if (!task.output) return
  try {
    const res = await callApi('system_pyOpenFile', task.output)
    if (!res.ok) ElMessage.error(res.message || '无法打开输出')
  } catch (error) {
    ElMessage.error(error?.message || '无法打开输出')
  }
}

const clearTasks = async () => {
  if (!tasks.value.length) return
  try {
    await ElMessageBox.confirm('将清除所有已完成、失败和中断的任务记录；正在运行的任务会保留。', '清除任务记录', {
      confirmButtonText: '清除记录',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  clearFinishedTasks()
}
</script>

<template>
  <div class="task-page">
    <header class="page-head">
      <div>
        <span class="eyebrow">V2 工作流</span>
        <h1>任务中心</h1>
        <p>集中查看文件处理状态、输出位置与失败原因。任务信息仅保存在本机。</p>
      </div>
      <el-button :disabled="!tasks.length" @click="clearTasks">清除已结束记录</el-button>
    </header>

    <section class="stats" aria-label="任务统计">
      <div class="stat-card">
        <el-icon><Loading /></el-icon>
        <div>
          <b>{{ runningTasks.length }}</b
          ><span>处理中</span>
        </div>
      </div>
      <div class="stat-card success">
        <el-icon><CircleCheck /></el-icon>
        <div>
          <b>{{ completedCount }}</b
          ><span>已完成</span>
        </div>
      </div>
      <div class="stat-card danger">
        <el-icon><WarningFilled /></el-icon>
        <div>
          <b>{{ failedCount }}</b
          ><span>需要关注</span>
        </div>
      </div>
    </section>

    <section class="task-list" aria-live="polite">
      <el-empty v-if="!tasks.length" description="完成一次文件处理后，任务会显示在这里">
        <el-button type="primary" @click="emit('open', 'home')">返回首页选择任务</el-button>
      </el-empty>

      <article v-for="task in tasks" v-else :key="task.id" class="task-card">
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
          <p v-if="task.output" class="task-output" :title="task.output">{{ task.output }}</p>
        </div>
        <div class="task-actions">
          <el-button v-if="task.output" text type="primary" @click="openOutput(task)"
            ><el-icon><FolderOpened /></el-icon>打开输出</el-button
          >
          <el-button text @click="openTask(task)"
            ><el-icon><RefreshRight /></el-icon>再次打开</el-button
          >
        </div>
      </article>
    </section>
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
  max-width: 980px;
  margin: 0 auto 22px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
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
  margin: 0;
  color: var(--ppx-text-muted);
}
.stats {
  max-width: 980px;
  margin: 0 auto 18px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
.stat-card .el-icon {
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
.task-list {
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.task-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-surface);
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
.task-output {
  overflow: hidden;
  color: var(--accent);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-actions {
  display: flex;
  align-items: center;
}
@media (max-width: 840px) {
  .stats {
    grid-template-columns: 1fr;
  }
  .task-card {
    grid-template-columns: 40px minmax(0, 1fr);
  }
  .task-actions {
    grid-column: 2;
  }
}
</style>
