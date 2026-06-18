<script setup>
import { ref } from 'vue'

import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import ConvertPanel from './parts/ConvertPanel.vue'
import CompressPanel from './parts/CompressPanel.vue'
import CutPanel from './parts/CutPanel.vue'
import AudioPanel from './parts/AudioPanel.vue'
import ConcatPanel from './parts/ConcatPanel.vue'

const activeTab = ref('convert')

const TABS = [
  { name: 'convert', label: '格式转换' },
  { name: 'compress', label: '视频压缩' },
  { name: 'cut', label: '视频截取' },
  { name: 'audio', label: '音频提取' },
  { name: 'concat', label: '视频合成' }
]
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#d6447a">
    <ConvertPanel v-show="activeTab === 'convert'" />
    <CompressPanel v-show="activeTab === 'compress'" />
    <CutPanel v-show="activeTab === 'cut'" />
    <AudioPanel v-show="activeTab === 'audio'" />
    <ConcatPanel v-show="activeTab === 'concat'" />
  </ToolWorkspace>
</template>

<style scoped>
/* 使用全局主题样式 */
</style>
