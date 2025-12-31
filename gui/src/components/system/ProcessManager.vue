<script setup>
import { computed, reactive, ref, watch, onMounted, onUnmounted } from 'vue'
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

const windowSize = reactive({ width: 0, height: 0 })

const dialogWidth = computed(() => {
  if (windowSize.width < 480) return '95%'
  if (windowSize.width < 768) return '90%'
  if (windowSize.width < 1024) return '85%'
  if (windowSize.width < 1200) return '800px'
  return '960px'
})

const tableHeight = computed(() => {
  if (windowSize.height < 600) return 250
  if (windowSize.height < 768) return 300
  if (windowSize.height < 1000) return 350
  return 420
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

const filters = reactive({
  keyword: '',
  port: '',
  limit: 200
})

const limitOptions = [50, 100, 200, 500]
const processRows = ref([])
const loading = ref(false)
const stats = reactive({ total: 0, hasMore: false })
const lastError = ref('')
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

const normalizePort = (value) => {
  const digits = String(value ?? '').replace(/[^\d]/g, '')
  return digits.slice(0, 5)
}

const buildPayload = () => {
  const payload = {
    limit: filters.limit
  }
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
  if (!apiReady.value) {
    lastError.value = '仅能在桌面客户端内使用进程管理'
    processRows.value = []
    return
  }
  if (!window.pywebview?.api?.system_listProcesses) {
    lastError.value = '当前客户端未暴露 system_listProcesses 接口'
    processRows.value = []
    return
  }
  loading.value = true
  lastError.value = ''
  try {
    const res = await window.pywebview.api.system_listProcesses(buildPayload())
    if (res?.success) {
      processRows.value = Array.isArray(res.items) ? res.items : []
      stats.total = typeof res.total === 'number' ? res.total : processRows.value.length
      stats.hasMore = !!res.hasMore
    } else {
      const message = res?.message || '获取进程列表失败'
      lastError.value = message
      ElMessage.error(message)
    }
  } catch (error) {
    const message = error?.message || '获取进程列表失败'
    lastError.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  fetchProcesses()
}

const handleReset = () => {
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
  try {
    const res = await window.pywebview.api.system_killProcess(row.pid)
    if (res?.success) {
      ElMessage.success(`已结束 PID ${row.pid}`)
      fetchProcesses()
    } else {
      ElMessage.error(res?.message || '结束进程失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '结束进程失败')
  }
}

watch(
  () => visible.value,
  (show) => {
    if (show && apiReady.value) {
      fetchProcesses()
    }
  }
)

watch(
  () => apiReady.value,
  (ready) => {
    if (ready && visible.value) {
      fetchProcesses()
    }
  }
)

watch(
  () => filters.limit,
  () => {
    if (visible.value) {
      fetchProcesses()
    }
  }
)

const summaryText = computed(() => {
  if (!stats.total) {
    return '暂无进程数据'
  }
  if (stats.hasMore) {
    return `已展示 ${processRows.value.length}/${stats.total} 条，建议进一步筛选`
  }
  return `共 ${stats.total} 条记录`
})
</script>

<template>
  <el-dialog
    v-model="visible"
    class="process-manager"
    :width="dialogWidth"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <template #title>
      <div class="dialog-title">
        <span>进程管理</span>
        <small>按名称或端口检索，可直接强制结束</small>
      </div>
    </template>
    <div class="toolbar">
      <el-input
        v-model.trim="filters.keyword"
        placeholder="进程名称 / 命令关键字"
        clearable
        class="keyword-input"
        @keyup.enter="handleSearch"
      />
      <el-input
        v-model="filters.port"
        placeholder="端口"
        clearable
        class="port-input"
        maxlength="5"
        @keyup.enter="handleSearch"
      />
      <el-select v-model="filters.limit" class="limit-select">
        <el-option v-for="count in limitOptions" :key="count" :label="`最多 ${count} 条`" :value="count" />
      </el-select>
      <el-button type="primary" @click="handleSearch">检索</el-button>
      <el-button @click="handleReset">重置</el-button>
    </div>
    <el-alert v-if="!apiReady" type="warning" show-icon class="helper-hint">
      请在桌面客户端内使用，浏览器预览无法访问本地进程信息。
    </el-alert>
    <el-alert v-else-if="lastError" type="error" show-icon class="helper-hint">
      {{ lastError }}
    </el-alert>
    <el-table
      :data="processRows"
      row-key="pid"
      :height="tableHeight"
      border
      v-loading="loading"
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
      <span>{{ summaryText }}</span>
      <el-button text type="primary" @click="fetchProcesses">刷新</el-button>
    </div>
  </el-dialog>
</template>

<style scoped>
/* 使用全局深空玻璃主题样式 */

.process-manager :deep(.el-dialog__body) {
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

.helper-hint {
  margin-bottom: 12px;
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

/* 响应式布局 */
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

  :deep(.el-table-column--selection .el-table__cell) {
    padding: 8px 2px;
  }
}

@media (max-width: 768px) {
  .port-input {
    width: 100px;
  }

  .limit-select {
    width: 120px;
  }

  :deep(.el-table) {
    font-size: 12px;
  }
}
</style>
