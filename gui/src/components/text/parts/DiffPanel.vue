<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import PreviewPanel from '../../shared/PreviewPanel.vue'
import { callApi, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)
const state = reactive({
  left: '',
  right: '',
  mode: 'lines',
  ignoreWhitespace: false,
  ignoreCase: false,
  hideUnchanged: false,
  result: null
})

const visibleOperations = computed(() => (state.result?.operations || []).filter((item) => !state.hideUnchanged || item.type !== 'equal'))
const operationLabel = { equal: '相同', replace: '修改', delete: '删除', insert: '新增' }
const operationType = { equal: 'info', replace: 'warning', delete: 'danger', insert: 'success' }
const joinSegment = (items) => (state.result?.mode === 'words' ? (items || []).join('') : (items || []).join('\n'))

const compare = async () => {
  if (!state.left && !state.right) return ElMessage.warning('请至少输入一侧文本')
  if (!hasPyApi()) return ElMessage.warning('该功能需在桌面客户端使用')
  loading.value = true
  try {
    const response = await callApi('text_compare', {
      left: state.left,
      right: state.right,
      mode: state.mode,
      ignoreWhitespace: state.ignoreWhitespace,
      ignoreCase: state.ignoreCase
    })
    if (!response.ok) return ElMessage.error(response.message || '比较失败')
    state.result = response.data
    ElMessage.success(response.message)
  } catch (error) {
    ElMessage.error(error?.message || '比较失败')
  } finally {
    loading.value = false
  }
}

const swap = () => {
  const value = state.left
  state.left = state.right
  state.right = value
  state.result = null
}

watch([() => state.mode, () => state.ignoreWhitespace, () => state.ignoreCase], () => {
  state.result = null
})
</script>

<template>
  <section class="panel diff-panel">
    <header>
      <h4>文本 / 列表差异比较</h4>
      <p>按行或按词比较两份内容，统计新增、删除与修改，并生成统一 Diff。</p>
    </header>
    <div class="diff-options">
      <el-radio-group v-model="state.mode">
        <el-radio-button value="lines">按行</el-radio-button>
        <el-radio-button value="words">按词</el-radio-button>
      </el-radio-group>
      <el-checkbox v-model="state.ignoreWhitespace">忽略空白差异</el-checkbox>
      <el-checkbox v-model="state.ignoreCase">忽略大小写</el-checkbox>
      <el-checkbox v-model="state.hideUnchanged">隐藏相同内容</el-checkbox>
    </div>
    <div class="input-grid">
      <div><strong>左侧 / 原始内容</strong><el-input v-model="state.left" type="textarea" :rows="12" resize="vertical" placeholder="粘贴原始文本或列表" /></div>
      <div><strong>右侧 / 新内容</strong><el-input v-model="state.right" type="textarea" :rows="12" resize="vertical" placeholder="粘贴要比较的文本或列表" /></div>
    </div>
    <div class="actions"><el-button @click="swap">交换两侧</el-button><el-button type="primary" :loading="loading" @click="compare">开始比较</el-button></div>

    <template v-if="state.result">
      <div class="stats">
        <div>
          <b>{{ state.result.similarity }}%</b><span>相似度</span>
        </div>
        <div class="success">
          <b>+{{ state.result.stats.added }}</b
          ><span>新增</span>
        </div>
        <div class="danger">
          <b>-{{ state.result.stats.removed }}</b
          ><span>删除</span>
        </div>
        <div>
          <b>{{ state.result.stats.changedGroups }}</b
          ><span>变化分组</span>
        </div>
      </div>
      <div class="operation-list">
        <article v-for="(operation, index) in visibleOperations" :key="`${operation.type}-${index}`" class="operation" :class="operation.type">
          <el-tag :type="operationType[operation.type]" size="small" effect="plain">{{ operationLabel[operation.type] }}</el-tag>
          <pre class="left">{{ joinSegment(operation.left) || '∅' }}</pre>
          <pre class="right">{{ joinSegment(operation.right) || '∅' }}</pre>
        </article>
        <el-empty v-if="!visibleOperations.length" description="两侧内容没有差异" />
      </div>
      <PreviewPanel v-if="state.result.mode === 'lines' && state.result.unifiedDiff" class="unified" title="Unified Diff" :content="state.result.unifiedDiff" />
    </template>
  </section>
</template>

<style scoped>
.diff-options,
.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}
.input-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 16px;
}
.input-grid > div {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--ppx-text-secondary);
}
.actions {
  justify-content: flex-end;
  margin-top: 12px;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 20px 0 12px;
}
.stats div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 10px;
  background: var(--ppx-bg-soft);
}
.stats b {
  color: var(--accent);
  font-size: 20px;
}
.stats .success b {
  color: var(--el-color-success);
}
.stats .danger b {
  color: var(--el-color-danger);
}
.stats span {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.operation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.operation {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 10px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 10px;
}
.operation pre {
  max-height: 220px;
  margin: 0;
  padding: 9px;
  overflow: auto;
  border-radius: 7px;
  background: var(--ppx-bg-soft);
  color: var(--ppx-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}
.operation.delete .left,
.operation.replace .left {
  background: color-mix(in srgb, var(--el-color-danger) 10%, var(--ppx-bg-soft));
}
.operation.insert .right,
.operation.replace .right {
  background: color-mix(in srgb, var(--el-color-success) 10%, var(--ppx-bg-soft));
}
.unified {
  margin-top: 14px;
}
@media (max-width: 850px) {
  .input-grid,
  .stats {
    grid-template-columns: 1fr;
  }
  .operation {
    grid-template-columns: 1fr;
  }
}
</style>
