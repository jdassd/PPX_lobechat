<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useDraft } from '../../../utils/workspace'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'
import ResultActions from '../../shared/ResultActions.vue'

const state = useDraft('file/parts/DedupPanel/state', { directory: '', extensions: '', recursive: true, mode: 'content', limit: 5000, outputDir: '' })
// Old drafts stored scan output. A persisted form must not present it as a fresh scan.
delete state.result
delete state.summary
const loading = ref(false)
const exporting = ref(false)
const picking = ref(false)
const busy = computed(() => loading.value || exporting.value || picking.value)
const result = ref(null)
const report = ref(null)
const error = ref('')
const page = ref(1)
const activeGroup = computed(() => result.value?.groups[page.value - 1])
const filePage = ref(1)
const visibleFiles = computed(() => activeGroup.value?.files.slice((filePage.value - 1) * 20, filePage.value * 20) || [])
let revision = 0
let disposed = false
watch(
  () => [state.directory, state.extensions, state.recursive, state.mode, state.limit],
  () => {
    revision += 1
    result.value = null
    report.value = null
    error.value = ''
    page.value = 1
  },
  { flush: 'sync' }
)
watch(page, () => {
  filePage.value = 1
})
watch(
  () => state.outputDir,
  () => {
    report.value = null
  }
)
onBeforeUnmount(() => {
  disposed = true
  revision += 1
})
const ready = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const chooseDir = async (field) => {
  if (busy.value || !ready()) return
  picking.value = true
  const current = revision
  try {
    const directory = await callApiRaw('system_pySelectDirDialog', state[field])
    if (!disposed && current === revision && directory) state[field] = directory
  } catch (failure) {
    if (!disposed) error.value = failure.message || '目录选择失败'
  } finally {
    if (!disposed) picking.value = false
  }
}
const run = async () => {
  if (busy.value || !ready()) return
  if (!state.directory) {
    ElMessage.warning('请选择扫描目录')
    return
  }
  const current = revision
  loading.value = true
  result.value = null
  report.value = null
  error.value = ''
  page.value = 1
  filePage.value = 1
  try {
    const response = await pyCall('file_deduplicate', {
      directory: state.directory,
      extensions: state.extensions
        .split(/[,，]/)
        .map((value) => value.trim().replace(/^\./, ''))
        .filter(Boolean),
      recursive: state.recursive,
      mode: state.mode,
      limit: state.limit
    })
    if (disposed || current !== revision) return
    if (response.ok) result.value = response.data
    else error.value = response.message || '扫描未完成'
  } catch (failure) {
    if (!disposed && current === revision) error.value = failure.message || '扫描失败'
  } finally {
    if (!disposed) loading.value = false
  }
}
const exportReport = async () => {
  if (busy.value || !result.value || !ready()) return
  if (!state.outputDir) {
    ElMessage.warning('请选择报告输出目录')
    return
  }
  const current = revision
  exporting.value = true
  error.value = ''
  try {
    const response = await pyCall('file_deduplicate_report', { groups: result.value.groups, summary: result.value.summary, outputDir: state.outputDir })
    if (disposed || current !== revision) return
    if (response.ok) report.value = response.data
    else error.value = response.message || '报告导出失败'
  } catch (failure) {
    if (!disposed && current === revision) error.value = failure.message || '报告导出失败'
  } finally {
    if (!disposed) exporting.value = false
  }
}
const openFile = async (path) => {
  try {
    const response = await pyCall('system_pyOpenFile', path)
    if (!response.ok) ElMessage.error(response.message || '文件已移动或无法打开')
  } catch (failure) {
    ElMessage.error(failure.message || '文件无法打开')
  }
}
const displayPath = (file) => {
  const root =
    String(result.value?.summary?.directory || '')
      .replace(/\\/g, '/')
      .replace(/\/$/, '') + '/'
  const path = file.replace(/\\/g, '/')
  return path.startsWith(root) ? path.slice(root.length) : file
}
</script>

