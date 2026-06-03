/**
 * usePdfApi —— PDF 工具集各子面板共享的调用层。
 *
 * 背景：
 *   原 PdfTool.vue 中存在一个中央 `callApi`，它统一处理：
 *     · pywebview 就绪校验（ensurePyReady）
 *     · 方法存在性校验
 *     · 共享的 loading 状态（state.loading）
 *     · 成功/失败提示（ElMessage）
 *     · 共享的操作日志（state.logs，最近 8 条）
 *
 *   拆分子组件后，loading 与 logs 仍需在所有面板之间共享（loading 是全局唯一开关，
 *   logs 显示在底部统一日志面板）。因此由壳层创建一个共享对象 `shared = { loading, logs }`，
 *   通过本 composable 提供给各子面板，保证调用行为与原实现 100% 等价。
 *
 * 用法：
 *   壳层：
 *     const shared = reactive({ loading: false, logs: [] })
 *     const pdfApi = usePdfApi(shared)
 *     provide('pdfApi', pdfApi)
 *     provide('pdfShared', shared)
 *   子面板：
 *     const { callApi, pickPdf, pickDir, openPath, ensurePyReady } = inject('pdfApi')
 *     const shared = inject('pdfShared')   // 读取 shared.loading 用于按钮 :loading
 */

import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

/**
 * 创建共享的 PDF 调用层。
 * @param {{ loading: boolean, logs: Array }} shared 壳层创建的共享响应式对象
 */
export function usePdfApi(shared) {
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
      ElMessage.error('当前客户端版本缺少 PDF 能力')
      return null
    }
    shared.loading = true
    try {
      // 统一封装：归一化返回 { ok, message, data }
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
   * 弹出 PDF 文件选择对话框，返回后端原始数组（未选择时返回空数组）。
   * @returns {Promise<Array>}
   */
  const pickPdf = async () => {
    if (!ensurePyReady()) return []
    const result = await callApiRaw('system_pyCreateFileDialog', ['PDF 文件 (*.pdf)'])
    return result && result.length ? result : []
  }

  /**
   * 弹出图片文件选择对话框，返回后端原始数组（未选择时返回空数组）。
   * @returns {Promise<Array>}
   */
  const pickImages = async () => {
    if (!ensurePyReady()) return []
    const files = await callApiRaw('system_pyCreateFileDialog', [
      '图片 (*.png;*.jpg;*.jpeg;*.webp;*.bmp)'
    ])
    return files?.length ? files : []
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
    pickPdf,
    pickImages,
    pickDir
  }
}
