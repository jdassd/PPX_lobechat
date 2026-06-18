<script setup>
import { ref } from 'vue'

import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import JsonPanel from './parts/JsonPanel.vue'
import TransformPanel from './parts/TransformPanel.vue'
import DedupPanel from './parts/DedupPanel.vue'
import ReplacePanel from './parts/ReplacePanel.vue'

const activeTab = ref('json')

const TABS = [
  { name: 'json', label: 'JSON 工具' },
  { name: 'transform', label: '文本转换' },
  { name: 'dedup', label: '去重 / 排序' },
  { name: 'replace', label: '批量替换' }
]
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#7c5cff">
    <JsonPanel v-show="activeTab === 'json'" />
    <TransformPanel v-show="activeTab === 'transform'" />
    <DedupPanel v-show="activeTab === 'dedup'" />
    <ReplacePanel v-show="activeTab === 'replace'" />
  </ToolWorkspace>
</template>

<style scoped>
/* 使用全局主题样式 */
</style>
