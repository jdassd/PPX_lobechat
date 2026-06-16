<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#3b7de0">
    <el-alert v-if="!apiReady" type="warning" show-icon class="helper-hint" :closable="false">
      请在桌面客户端内使用，浏览器预览无法访问本地系统信息。
    </el-alert>

    <StartupPanel v-show="activeTab === 'startup'" :api-ready="apiReady" :visible="activeTab === 'startup'" />
    <ProcessPanel v-show="activeTab === 'process'" :api-ready="apiReady" :visible="activeTab === 'process'" />
  </ToolWorkspace>
</template>

<script setup>
import { ref } from 'vue'
import { usePyReady } from '@/composables/useApiCall'
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import StartupPanel from './parts/StartupPanel.vue'
import ProcessPanel from './parts/ProcessPanel.vue'

// 系统管理仅保留「开机启动项」与「进程管理」两项功能
const TABS = [
  { name: 'startup', label: '开机启动项' },
  { name: 'process', label: '进程管理' },
]

const activeTab = ref('startup')

// 统一就绪状态管理（替代原手写 pywebviewready 监听）
const { apiReady } = usePyReady()
</script>

<style scoped>
.helper-hint {
  margin-bottom: 12px;
}
</style>
