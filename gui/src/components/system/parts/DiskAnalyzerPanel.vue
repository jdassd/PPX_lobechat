<template>
  <div>
    <div class="toolbar">
      <el-select v-model="diskAnalyzerState.selectedDisk" placeholder="选择分区" class="disk-select">
        <el-option
          v-for="disk in status.disks"
          :key="disk.mount"
          :label="`${disk.label} (${disk.usedText} / ${disk.totalText})`"
          :value="disk.mount"
        />
      </el-select>
      <el-button type="primary" :loading="diskAnalyzerState.analyzing" @click="analyzeDisk">
        <template #icon><el-icon><Search /></el-icon></template>
        分析磁盘空间
      </el-button>
    </div>

    <div v-if="diskAnalyzerState.tree" class="disk-tree-container">
      <div class="disk-summary">
        <span>总占用: <strong>{{ diskAnalyzerState.tree.sizeText }}</strong></span>
        <span>文件数: <strong>{{ diskAnalyzerState.tree.fileCount }}</strong></span>
        <span>目录数: <strong>{{ diskAnalyzerState.tree.dirCount }}</strong></span>
      </div>
      <el-tree
        :data="diskAnalyzerState.tree.children"
        :props="{ label: 'name', children: 'children' }"
        default-expand-all
        class="disk-tree"
      >
        <template #default="{ node, data }">
          <div class="tree-node">
            <el-icon v-if="data.isFile"><Document /></el-icon>
            <el-icon v-else><Folder /></el-icon>
            <span class="tree-label">{{ data.name }}</span>
            <el-tag size="small" effect="plain">{{ data.sizeText }}</el-tag>
          </div>
        </template>
      </el-tree>
    </div>
    <div v-else-if="!diskAnalyzerState.analyzing" class="empty-hint">
      选择分区后点击“分析磁盘空间”开始分析
    </div>
    <div v-else class="empty-hint">
      正在分析中，请稍候...
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall } from '@/utils/pyapi'
import { Search, Document, Folder } from '@element-plus/icons-vue'

const props = defineProps({
  apiReady: {
    type: Boolean,
    default: false
  },
  status: {
    type: Object,
    required: true
  }
})

const diskAnalyzerState = reactive({
  selectedDisk: '',
  analyzing: false,
  tree: null
})

const analyzeDisk = async () => {
  if (!diskAnalyzerState.selectedDisk) {
    ElMessage.warning('请先选择要分析的分区')
    return
  }
  if (!props.apiReady || !window.pywebview?.api?.system_analyzeDisk) {
    ElMessage.warning('当前环境不支持磁盘分析功能')
    return
  }
  diskAnalyzerState.analyzing = true
  diskAnalyzerState.tree = null
  try {
    const { ok, data: res } = await pyCall('system_analyzeDisk', {
      path: diskAnalyzerState.selectedDisk,
      maxDepth: 3,
      maxItems: 50
    })
    if (ok) {
      diskAnalyzerState.tree = res.tree
    } else {
      ElMessage.error(res?.message || '分析失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '分析失败')
  } finally {
    diskAnalyzerState.analyzing = false
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

.disk-select {
  width: 280px;
}

.empty-hint {
  font-size: 12px;
  color: var(--ppx-text-secondary);
  margin-top: 8px;
}

.disk-tree-container {
  margin-top: 12px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  padding: 16px;
}

.disk-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--ppx-text-secondary);
}

.disk-summary strong {
  color: var(--ppx-text-primary);
}

.disk-tree {
  background: transparent;
  --el-tree-node-hover-bg-color: rgba(148, 163, 184, 0.1);
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.tree-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-node .el-icon {
  color: var(--ppx-text-muted);
}

@media (max-width: 600px) {
  .toolbar {
    flex-direction: column;
  }

  .disk-select {
    width: 100%;
  }

  :deep(.el-button) {
    width: 100%;
  }
}
</style>
