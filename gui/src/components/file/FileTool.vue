<script setup>
import { ref } from 'vue'

import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import SearchPanel from './parts/SearchPanel.vue'
import ClassifyPanel from './parts/ClassifyPanel.vue'
import CopyPanel from './parts/CopyPanel.vue'
import DeletePanel from './parts/DeletePanel.vue'
import RenamePanel from './parts/RenamePanel.vue'
import DedupPanel from './parts/DedupPanel.vue'
import AnalyzePanel from './parts/AnalyzePanel.vue'
import ComparePanel from './parts/ComparePanel.vue'
import ArchivePanel from './parts/ArchivePanel.vue'

const activeTab = ref('search')

const TABS = [
  { name: 'search', label: '文件搜索' },
  { name: 'classify', label: '自动分类' },
  { name: 'copy', label: '批量复制' },
  { name: 'delete', label: '批量删除' },
  { name: 'rename', label: '批量改名' },
  { name: 'dedup', label: '文件去重' },
  { name: 'analyze', label: '目录分析' },
  { name: 'compare', label: '文件对比' },
  { name: 'archive', label: '压缩 / 解压' }
]
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#0c9c8f">
    <SearchPanel v-show="activeTab === 'search'" />
    <ClassifyPanel v-show="activeTab === 'classify'" />
    <CopyPanel v-show="activeTab === 'copy'" />
    <DeletePanel v-show="activeTab === 'delete'" />
    <RenamePanel v-show="activeTab === 'rename'" />
    <DedupPanel v-show="activeTab === 'dedup'" />
    <AnalyzePanel v-show="activeTab === 'analyze'" />
    <ComparePanel v-show="activeTab === 'compare'" />
    <ArchivePanel v-show="activeTab === 'archive'" />
  </ToolWorkspace>
</template>

<style scoped>
/* 使用全局主题样式 */
</style>
