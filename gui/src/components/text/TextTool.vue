<script setup>
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import { useInitialTab } from '@/composables/useInitialTab'
import JsonPanel from './parts/JsonPanel.vue'
import TransformPanel from './parts/TransformPanel.vue'
import DedupPanel from './parts/DedupPanel.vue'
import DiffPanel from './parts/DiffPanel.vue'
import JwtPanel from './parts/JwtPanel.vue'
import ReplacePanel from './parts/ReplacePanel.vue'

const TABS = [
  { name: 'json', label: 'JSON 工具' },
  { name: 'transform', label: '文本转换' },
  { name: 'dedup', label: '去重 / 排序' },
  { name: 'replace', label: '批量替换' },
  { name: 'diff', label: '差异比较' },
  { name: 'jwt', label: 'JWT 诊断' }
]

const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = useInitialTab(TABS, () => props.initialTab, 'json')
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#7c5cff">
    <JsonPanel v-show="activeTab === 'json'" />
    <TransformPanel v-show="activeTab === 'transform'" />
    <DedupPanel v-show="activeTab === 'dedup'" />
    <ReplacePanel v-show="activeTab === 'replace'" />
    <DiffPanel v-show="activeTab === 'diff'" />
    <JwtPanel v-show="activeTab === 'jwt'" />
  </ToolWorkspace>
</template>

<style scoped>
/* 使用全局主题样式 */
</style>
