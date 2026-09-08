import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi, hasPyApi } from '@/utils/pyapi'

// A response belongs to the input snapshot that started it, never the next file.
export function useExcelRequest(onLog = () => {}) {
  const pending = ref(0)
  const error = ref('')
  const loading = computed(() => pending.value > 0)
  const fail = (message) => {
    error.value = message
    ElMessage.error(message)
  }
  const request = async (method, payload, current = () => true) => {
    pending.value += 1
    if (current()) error.value = ''
    try {
      if (!hasPyApi()) throw new Error('请在桌面客户端中打开 Excel 工具后重试')
      const result = await callApi(method, payload)
      if (!current()) return null
      if (!result.ok) throw new Error(result.message || '操作失败，请检查文件与所选工作表后重试')
      onLog('success', result.message || '操作成功', method)
      return result.data
    } catch (cause) {
      if (current()) {
        const message = cause.message || '调用失败，请检查文件是否可读后重试'
        fail(message)
        onLog('danger', message, method)
      }
      return null
    } finally {
      pending.value -= 1
    }
  }
  const safely = async (action) => {
    try {
      if (!hasPyApi()) throw new Error('请在桌面客户端中打开 Excel 工具后重试')
      return await action()
    } catch (cause) {
      fail(cause.message || '操作失败，请重试')
      return null
    }
  }
  return { loading, error, request, safely }
}
