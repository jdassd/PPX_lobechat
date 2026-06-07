<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#2b579a">
    <SplitPanel v-show="activeTab === 'split'" />
    <MergePanel v-show="activeTab === 'merge'" />

    <section class="log-panel">
      <header>
        <h4>最近操作</h4>
        <p>保留最近 8 条，便于定位输出目录</p>
      </header>
      <el-timeline v-if="shared.logs.length">
        <el-timeline-item v-for="item in shared.logs" :key="item.id" :timestamp="item.time" :type="item.type" size="large">
          <div class="log-entry">
            <strong>{{ item.message }}</strong>
            <p class="log-sub">{{ item.action }}</p>
            <el-link v-if="item.detail?.output" type="primary" @click="openPath(item.detail.output)"> 打开输出 </el-link>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无记录" />
    </section>
  </ToolWorkspace>
</template>

<script setup>
import { provide, reactive, ref } from 'vue'
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import { useWordApi } from './parts/useWordApi'
import SplitPanel from './parts/SplitPanel.vue'
import MergePanel from './parts/MergePanel.vue'

const TABS = [
  { name: 'split', label: '切割 Word' },
  { name: 'merge', label: '合并 Word' }
]

const activeTab = ref('split')

const shared = reactive({
  loading: false,
  logs: []
})

const wordApi = useWordApi(shared)
const { openPath } = wordApi

provide('wordApi', wordApi)
provide('wordShared', shared)
</script>

<style scoped>
.log-panel {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--ppx-glass-border);
}
.log-panel header {
  margin-bottom: 12px;
}
.log-panel header h4 {
  margin: 0;
  color: var(--ppx-text-primary);
}
.log-panel header p {
  margin: 4px 0 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}
.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.log-entry .log-sub {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>