<template>
  <section class="panel dedup-panel">
    <header>
      <h4>重复文件审查</h4>
      <p>先核对候选，再导出报告。扫描和导出都保留来源文件。</p>
    </header>
    <el-form :model="state" label-width="120px" :disabled="busy">
      <el-form-item label="扫描目录"
        ><div class="field-row"><el-input v-model="state.directory" readonly placeholder="选择要检查的目录" /><el-button @click="chooseDir('directory')">选择目录</el-button></div></el-form-item
      >
      <el-form-item label="扩展名"><el-input v-model="state.extensions" placeholder="逗号分隔；留空检查全部普通文件" /></el-form-item>
      <el-form-item label="比较方式"
        ><el-radio-group v-model="state.mode"><el-radio-button value="content">比较内容</el-radio-button><el-radio-button value="name">同名候选</el-radio-button></el-radio-group></el-form-item
      >
      <el-form-item label="最多扫描文件"><el-input-number :key="busy ? 'locked' : 'open'" v-model="state.limit" :disabled="busy" :min="100" :max="20000" :precision="0" /></el-form-item>
      <el-form-item><el-checkbox v-model="state.recursive">包含子目录</el-checkbox></el-form-item>
      <el-form-item><el-button type="primary" :loading="loading" @click="run">开始扫描</el-button><small v-if="loading">可在任务中心查看进度或取消</small></el-form-item>
    </el-form>
    <p class="scope-note">{{ state.mode === 'name' ? '同名仅表示文件名相同，未比较内容，不估算重复体积。' : '先按大小筛选，再比较 SHA-256；内容比较最多 60 秒。体积为重复逻辑字节，不代表磁盘实际可释放空间。' }} 不跟随链接，跳过 PPX 回收和历史目录。</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="result">
      <el-alert v-if="result.partial" title="扫描不完整" :description="result.truncated ? '达到文件数量上限，请缩小扫描范围；当前仅显示已确认候选。' : '部分文件未完成比较，请查看原因。当前仅显示已确认候选。'" type="warning" :closable="false" show-icon />
      <div class="dedup-summary">
        <strong>{{ result.complete ? '扫描完整' : '扫描不完整' }} · {{ result.totalGroups }} 组{{ result.mode === 'name' ? '同名候选' : '相同内容' }}</strong
        ><span>已扫描 {{ result.scanned }} 份 · 已比较内容 {{ result.hashedFiles }} 份</span><span v-if="result.mode === 'content'">重复逻辑体积 {{ result.spaceSaved }} · 硬链接别名 {{ result.hardLinkAliases }} 份</span>
      </div>
      <details v-if="result.errorCount" class="scan-errors">
        <summary>查看 {{ result.errorCount }} 项原因（最多显示 20 项）</summary>
        <ul>
          <li v-for="(issue, index) in result.errors" :key="index">{{ issue.path }}：{{ issue.message }}</li>
        </ul>
      </details>
      <section v-if="activeGroup" class="duplicate-group" aria-label="候选分组">
        <div class="group-heading">
          <strong>第 {{ page }} 组 · {{ activeGroup.count }} 份文件</strong><span>{{ result.mode === 'content' ? '内容相同' : '仅名称相同' }}</span>
        </div>
        <ul class="duplicate-files">
          <li v-for="file in visibleFiles" :key="file">
            <button type="button" :title="file" :aria-label="file" @click="openFile(file)">{{ displayPath(file) }}</button>
          </li>
        </ul>
        <el-pagination v-if="activeGroup.files.length > 20" v-model:current-page="filePage" :page-size="20" :total="activeGroup.files.length" layout="prev, pager, next" small aria-label="组内文件分页" />
        <el-pagination v-if="result.groups.length > 1" v-model:current-page="page" :page-size="1" :total="result.groups.length" layout="prev, pager, next" small aria-label="候选分组分页" />
      </section>
      <el-empty v-else :description="result.complete ? '当前范围内未发现重复候选' : '当前未确认重复候选，请先处理未完成原因'" :image-size="60" />
      <section class="report-section" aria-label="导出核对报告">
        <h4>保留这次核对记录</h4>
        <p>报告保留扫描时间、范围、完整性和逐文件路径。导出时不重新扫描；不完整结果会在报告中明确标注。</p>
        <div class="field-row"><el-input v-model="state.outputDir" readonly placeholder="选择报告输出目录" /><el-button :disabled="busy" @click="chooseDir('outputDir')">选择报告目录</el-button><el-button type="primary" :disabled="busy" :loading="exporting" @click="exportReport">导出 Excel 报告</el-button></div>
        <ResultActions v-if="report?.outputAssets?.length" :assets="report.outputAssets" />
      </section>
    </template>
  </section>
</template>

<style scoped>
.dedup-panel .field-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}
.dedup-panel .field-row > .el-input {
  flex: 1;
  min-width: 140px;
}
.scope-note,
small,
.report-section p,
.group-heading span {
  color: var(--ppx-text-muted);
  font-size: 12px;
  line-height: 1.6;
}
small {
  margin-left: 12px;
}
.dedup-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 18px 0;
  font-size: 13px;
}
.duplicate-group,
.report-section {
  padding: 16px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  margin-top: 16px;
}
.group-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.duplicate-files {
  list-style: none;
  padding: 0;
  margin: 12px 0;
  max-height: 280px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
.duplicate-files button {
  color: var(--ppx-neon-blue);
  text-align: left;
  background: none;
  border: 0;
  padding: 6px 0;
  cursor: pointer;
  overflow-wrap: anywhere;
  font: inherit;
  font-size: 12px;
}
.duplicate-files button:focus-visible {
  outline: 2px solid var(--ppx-neon-blue);
  outline-offset: 3px;
}
.scan-errors {
  margin: 12px 0;
  overflow-wrap: anywhere;
}
.scan-errors summary {
  cursor: pointer;
}
.report-section h4 {
  margin: 0;
}
.dedup-panel :deep(.el-pagination) {
  margin-top: 10px;
  flex-wrap: wrap;
}
</style>
