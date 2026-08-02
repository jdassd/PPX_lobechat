<template>
  <div>
    <el-alert title="v2.0 将启动项改为只读诊断" description="这里不会新增、删除或运行任意启动命令。需要修改时，请进入 Windows 系统设置或任务管理器。" type="info" :closable="false" show-icon />

    <div class="toolbar">
      <span>检测到 {{ startupRules.length }} 个系统启动项</span>
      <el-button :loading="loading" @click="loadStartupRules">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="startupRules" size="small" border class="startup-table" empty-text="未检测到系统启动项">
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="command" label="路径 / 命令（只读）" min-width="280" show-overflow-tooltip />
      <el-table-column prop="description" label="来源" min-width="150" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default><el-tag size="small" type="info" effect="plain">系统项</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }"><el-button size="small" text type="primary" @click="openStartupLocation(row)">打开位置</el-button></template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { callApi as pyCall } from '@/utils/pyapi'

const props = defineProps({
  apiReady: { type: Boolean, default: false },
  visible: { type: Boolean, default: false }
})

const startupRules = ref([])
const loading = ref(false)

const loadStartupRules = async () => {
  if (!props.apiReady || !window.pywebview?.api?.system_listStartupRules) return
  loading.value = true
  try {
    const response = await pyCall('system_listStartupRules')
    if (response.ok) startupRules.value = response.data?.rules || []
    else ElMessage.error(response.message || '获取启动项失败')
  } catch (error) {
    ElMessage.error(error?.message || '获取启动项失败')
  } finally {
    loading.value = false
  }
}

const openStartupLocation = async (row) => {
  const response = await pyCall('system_openStartupLocation', {
    source: row.source,
    regKey: row.regKey,
    filePath: row.filePath
  })
  if (!response.ok) ElMessage.error(response.message || '打开位置失败')
}

const loadWhenVisible = () => {
  if (props.visible && props.apiReady) loadStartupRules()
}

onMounted(loadWhenVisible)
watch(() => props.visible, loadWhenVisible)
watch(() => props.apiReady, loadWhenVisible)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 14px 0 10px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.startup-table {
  margin-top: 6px;
}
</style>
