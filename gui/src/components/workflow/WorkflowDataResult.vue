<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { dataResultEntries, previewResult } from '@/utils/workflowResults.mjs'

const props = defineProps({ result: { type: Object, default: () => ({}) }, fields: { type: Array, default: () => [] } })
const selectedPath = ref('')
const open = ref(false)
const entries = computed(() => dataResultEntries(props.result, props.fields))
const selected = computed(() => entries.value.find((entry) => entry.path === selectedPath.value) || entries.value[0])
const preview = computed(() => previewResult(selected.value?.value))
const copyResult = async () => {
  try {
    await navigator.clipboard.writeText(preview.value.fullText)
    ElMessage.success('已复制完整结果')
  } catch {
    ElMessage.error('复制失败，可选中下方结果手动复制')
  }
}
</script>

<template>
  <details v-if="entries.length" class="workflow-data-result" @toggle="open = $event.target.open">
    <summary>查看数据结果 · {{ entries.length }} 项</summary>
    <template v-if="open">
      <div class="data-result-toolbar">
        <el-select :model-value="selected?.path" aria-label="选择数据结果" @update:model-value="selectedPath = $event">
          <el-option v-for="entry in entries" :key="entry.path" :value="entry.path" :label="entry.label" />
        </el-select>
        <el-button size="small" @click="copyResult">复制完整结果</el-button>
      </div>
      <small v-if="preview.truncated">仅预览前 12000 个字符，复制可获得完整结果。</small>
      <pre tabindex="0" aria-label="数据结果内容">{{ preview.empty ? '（空字符串）' : preview.text }}</pre>
    </template>
  </details>
</template>

<style scoped>
.workflow-data-result {
  max-width: 100%;
  margin: 12px 0;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 8px;
  padding: 10px 12px;
}
summary {
  cursor: pointer;
  font-size: 12px;
}
.data-result-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 8px;
}
.data-result-toolbar .el-select {
  flex: 1;
  min-width: 140px;
}
small {
  color: var(--ppx-text-muted);
}
pre {
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 12px;
  line-height: 1.6;
  user-select: text;
}
</style>
