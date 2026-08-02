<script setup>
import { onMounted, ref } from 'vue'

import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import { useInitialTab } from '@/composables/useInitialTab'
import { callApi } from '@/utils/pyapi'
import ConvertPanel from './parts/ConvertPanel.vue'
import CompressPanel from './parts/CompressPanel.vue'
import CutPanel from './parts/CutPanel.vue'
import AudioPanel from './parts/AudioPanel.vue'
import ConcatPanel from './parts/ConcatPanel.vue'

const environment = ref(null)

const TABS = [
  { name: 'convert', label: '格式转换' },
  { name: 'compress', label: '视频压缩' },
  { name: 'cut', label: '视频截取' },
  { name: 'audio', label: '音频提取' },
  { name: 'concat', label: '视频合成' }
]

const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = useInitialTab(TABS, () => props.initialTab, 'convert')

onMounted(async () => {
  try {
    const { ok, message, data } = await callApi('video_checkEnvironment')
    environment.value = {
      available: ok && data?.available,
      message: message || '未检测到完整的 FFmpeg 环境'
    }
  } catch (error) {
    if (String(error?.message || '').includes('不在桌面客户端')) return
    environment.value = { available: false, message: error?.message || '视频处理环境检查失败' }
  }
})
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#d6447a">
    <el-alert v-if="environment && !environment.available" class="environment-alert" type="warning" :closable="false" show-icon :title="environment.message" description="请安装完整 FFmpeg 并将 ffmpeg、ffprobe 加入系统 PATH，完成后重启应用。" />
    <ConvertPanel v-show="activeTab === 'convert'" />
    <CompressPanel v-show="activeTab === 'compress'" />
    <CutPanel v-show="activeTab === 'cut'" />
    <AudioPanel v-show="activeTab === 'audio'" />
    <ConcatPanel v-show="activeTab === 'concat'" />
  </ToolWorkspace>
</template>

<style scoped>
.environment-alert {
  margin-bottom: 16px;
}
</style>
