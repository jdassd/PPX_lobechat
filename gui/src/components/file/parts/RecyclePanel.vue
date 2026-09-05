<script setup>
import { useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { callApi, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)
const state = useDraft('file/parts/RecyclePanel/state', { directory: '', batches: [], olderThanDays: 30 })
const ready = () => {
  if (hasPyApi()) return true
  ElMessage.warning('该功能需在桌面客户端中使用')
  return false
}
const chooseDir = async () => {
  if (!ready()) return
  const dir = await callApiRaw('system_pySelectDirDialog', state.directory)
  if (dir) {
    state.directory = dir
    await loadBatches()
  }
}
const loadBatches = async () => {
  if (!state.directory) return
  loading.value = true
  try {
    const result = await callApi('file_recycle_list', { directory: state.directory })
    if (!result.ok) return ElMessage.error(result.message || '读取回收站失败')
    state.batches = (result.data.batches || []).map((item) => ({ ...item, createdText: new Date(Number(item.createdAt || 0) * 1000).toLocaleString(), filesText: (item.files || []).join('、') }))
  } finally {
    loading.value = false
  }
}
const restore = async (batch) => {
  try {
    await ElMessageBox.confirm(`恢复该批次的 ${batch.count} 个文件？名称冲突时会自动追加 restored 后缀。`, '恢复文件', { confirmButtonText: '恢复', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  const result = await callApi('file_recycle_restore', { directory: state.directory, id: batch.id, conflictPolicy: 'rename' })
  if (result.ok) {
    ElMessage.success(result.message || '恢复完成')
    await loadBatches()
  } else ElMessage.error(result.message || '恢复失败')
}
const purge = async (batch = null) => {
  const message = batch ? `永久清理该批次的 ${batch.count} 个回收文件？此操作不可撤销。` : `永久清理 ${state.olderThanDays} 天前的回收批次？此操作不可撤销。`
  try {
    await ElMessageBox.confirm(message, '永久清理', { confirmButtonText: '永久清理', cancelButtonText: '取消', type: 'error' })
  } catch {
    return
  }
  const result = await callApi('file_recycle_purge', { directory: state.directory, id: batch?.id || '', olderThanDays: batch ? 0 : state.olderThanDays })
  if (result.ok) {
    ElMessage.success(result.message || '清理完成')
    await loadBatches()
  } else ElMessage.error(result.message || '清理失败')
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>PPX 回收站</h4>
      <p>查看、恢复或按保留期清理安全删除的文件；恢复时不会覆盖现有文件</p>
    </header>
    <el-form :model="state" label-width="110px">
      <el-form-item label="原始目录"
        ><div class="field-row"><el-input v-model="state.directory" readonly placeholder="选择执行过安全删除的目录" /><el-button @click="chooseDir">选择</el-button><el-button :disabled="!state.directory" :loading="loading" @click="loadBatches">刷新</el-button></div></el-form-item
      >
      <el-form-item label="定期清理"
        ><div class="field-row compact"><el-input-number v-model="state.olderThanDays" :min="1" :max="3650" /><span>天前</span><el-button type="danger" plain :disabled="!state.directory" @click="purge()">清理过期批次</el-button></div></el-form-item
      >
    </el-form>
    <el-table v-loading="loading" :data="state.batches" border size="small" empty-text="该目录没有 PPX 回收批次">
      <el-table-column prop="createdText" label="删除时间" width="180" />
      <el-table-column prop="count" label="文件数" width="80" />
      <el-table-column prop="sizeText" label="大小" width="100" />
      <el-table-column prop="filesText" label="原路径" min-width="240" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right"
        ><template #default="scope"><el-button text type="primary" @click="restore(scope.row)">恢复</el-button><el-button text type="danger" @click="purge(scope.row)">清理</el-button></template></el-table-column
      >
    </el-table>
  </section>
</template>

<style scoped>
.compact {
  align-items: center;
}
.compact span {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>
