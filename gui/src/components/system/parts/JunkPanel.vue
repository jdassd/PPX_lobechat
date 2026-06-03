<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" :loading="junkState.scanning" @click="scanJunk">
        <template #icon><el-icon><Search /></el-icon></template>
        扫描垃圾文件
      </el-button>
      <el-button
        type="danger"
        :loading="junkState.cleaning"
        :disabled="!junkState.selectedCategories.length"
        @click="cleanJunk"
      >
        <template #icon><el-icon><Delete /></el-icon></template>
        清理选中项 ({{ junkState.selectedCategories.length }})
      </el-button>
      <div class="toolbar-info" v-if="junkState.totalSizeText">
        <span>总计可清理: <strong>{{ junkState.totalSizeText }}</strong></span>
      </div>
    </div>

    <el-table
      :data="junkState.items"
      v-loading="junkState.scanning"
      border
      size="small"
      empty-text="点击“扫描垃圾文件”开始扫描"
      @selection-change="onJunkSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="name" label="类别" min-width="160" />
      <el-table-column prop="fileCount" label="文件数" width="100" />
      <el-table-column prop="sizeText" label="大小" width="120" />
      <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
    </el-table>

    <div v-if="junkState.cleanResult" class="clean-result">
      <el-alert
        :type="junkState.cleanResult.errors?.length ? 'warning' : 'success'"
        show-icon
        :closable="false"
      >
        <template #title>
          已清理 {{ junkState.cleanResult.clearedCount }} 个项目，释放 {{ junkState.cleanResult.clearedSizeText }}
        </template>
        <template #default v-if="junkState.cleanResult.errors?.length">
          <div v-for="err in junkState.cleanResult.errors" :key="err">{{ err }}</div>
        </template>
      </el-alert>
    </div>
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
  }
})

const junkState = reactive({
  scanning: false,
  cleaning: false,
  items: [],
  selectedCategories: [],
  totalSizeText: '',
  cleanResult: null
})

const onJunkSelectionChange = (selection) => {
  junkState.selectedCategories = selection.map(item => item.category)
}

const scanJunk = async () => {
  if (!props.apiReady || !window.pywebview?.api?.system_scanJunk) {
    ElMessage.warning('当前环境不支持垃圾清理功能')
    return
  }
  junkState.scanning = true
  junkState.cleanResult = null
  try {
    const { ok, data: res } = await pyCall('system_scanJunk')
    if (ok) {
      junkState.items = res.items || []
      junkState.totalSizeText = res.totalSizeText || ''
    } else {
      ElMessage.error(res?.message || '扫描失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '扫描失败')
  } finally {
    junkState.scanning = false
  }
}

const cleanJunk = async () => {
  if (!junkState.selectedCategories.length) {
    ElMessage.warning('请先选择要清理的类别')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要清理选中的 ${junkState.selectedCategories.length} 个类别吗？此操作不可撤销。`,
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
  junkState.cleaning = true
  try {
    const { ok, data: res } = await pyCall('system_cleanJunk', {
      categories: junkState.selectedCategories
    })
    if (ok) {
      junkState.cleanResult = res
      ElMessage.success(`已清理 ${res.clearedCount} 个项目，释放 ${res.clearedSizeText}`)
      // 重新扫描
      await scanJunk()
    } else {
      ElMessage.error(res?.message || '清理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '清理失败')
  } finally {
    junkState.cleaning = false
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-info {
  flex: 1;
  text-align: right;
  color: var(--ppx-text-secondary);
  font-size: 13px;
}

.toolbar-info strong {
  color: var(--el-color-primary);
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
