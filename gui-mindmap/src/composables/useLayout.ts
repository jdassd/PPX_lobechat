import { watch } from 'vue'
import { useMindmapStore } from '../stores/mindmap'
import { computeLayout } from '../utils/layout'

export function useLayout() {
  const store = useMindmapStore()

  function recalculate() {
    if (store.root) {
      store.layout = computeLayout(store.root)
    }
  }

  return { recalculate }
}
