<script setup>
import { computed, ref, watch } from 'vue'
import ResultActions from './ResultActions.vue'
const props = defineProps({ task: { type: Object, required: true } })
const visible = ref(false)
const page = ref(1)
const filter = ref('all')
const labels = { success: '成功', failed: '失败', skipped: '跳过', canceled: '已取消', interrupted: '已中断', pending: '待处理' }
const rows = computed(() => {
  const detailed = props.task.itemResults?.length ? props.task.itemResults : props.task.result?.itemResults
  return detailed?.length ? detailed : (props.task.result?.failures || []).map((failure) => ({ input: failure.input || failure.path || failure.url, status: 'failed', message: failure.error, outputs: [] }))
})
const filtered = computed(() => rows.value.filter((row) => filter.value === 'all' || row.status === filter.value))
const paged = computed(() => filtered.value.slice((page.value - 1) * 25, page.value * 25))
watch(filter, () => {
  page.value = 1
})
</script>
<template>
  <el-button v-if="rows.length" text @click="visible = true">逐项检查（{{ rows.length }}）</el-button>
  <el-dialog v-model="visible" title="逐项处理结果" width="min(1000px, 92vw)" append-to-body>
    <el-select v-model="filter" style="width: 160px; margin-bottom: 12px"><el-option label="全部结果" value="all" /><el-option v-for="(label, status) in labels" :key="status" :label="label" :value="status" /></el-select>
    <el-table :data="paged" max-height="500">
      <el-table-column prop="input" label="输入" min-width="250" show-overflow-tooltip />
      <el-table-column label="状态" width="100"
        ><template #default="{ row }"
          ><el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'info'">{{ labels[row.status] || row.status }}</el-tag></template
        ></el-table-column
      >
      <el-table-column prop="message" label="说明" min-width="240" show-overflow-tooltip />
      <el-table-column label="结果" width="190"
        ><template #default="{ row }"><ResultActions v-if="row.outputs?.length" :assets="row.outputs" /></template
      ></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="25" :total="filtered.length" layout="total, prev, pager, next" />
  </el-dialog>
</template>
