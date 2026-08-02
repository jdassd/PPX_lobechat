import { ref, watch } from 'vue'

export function useInitialTab(tabs, source, fallback) {
  const activeTab = ref(fallback || tabs[0]?.name || '')
  watch(
    source,
    (value) => {
      if (value && tabs.some((tab) => tab.name === value)) activeTab.value = value
    },
    { immediate: true }
  )
  return activeTab
}
