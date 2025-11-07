<script setup>
import { computed, markRaw } from 'vue'
import { useToolkitStore } from '@/stores/toolkit'
import ClipboardTool from './modules/ClipboardTool.vue'
import TextBatchTool from './modules/TextBatchTool.vue'
import UnitConverterTool from './modules/UnitConverterTool.vue'
import SystemMonitorTool from './modules/SystemMonitorTool.vue'

const store = useToolkitStore()

const modules = [
  {
    id: 'clipboard',
    component: markRaw(ClipboardTool),
    keywords: ['clip', '剪贴板', '历史']
  },
  {
    id: 'text',
    component: markRaw(TextBatchTool),
    keywords: ['文本', '批处理', '正则']
  },
  {
    id: 'unit',
    component: markRaw(UnitConverterTool),
    keywords: ['单位', '换算', '汇率']
  },
  {
    id: 'system-monitor',
    component: markRaw(SystemMonitorTool),
    keywords: ['系统', '监控', 'cpu', 'gpu']
  }
]

const visibleModules = computed(() => {
  return modules.filter((mod) => store.searchMatcher([...mod.keywords, mod.id]))
})
</script>

<template>
  <section class="tool-grid">
    <component
      v-for="mod in visibleModules"
      :key="mod.id"
      :is="mod.component"
      class="tool-grid__item"
    />
    <el-empty
      v-if="!visibleModules.length"
      description="没有匹配的工具"
    />
  </section>
</template>
