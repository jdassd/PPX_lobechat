<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
const props = defineProps({ modelValue: { type: Object, default: () => ({}) }, numeric: Boolean, keyLabel: { type: String, default: '目标字段' }, valueLabel: { type: String, default: '来源字段' } })
const emit = defineEmits(['update:modelValue'])
const newKey = ref('')
const entries = computed(() => Object.entries(props.modelValue || {}))
const set = (key, value) => emit('update:modelValue', { ...(props.modelValue || {}), [key]: value })
const remove = (key) => {
  const next = { ...props.modelValue }
  delete next[key]
  emit('update:modelValue', next)
}
const add = () => {
  const key = newKey.value.trim()
  if (!key || Object.prototype.hasOwnProperty.call(props.modelValue || {}, key)) return ElMessage.warning('请输入尚未使用的名称')
  set(key, props.numeric ? 0 : '')
  newKey.value = ''
}
</script>
<template>
  <div class="mapping-editor">
    <div v-for="[key, value] in entries" :key="key" class="mapping-row">
      <span :title="key">{{ key }}</span
      ><span>→</span>
      <el-input-number v-if="numeric" :model-value="Number(value)" @update:model-value="set(key, $event)" />
      <el-input v-else :model-value="String(value)" :placeholder="valueLabel" @update:model-value="set(key, $event)" />
      <el-button text @click="remove(key)">移除</el-button>
    </div>
    <div class="mapping-row"><el-input v-model="newKey" :placeholder="keyLabel" @keyup.enter="add" /><el-button @click="add">添加映射</el-button></div>
  </div>
</template>
<style scoped>
.mapping-editor {
  width: 100%;
  display: grid;
  gap: 8px;
}
.mapping-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mapping-row > span:first-child {
  min-width: 100px;
  max-width: 35%;
  overflow-wrap: anywhere;
}
.mapping-row .el-input {
  flex: 1;
}
</style>
