<script setup>
import { computed, ref, watch } from 'vue'
import { callApi } from '@/utils/pyapi'
import { TASK_METHODS } from '@/utils/taskCenter'
import ResultActions from './ResultActions.vue'

const props = defineProps({ task: { type: Object, required: true } })
const opened = ref(false)
const trail = ref([])
const pendingId = ref('')
const error = ref('')
const page = ref(1)
const pageSize = 12
let revision = 0
const current = computed(() => trail.value.at(-1) || props.task)
const origins = computed(() => current.value.inputOrigins || [])
const visibleOrigins = computed(() => origins.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const available = computed(() => props.task.inputOrigins?.length || props.task.inputOriginWarnings?.length || props.task.retryOf)
const methodLabel = (method) => TASK_METHODS[method]?.[2] || method || '历史任务'
const filename = (path) =>
  String(path || '')
    .split(/[\\/]/)
    .pop()
const statusLabel = (status) => ({ success: '已完成', partial: '部分成功', failed: '失败', canceled: '已取消', interrupted: '已中断', queued: '排队中', running: '处理中', canceling: '取消中' })[status] || status
const formatTime = (value) => {
  const number = Number(value)
  if (!Number.isFinite(number) || number <= 0) return '时间未记录'
  return new Date(number < 10_000_000_000 ? number * 1000 : number).toLocaleString('zh-CN')
}
watch(
  () => current.value.id,
  () => {
    page.value = 1
    error.value = ''
  }
)
watch(opened, () => {
  revision += 1
  trail.value = []
  pendingId.value = ''
  error.value = ''
  page.value = 1
})
const openRelated = async (id) => {
  if (!id) return
  if ([props.task.id, ...trail.value.map((task) => task.id)].includes(id)) {
    error.value = '该记录已在当前来源路径中，请使用返回按钮查看。'
    return
  }
  const request = ++revision
  pendingId.value = id
  error.value = ''
  try {
    const result = await callApi('task_get', { id })
    if (request !== revision || !opened.value) return
    if (!result.ok || !result.data.task) throw new Error('来源记录已清理或暂时不可用，当前任务与输出文件仍保留。')
    trail.value.push(result.data.task)
  } catch (cause) {
    if (request === revision && opened.value) error.value = cause.message || '无法读取来源任务，请稍后重试。'
  } finally {
    if (request === revision) pendingId.value = ''
  }
}
const back = () => {
  revision += 1
  pendingId.value = ''
  trail.value.pop()
}
</script>

<template>
  <el-button v-if="available" class="task-origins-button" size="small" text @click="opened = true">输入来源{{ task.inputOrigins?.length ? `（${task.inputOrigins.length}）` : '' }}</el-button>
  <el-dialog v-model="opened" title="输入来源" width="min(820px, 94vw)" top="5vh" append-to-body class="ppx-origins-dialog">
    <header class="origin-task">
      <el-button v-if="trail.length" size="small" plain @click="back">返回上一任务</el-button>
      <div>
        <h3>{{ methodLabel(current.method) }}</h3>
        <p>{{ statusLabel(current.status) }} · {{ formatTime(current.createdAt || current.startedAt) }}</p>
        <small>任务 {{ current.id }}</small>
      </div>
    </header>
    <p class="origin-note">记录明确接收后使用的主文件路径；不校验文件内容是否被外部修改。</p>
    <el-alert v-if="error" :title="error" type="warning" :closable="false" show-icon class="origin-error" />
    <el-alert v-if="current.inputOriginWarnings?.length" :title="current.inputOriginWarnings.join('；')" type="warning" :closable="false" show-icon class="origin-error" />
    <div v-if="current.retryOf" class="retry-origin">
      <span>这是一次重试，原任务：</span><code>{{ current.retryOf }}</code>
      <el-button size="small" text type="primary" :loading="pendingId === current.retryOf" @click="openRelated(current.retryOf)">查看原任务</el-button>
    </div>
    <ol v-if="origins.length" class="origin-list">
      <li v-for="(origin, index) in visibleOrigins" :key="`${origin.sourceTaskId}:${origin.inputPath}`" class="origin-item">
        <span class="origin-number">{{ (page - 1) * pageSize + index + 1 }}</span>
        <div class="origin-file">
          <strong>{{ filename(origin.inputPath) }}</strong>
          <small class="origin-path">{{ origin.inputPath }}</small>
          <p>来自 {{ methodLabel(origin.sourceMethod) }} · {{ formatTime(origin.sourceCreatedAt) }}</p>
          <small class="origin-id">任务 {{ origin.sourceTaskId }}</small>
          <span v-if="origin.sourceAvailable === false" class="missing-source">来源记录已清理，文件使用关系仍保留</span>
        </div>
        <el-button size="small" :disabled="origin.sourceAvailable === false" :loading="pendingId === origin.sourceTaskId" @click="openRelated(origin.sourceTaskId)">查看来源任务</el-button>
      </li>
    </ol>
    <el-empty v-else :image-size="44" description="未记录接力主输入来源" />
    <el-pagination v-if="origins.length > pageSize" v-model:current-page="page" :page-size="pageSize" :total="origins.length" layout="prev, pager, next, total" />
    <section v-if="trail.length" class="source-results">
      <p>{{ current.message }}</p>
      <ResultActions :assets="current.outputs || []" :source-task-id="current.id" @sent="opened = false" />
    </section>
    <template #footer><el-button @click="opened = false">关闭</el-button></template>
  </el-dialog>
</template>

<style scoped>
:global(.ppx-origins-dialog) {
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}
:global(.ppx-origins-dialog .el-dialog__body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
:global(.ppx-origins-dialog .el-dialog__header),
:global(.ppx-origins-dialog .el-dialog__footer) {
  flex-shrink: 0;
}
.task-origins-button {
  margin: 4px 0;
}
.origin-task {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.origin-task h3 {
  margin: 0 0 6px;
  font-size: 18px;
  color: var(--ppx-text-primary);
}
.origin-task p,
.origin-file p {
  margin: 4px 0;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}
.origin-task small,
.origin-id,
.origin-note {
  color: var(--ppx-text-muted);
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.origin-note {
  margin: 18px 0;
}
.origin-error {
  margin-bottom: 12px;
}
.origin-list {
  padding: 0;
  margin: 0;
  list-style: none;
}
.origin-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 0;
  border-top: 1px solid var(--ppx-glass-border);
}
.origin-number {
  color: var(--ppx-text-muted);
  font-size: 12px;
  min-width: 18px;
  padding-top: 3px;
}
.origin-file {
  flex: 1;
  min-width: 0;
}
.origin-file strong,
.origin-path,
.missing-source {
  display: block;
  overflow-wrap: anywhere;
  line-height: 1.6;
}
.origin-file strong {
  color: var(--ppx-text-primary);
}
.origin-path {
  color: var(--ppx-text-secondary);
  font-size: 12px;
  margin: 4px 0 8px;
}
.missing-source {
  color: var(--el-color-warning-dark-2);
  font-size: 12px;
  margin-top: 6px;
}
.retry-origin {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  background: var(--ppx-bg-base);
  padding: 10px 12px;
  margin-bottom: 16px;
  font-size: 12px;
}
.retry-origin code {
  overflow-wrap: anywhere;
}
.source-results {
  border-top: 1px solid var(--ppx-glass-border);
  margin-top: 16px;
  padding-top: 12px;
  color: var(--ppx-text-secondary);
  font-size: 13px;
}
@media (max-width: 640px) {
  .origin-item,
  .origin-task {
    flex-wrap: wrap;
  }
  .origin-file {
    flex-basis: calc(100% - 36px);
  }
  .origin-item > .el-button {
    margin-left: 32px;
  }
}
</style>
