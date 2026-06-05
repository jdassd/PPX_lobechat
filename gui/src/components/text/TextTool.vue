<script setup>
import { ref } from 'vue'

import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import CodecPanel from './parts/CodecPanel.vue'
import RegexPanel from './parts/RegexPanel.vue'
import JsonPanel from './parts/JsonPanel.vue'
import CsvPanel from './parts/CsvPanel.vue'
import TransformPanel from './parts/TransformPanel.vue'
import DedupPanel from './parts/DedupPanel.vue'
import ReplacePanel from './parts/ReplacePanel.vue'
import TimestampPanel from './parts/TimestampPanel.vue'
import UnicodePanel from './parts/UnicodePanel.vue'
import HashPanel from './parts/HashPanel.vue'

const activeTab = ref('codec')

const TABS = [
  { name: 'codec', label: '编码 / 解码' },
  { name: 'regex', label: '正则工具' },
  { name: 'json', label: 'JSON 工具' },
  { name: 'csv', label: 'CSV / JSON 转换' },
  { name: 'transform', label: '文本转换' },
  { name: 'dedup', label: '去重 / 排序' },
  { name: 'replace', label: '批量替换' },
  { name: 'timestamp', label: '时间戳转换' },
  { name: 'unicode', label: 'Unicode 工具' },
  { name: 'hash', label: '哈希计算' },
]
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#7c5cff">
    <CodecPanel v-show="activeTab === 'codec'" />
    <RegexPanel v-show="activeTab === 'regex'" />
    <JsonPanel v-show="activeTab === 'json'" />
    <CsvPanel v-show="activeTab === 'csv'" />
    <TransformPanel v-show="activeTab === 'transform'" />
    <DedupPanel v-show="activeTab === 'dedup'" />
    <ReplacePanel v-show="activeTab === 'replace'" />
    <TimestampPanel v-show="activeTab === 'timestamp'" />
    <UnicodePanel v-show="activeTab === 'unicode'" />
    <HashPanel v-show="activeTab === 'hash'" />
  </ToolWorkspace>
</template>

<style scoped>
/* 使用全局主题样式 */
</style>
