<script setup>
const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  },
  columns: {
    type: Array,
    default: () => []
  },
  items: {
    type: Array,
    default: () => []
  },
  maxHeight: {
    type: Number,
    default: 260
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  }
})
</script>

<template>
  <div class="result-table">
    <div class="head">
      <div>
        <p v-if="title" class="title">{{ title }}</p>
        <p v-if="description" class="desc">{{ description }}</p>
      </div>
      <slot name="actions" />
    </div>
    <el-table
      :data="items"
      :height="items.length ? maxHeight : undefined"
      border
      size="small"
      :empty-text="emptyText"
    >
      <el-table-column
        v-for="col in columns"
        :key="col.prop || col.label"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        show-overflow-tooltip
      />
    </el-table>
  </div>
</template>

<style scoped>
.result-table {
  margin-top: 16px;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.title {
  margin: 0;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.desc {
  margin: 6px 0 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}
</style>
