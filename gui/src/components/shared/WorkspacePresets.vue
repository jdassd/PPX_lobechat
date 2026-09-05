<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { applyConfiguration, draftKeys, getDraft, safeConfiguration } from '../../utils/workspace'

const props = defineProps({ tool: { type: String, default: '' } })
const available = computed(() => draftKeys.value.filter((key) => key.startsWith(`${props.tool}/`)))
const selected = ref('')
const presetName = ref('')
const presets = ref([])
const load = () => {
  try {
    presets.value = JSON.parse(localStorage.getItem(`ppx-presets:${selected.value}`) || '[]')
  } catch {
    presets.value = []
  }
}
watch(available, (items) => {
  if (!items.includes(selected.value)) selected.value = items[0] || ''
})
watch(selected, load)
const save = () => {
  const name = presetName.value.trim()
  if (!name || !selected.value) return
  const value = safeConfiguration(getDraft(selected.value))
  presets.value = [...presets.value.filter((item) => item.name !== name), { name, value }]
  localStorage.setItem(`ppx-presets:${selected.value}`, JSON.stringify(presets.value))
  ElMessage.success('已保存参数预设')
}
const apply = (name) => {
  const preset = presets.value.find((item) => item.name === name)
  if (preset) applyConfiguration(getDraft(selected.value), preset.value)
}
</script>

<template>
  <el-popover v-if="available.length" placement="bottom-end" width="360" trigger="click">
    <template #reference><el-button size="small" text>参数预设</el-button></template>
    <p>切换页面保留草稿；重启恢复参数，文件和密码需重新选择或填写。</p>
    <el-select v-model="selected" placeholder="选择参数组" style="width: 100%">
      <el-option v-for="key in available" :key="key" :value="key" :label="key.split('/').slice(1).join(' / ')" />
    </el-select>
    <el-input v-model="presetName" placeholder="预设名称" maxlength="60" style="margin-top: 8px"
      ><template #append><el-button @click="save">保存</el-button></template></el-input
    >
    <el-select placeholder="应用已保存预设" style="width: 100%; margin-top: 8px" @change="apply"><el-option v-for="preset in presets" :key="preset.name" :label="preset.name" :value="preset.name" /></el-select>
  </el-popover>
</template>
