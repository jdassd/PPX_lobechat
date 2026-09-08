<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useDraft } from '../../../utils/workspace'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'
import ResultTable from '../../shared/ResultTable.vue'
import ResultActions from '../../shared/ResultActions.vue'

const state = useDraft('file/parts/SearchPanel/state', {
  directory: '',
  keyword: '',
  extensions: '',
  recursive: true,
  minSize: 0,
  maxSize: 0,
  limit: 500
})
const loading = ref(false)
const picking = ref(false)
const busy = computed(() => loading.value || picking.value)
const result = ref(null)
const error = ref('')
let revision = 0
let disposed = false
watch(
  () => [state.directory, state.keyword, state.extensions, state.recursive, state.minSize, state.maxSize, state.limit],
  () => {
    revision += 1
    result.value = null
    error.value = ''
  },
  { flush: 'sync' }
)
onBeforeUnmount(() => {
  disposed = true
  revision += 1
})

const ensurePyReady = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const selectDir = async () => {
  if (busy.value || !ensurePyReady()) return
  const current = revision
  picking.value = true
  try {
    const directory = await callApiRaw('system_pySelectDirDialog', state.directory)
    if (!disposed && current === revision && directory) state.directory = directory
  } catch (failure) {
    if (!disposed) error.value = failure.message || '目录选择失败'
  } finally {
    if (!disposed) picking.value = false
  }
}
const openDirectory = () => {
  if (ensurePyReady()) callApiRaw('system_pyOpenFile', state.directory)
}
const runSearch = async () => {
  if (busy.value || !ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  const current = revision
  const options = {
    directory: state.directory,
    keyword: state.keyword,
    extensions: state.extensions
      .split(/[,，]/)
      .map((item) => item.trim().replace(/^\./, ''))
      .filter(Boolean),
    recursive: state.recursive,
    minSize: state.minSize,
    maxSize: state.maxSize,
    limit: state.limit
  }
  loading.value = true
  result.value = null
  error.value = ''
  try {
    const response = await pyCall('file_search', options)
    if (disposed || current !== revision) return
    if (response.ok) result.value = response.data
    else error.value = response.message || '搜索失败'
  } catch (failure) {
    if (!disposed && current === revision) error.value = failure.message || '搜索失败'
  } finally {
    if (!disposed) loading.value = false
  }
}
</script>

<template>
  <section class="panel search-panel">
    <header>
      <h4>查找文件，再继续处理</h4>
      <p>按文件名包含匹配，不区分大小写；支持扩展名、大小和子目录筛选。</p>
    </header>
    <el-form :model="state" label-width="120px" :disabled="busy">
      <el-form-item label="搜索目录">
        <div class="field-row"><el-input v-model="state.directory" placeholder="选择要搜索的目录" readonly /><el-button :disabled="busy" :loading="picking" @click="selectDir">选择目录</el-button></div>
      </el-form-item>
      <el-form-item label="文件名包含"><el-input v-model="state.keyword" placeholder="按文字匹配，例如 报告[1]" clearable /></el-form-item>
      <el-form-item label="扩展名"><el-input v-model="state.extensions" placeholder="逗号分隔，例如 pdf,docx,xlsx；留空不限" /></el-form-item>
      <el-form-item label="大小（字节）">
        <div class="size-range">
          <el-input-number :key="busy ? 'min-locked' : 'min-open'" v-model="state.minSize" :disabled="busy" :min="0" :precision="0" aria-label="最小字节数" />
          <span>至</span>
          <el-input-number :key="busy ? 'max-locked' : 'max-open'" v-model="state.maxSize" :disabled="busy" :min="0" :precision="0" aria-label="最大字节数" />
          <small>0 表示不限</small>
        </div>
      </el-form-item>
      <el-form-item label="最多结果"><el-input-number :key="busy ? 'limit-locked' : 'limit-open'" v-model="state.limit" :disabled="busy" :min="50" :max="2000" :precision="0" /></el-form-item>
      <el-form-item><el-checkbox v-model="state.recursive">包含子目录</el-checkbox></el-form-item>
      <el-form-item><el-button type="primary" :loading="loading" :disabled="picking" @click="runSearch">开始搜索</el-button></el-form-item>
    </el-form>
    <p class="search-scope">仅搜索普通文件，不跟随链接；自动跳过 PPX 回收站和历史目录。搜索耗时或规模超限会说明未完成范围。</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <template v-if="result">
      <el-alert v-if="result.partial" :title="result.msg" description="请缩小范围后重新搜索，或仅处理下方已找到的文件。" type="warning" :closable="false" show-icon />
      <p class="search-summary">
        {{ result.complete ? '搜索完整' : '结果不完整' }} · 已找到 {{ result.items.length }} 个文件 <small>已检查 {{ result.scannedEntries }} 个条目，跳过 {{ result.skippedLinks }} 个链接</small>
      </p>
      <details v-if="result.errorCount" class="search-errors">
        <summary>查看 {{ result.errorCount }} 项未完成原因（最多显示 20 项）</summary>
        <ul>
          <li v-for="(issue, index) in result.errors" :key="index">{{ issue.path }}：{{ issue.message }}</li>
        </ul>
      </details>
      <ResultTable
        v-if="result.items.length"
        title="搜索结果"
        :items="result.items"
        :max-height="Math.min(340, result.items.length * 32 + 36)"
        :columns="[
          { label: '文件名', prop: 'name', width: 160 },
          { label: '相对路径', prop: 'relativePath' },
          { label: '大小', prop: 'sizeText', width: 100 }
        ]"
      >
        <template #actions><el-button text type="primary" @click="openDirectory">打开搜索目录</el-button></template>
      </ResultTable>
      <el-empty v-else :description="result.complete ? '未找到匹配文件，可调整关键词或扩展名' : '尚未返回文件，请查看未完成原因'" :image-size="70" />
      <ResultActions v-if="result.outputAssets?.length" :assets="result.outputAssets" />
    </template>
  </section>
</template>

<style scoped>
.search-scope,
small {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.search-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: baseline;
}
.search-errors {
  margin: 12px 0;
  overflow-wrap: anywhere;
}
.search-errors summary {
  cursor: pointer;
}
.search-panel :deep(.field-row) {
  flex-wrap: wrap;
}
.search-panel :deep(.field-row > .el-input) {
  flex: 1;
  min-width: 120px;
}
.size-range {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  width: 100%;
}
.size-range :deep(.el-input-number) {
  width: 100%;
  min-width: 0;
}
.size-range small {
  grid-column: 1 / -1;
}
</style>
