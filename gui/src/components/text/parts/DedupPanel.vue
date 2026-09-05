<script setup>
import { useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

const state = useDraft('text/parts/DedupPanel/state', {
  content: '',
  operation: 'deduplicate',
  sortMethod: 'alpha',
  caseSensitive: true,
  trimWhitespace: true,
  keepEmpty: false,
  result: '',
  stats: null,
  frequency: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runDedup = async () => {
  if (!ensurePyReady()) return
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('text_deduplicate_sort', {
      content: state.content,
      operation: state.operation,
      sortMethod: state.sortMethod,
      caseSensitive: state.caseSensitive,
      trimWhitespace: state.trimWhitespace,
      keepEmpty: state.keepEmpty
    })
    if (ok) {
      state.result = res.result || ''
      state.stats = res.stats || null
      state.frequency = res.frequency || []
      ElMessage.success(message || '处理完成')
    } else {
      ElMessage.error(message || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>多行文本去重与排序</h4>
      <p>自定义大小写敏感、保留空行以及词频统计</p>
    </header>
    <el-form :model="state" label-width="130px" class="form-gap">
      <el-form-item label="操作">
        <el-radio-group v-model="state.operation">
          <el-radio-button label="deduplicate">去重</el-radio-button>
          <el-radio-button label="sort">排序</el-radio-button>
          <el-radio-button label="frequency">词频</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="排序方式" v-if="state.operation === 'sort'">
        <el-select v-model="state.sortMethod" style="width: 220px">
          <el-option label="字典序" value="alpha" />
          <el-option label="按长度" value="length" />
        </el-select>
      </el-form-item>
      <el-form-item label="选项">
        <el-checkbox v-model="state.caseSensitive">区分大小写</el-checkbox>
        <el-checkbox v-model="state.trimWhitespace">裁剪空白</el-checkbox>
        <el-checkbox v-model="state.keepEmpty">保留空行</el-checkbox>
      </el-form-item>
    </el-form>
    <div class="text-grid">
      <el-input v-model="state.content" type="textarea" :rows="8" placeholder="每行一个条目" />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runDedup">执行</el-button>
      </div>
      <PreviewPanel title="输出" :content="state.result" />
    </div>
    <div v-if="state.stats" class="stats-panel">
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="原始行数">{{ state.stats.originalCount }}</el-descriptions-item>
        <el-descriptions-item label="有效行数">{{ state.stats.effectiveCount }}</el-descriptions-item>
        <el-descriptions-item label="唯一计数">{{ state.stats.uniqueCount }}</el-descriptions-item>
        <el-descriptions-item label="移除行数">{{ state.stats.removedCount }}</el-descriptions-item>
      </el-descriptions>
    </div>
    <el-table v-if="state.frequency.length" :data="state.frequency" border size="small" style="margin-top: 16px">
      <el-table-column label="条目" prop="value" />
      <el-table-column label="次数" prop="count" width="100" />
    </el-table>
  </section>
</template>

<style scoped>
.text-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px minmax(0, 1fr);
  gap: 16px;
}

.text-grid-actions {
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-gap {
  margin-top: 12px;
}

.stats-panel {
  margin-top: 16px;
}
</style>
