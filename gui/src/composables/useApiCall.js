/**
 * useApiCall.js —— 基于 pyapi 的组合式函数
 *
 * 目标：把组件里高度重复的「设置 loading → callApi → 成功 ElMessage.success / 失败 ElMessage.error → 复位 loading」
 *       这一套模式收敛成一行调用。
 *
 * 提供：
 *   1) useApiCall()  —— 通用调用器，自带 loading 管理与成功/失败消息提示。
 *   2) usePyReady()  —— 跟踪 pywebview 就绪状态的响应式封装（替代各组件手写的 apiReady ref）。
 *
 * 设计原则：
 *   - 不改变任何既有交互语义：成功/失败的文案与提示行为保持等价；
 *   - 可控制是否弹出成功/失败提示（successMessage:false / errorMessage:false），
 *     以适配「失败由调用方自行处理」或「成功不提示」的组件；
 *   - run() 返回归一化结果 { ok, message, data }，失败/异常时返回 { ok:false, ... } 而非 throw，
 *     方便在模板事件处理器里直接 await 使用。
 */

import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi, whenPyReady, hasPyApi } from '@/utils/pyapi'

/**
 * 通用 API 调用器。
 *
 * @param {object} [defaults] 默认配置（可被单次 run 的 options 覆盖）
 * @param {boolean} [defaults.successMessage=true] 成功时是否弹 ElMessage.success
 * @param {boolean} [defaults.errorMessage=true]   失败/异常时是否弹 ElMessage.error
 * @param {string}  [defaults.successText]         成功提示文案（缺省时用后端 message，再缺省用「操作成功」）
 * @param {string}  [defaults.errorText]           失败提示文案（缺省时用后端 message，再缺省用「操作失败」）
 *
 * @returns {{
 *   loading: import('vue').Ref<boolean>,
 *   run: (method: string, args?: any[], options?: object) => Promise<{ok:boolean,message:string,data:any}>
 * }}
 */
export function useApiCall(defaults = {}) {
  const loading = ref(false)

  /**
   * 发起一次调用。
   * @param {string} method 后端方法名
   * @param {any[]} [args=[]] 传给后端方法的参数数组
   * @param {object} [options] 单次配置，覆盖 defaults
   * @returns {Promise<{ok:boolean,message:string,data:any}>}
   */
  const run = async (method, args = [], options = {}) => {
    const cfg = { successMessage: true, errorMessage: true, ...defaults, ...options }
    loading.value = true
    try {
      const result = await callApi(method, ...args)
      if (result.ok) {
        if (cfg.successMessage) {
          ElMessage.success(cfg.successText || result.message || '操作成功')
        }
      } else {
        if (cfg.errorMessage) {
          ElMessage.error(cfg.errorText || result.message || '操作失败')
        }
      }
      return result
    } catch (error) {
      // 环境/调用层异常（非桌面、超时、方法缺失、后端抛错）
      const message = cfg.errorText || error?.message || '执行失败'
      if (cfg.errorMessage) {
        ElMessage.error(message)
      }
      return { ok: false, message, data: null }
    } finally {
      loading.value = false
    }
  }

  return { loading, run }
}

/**
 * 跟踪 pywebview 就绪状态。
 * @returns {{ apiReady: import('vue').Ref<boolean>, ready: Promise<boolean> }}
 *   apiReady 为响应式就绪状态；ready 为可 await 的就绪 Promise（超时/非桌面环境会 reject）。
 */
export function usePyReady() {
  const apiReady = ref(hasPyApi())
  const ready = whenPyReady()
    .then(() => {
      apiReady.value = true
      return true
    })
    .catch((err) => {
      apiReady.value = false
      throw err
    })
  return { apiReady, ready }
}
