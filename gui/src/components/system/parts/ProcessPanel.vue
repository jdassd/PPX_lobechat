<template>
  <div>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi as pyCall } from '@/utils/pyapi'

const props = defineProps({
  apiReady: {
    type: Boolean,
    default: false
  },
  visible: {
    type: Boolean,
    default: false
  }
})

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
  if (!props.apiReady || !window.pywebview?.api?.system_listProcesses) {
    return
  }
  processLoading.value = true
  try {
    const { ok, data: res } = await pyCall('system_listProcesses', buildPayload())
    if (ok) {
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
  if (!props.apiReady || !window.pywebview?.api?.system_killProcess) {
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
  const { ok, data: res } = await pyCall('system_killProcess', row.pid)
  if (ok) {
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

// 等价复刻原父组件中两个 watch 的触发语义：
// 原父组件常驻挂载，靠 watch(visible) / watch(apiReady) 触发检索。
// 此处子面板位于 el-dialog 默认插槽内（destroy-on-close），每次打开会重新挂载，
// 因此「可见且就绪」的场景改由 onMounted 兜住（挂载时必然 visible=true）；
// 「先打开、apiReady 稍后就绪」的场景仍由 watch(apiReady) 覆盖；
// watch(visible) 保留以兼容面板未被销毁却切换可见态的边界情况。
onMounted(() => {
  if (props.visible && props.apiReady) {
    fetchProcesses()
  }
})

watch(
  () => props.visible,
  (show) => {
    if (show && props.apiReady) {
      fetchProcesses()
    }
  }
)

watch(
  () => props.apiReady,
  (ready) => {
    if (ready && props.visible) {
      fetchProcesses()
    }
  }
)
</script>

<style scoped>
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
