import { reactive } from 'vue'

import { callApi, hasPyApi } from '@/utils/pyapi'

const state = reactive({
  loading: false,
  loaded: false,
  error: '',
  platform: '',
  capabilities: {}
})

export function useCapabilities() {
  const loadCapabilities = async (force = false) => {
    if (state.loading || (state.loaded && !force)) return
    if (!hasPyApi()) {
      state.error = '请在桌面客户端中检测本机能力'
      return
    }
    state.loading = true
    state.error = ''
    try {
      const res = await callApi('capabilities_get')
      if (!res.ok) throw new Error(res.message || '能力检测失败')
      state.platform = res.data.platform || ''
      state.capabilities = res.data.capabilities || {}
      state.loaded = true
    } catch (error) {
      state.error = error?.message || '能力检测失败'
    } finally {
      state.loading = false
    }
  }

  return { state, loadCapabilities }
}
