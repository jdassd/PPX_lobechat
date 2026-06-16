/**
 * useWordApi —— Word 工具集各子面板共享的调用层。
 *
 * 与 usePdfApi 一致：统一处理 pywebview 就绪校验、共享 loading、消息提示、操作日志，
 * 并提供 Word(.docx) 文件 / 目录选择对话框封装。
 */

import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

/**
 * 创建共享的 Word 调用层。
 * @param {{ loading: boolean, logs: Array }} shared 壳层创建的共享响应式对象
 */
export function useWordApi(shared) {
  const ensurePyReady = () => {
    if (!hasPyApi()) {
      ElMessage.warning('该功能需在桌面客户端中使用')
      return false
    }
    return true
  }

  const pushLog = (type, message, action, detail) => {
    shared.logs.unshift({
      id: Date.now() + Math.random(),
      type,
      message,
      action,
      detail,
      time: new Date().toLocaleTimeString()
    })
    if (shared.logs.length > 8) {
      shared.logs.pop()
    }
  }

  const callApi = async (method, payload) => {
    if (!ensurePyReady()) return null
    if (!window.pywebview.api[method]) {
      ElMessage.error('当前客户端版本缺少 Word 能力')
      return null
    }
    shared.loading = true
    try {
      const result = await pyCall(method, payload)
      if (result.ok) {
        ElMessage.success(result.message || '操作成功')
        pushLog('success', result.message || '操作成功', method, result.data)
        return result.data
      } else {
        const msg = result.message || '操作失败'
        ElMessage.error(msg)
        pushLog('warning', msg, method, result.data)
        return null
      }
    } catch (error) {
      ElMessage.error(error.message || '执行失败')
      pushLog('danger', error.message || '执行失败', method)
      return null
    } finally {
      shared.loading = false
    }
  }

  const openPath = async (path) => {
    if (!path || !ensurePyReady()) return
    callApiRaw('system_pyOpenFile', path)
  }

  /**
   * 弹出 Word 文件选择对话框，返回后端原始数组（未选择时返回空数组）。
   * @returns {Promise<Array>}
   */
  const pickDocx = async () => {
    if (!ensurePyReady()) return []
    const result = await callApiRaw('system_pyCreateFileDialog', ['Word 文档 (*.docx)'])
    return result && result.length ? result : []
  }

  /**
   * 弹出目录选择对话框，返回所选目录（取消则返回空字符串）。
   * @param {string} current 当前目录，作为对话框默认路径
   * @returns {Promise<string>}
   */
  const pickDir = async (current = '') => {
    if (!ensurePyReady()) return ''
    const dir = await callApiRaw('system_pySelectDirDialog', current || '')
    return dir || ''
  }

  return {
    ensurePyReady,
    pushLog,
    callApi,
    openPath,
    pickDocx,
    pickDir
  }
}
