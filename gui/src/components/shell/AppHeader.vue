<script setup>
import { computed } from 'vue'
import dayjs from '@/utils/dayjs'
import { useToolkitStore } from '@/stores/toolkit'

const store = useToolkitStore()

const searchValue = computed({
  get: () => store.searchKeyword,
  set: (val) => store.setSearchKeyword(val)
})

const syncLabel = computed(() => {
  if (store.cloudSync.status === 'syncing') {
    return '同步中...'
  }
  if (store.cloudSync.status === 'online') {
    return store.cloudSync.updatedAt
      ? `已于 ${dayjs(store.cloudSync.updatedAt).format('HH:mm:ss')} 同步`
      : '已连接'
  }
  return '未连接'
})

const handleSync = () => {
  store.cloudSync.status = 'syncing'
  setTimeout(() => {
    store.cloudSync.status = 'online'
    store.cloudSync.updatedAt = new Date().toISOString()
  }, 800)
}
</script>

<template>
  <header class="app-header glass-panel">
    <div class="app-header__brand">
      <div class="app-header__logo">
        <span>PPX 工具箱</span>
        <small>开箱即用的多工具集</small>
      </div>
      <el-tag size="small" effect="dark" type="success">MVP 阶段</el-tag>
    </div>

    <div class="app-header__center">
      <el-input
        v-model="searchValue"
        placeholder="搜索工具、操作或标签"
        prefix-icon="ele-Search"
        clearable
      />
      <div class="app-header__sync-state">
        <span class="dot" :class="`is-${store.cloudSync.status}`" />
        <span>{{ syncLabel }}</span>
      </div>
    </div>

    <div class="app-header__actions">
      <el-tooltip :content="store.theme === 'light' ? '切换到深色' : '切换到浅色'">
        <el-button circle @click="store.toggleTheme">
          <component :is="store.theme === 'light' ? 'ele-Moon' : 'ele-Sunny'" />
        </el-button>
      </el-tooltip>
      <el-button :loading="store.cloudSync.status === 'syncing'" icon="ele-Cloudy" @click="handleSync">
        云同步
      </el-button>
      <el-avatar size="small">JD</el-avatar>
    </div>
  </header>
</template>
