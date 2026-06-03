<template>
  <div>
    <el-alert v-if="!isWindows" type="info" show-icon :closable="false" class="helper-hint">
      注册表清理仅支持 Windows 系统
    </el-alert>
    <template v-else>
      <div class="toolbar">
        <el-button type="primary" :loading="registryState.scanning" @click="scanRegistry">
          <template #icon><el-icon><Search /></el-icon></template>
          扫描无效注册表项
        </el-button>
        <el-button
          type="danger"
          :loading="registryState.cleaning"
          :disabled="!registryState.selectedItems.length"
          @click="cleanRegistry"
        >
          <template #icon><el-icon><Delete /></el-icon></template>
          清理选中项 ({{ registryState.selectedItems.length }})
        </el-button>
      </div>

      <el-table
        :data="registryState.items"
        v-loading="registryState.scanning"
        border
        size="small"
        max-height="350"
        empty-text="点击“扫描无效注册表项”开始扫描"
        @selection-change="onRegistrySelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="reason" label="问题描述" min-width="250" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.type === 'uninstall'" size="small" type="warning">卸载信息</el-tag>
            <el-tag v-else-if="row.type === 'file_ext'" size="small" type="info">文件关联</el-tag>
            <el-tag v-else size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="registryState.cleanResult" class="clean-result">
        <el-alert
          :type="registryState.cleanResult.errors?.length ? 'warning' : 'success'"
          show-icon
          :closable="false"
        >
          <template #title>
            已清理 {{ registryState.cleanResult.clearedCount }} 个注册表项
          </template>
          <template #default v-if="registryState.cleanResult.errors?.length">
            <div v-for="err in registryState.cleanResult.errors" :key="err">{{ err }}</div>
          </template>
        </el-alert>
      </div>
    </template>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi as pyCall } from '@/utils/pyapi'
import { Search, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  apiReady: {
    type: Boolean,
    default: false
  },
  isWindows: {
    type: Boolean,
    default: false
  }
})

const registryState = reactive({
  scanning: false,
  cleaning: false,
  items: [],
  selectedItems: [],
  cleanResult: null
})

const onRegistrySelectionChange = (selection) => {
  registryState.selectedItems = selection
}

const scanRegistry = async () => {
  if (!props.apiReady || !window.pywebview?.api?.system_scanRegistry) {
    ElMessage.warning('当前环境不支持注册表清理功能')
    return
  }
  registryState.scanning = true
  registryState.cleanResult = null
  try {
    const { ok, data: res } = await pyCall('system_scanRegistry')
    if (ok) {
      registryState.items = res.items || []
      if (!res.items?.length) {
        ElMessage.success('未发现无效注册表项')
      }
    } else {
      ElMessage.error(res?.message || '扫描失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '扫描失败')
  } finally {
    registryState.scanning = false
  }
}

const cleanRegistry = async () => {
  if (!registryState.selectedItems.length) {
    ElMessage.warning('请先选择要清理的注册表项')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要清理选中的 ${registryState.selectedItems.length} 个注册表项吗？此操作不可撤销。`,
      '确认清理',
      {
        confirmButtonText: '清理',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }
  registryState.cleaning = true
  try {
    const { ok, data: res } = await pyCall('system_cleanRegistry', {
      items: registryState.selectedItems
    })
    if (ok) {
      registryState.cleanResult = res
      ElMessage.success(`已清理 ${res.clearedCount} 个注册表项`)
      // 重新扫描
      await scanRegistry()
    } else {
      ElMessage.error(res?.message || '清理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '清理失败')
  } finally {
    registryState.cleaning = false
  }
}
</script>

<style scoped>
.helper-hint {
  margin-bottom: 12px;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.clean-result {
  margin-top: 12px;
}

@media (max-width: 600px) {
  .toolbar {
    flex-direction: column;
  }

  :deep(.el-button) {
    width: 100%;
  }
}
</style>
