<script setup>
import { computed, onMounted, watch } from 'vue'
import { useToolkitStore } from '@/stores/toolkit'
import AppHeader from '@/components/shell/AppHeader.vue'
import SideNav from '@/components/shell/SideNav.vue'
import InsightPanel from '@/components/shell/InsightPanel.vue'
import ToolGrid from '@/components/tools/ToolGrid.vue'

const store = useToolkitStore()
const themeClass = computed(() => `theme-${store.theme}`)

const applyTheme = (theme) => {
  if (typeof document === 'undefined') {
    return
  }
  const root = document.documentElement
  root.setAttribute('data-theme', theme)
}

onMounted(async () => {
  await store.bootstrap()
  applyTheme(store.theme)
})

watch(
  () => store.theme,
  (theme) => applyTheme(theme)
)
</script>

<template>
  <div class="app-shell" :class="themeClass">
    <AppHeader />
    <div class="app-shell__body">
      <SideNav />
      <main class="app-shell__main">
        <ToolGrid />
      </main>
      <InsightPanel />
    </div>
  </div>
</template>
