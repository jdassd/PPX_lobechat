/**
 * pyapi.js —— 统一的 pywebview 调用封装层
 *
 * 背景：
 *   - 前端通过 window.pywebview.api.<method>(...) 调用 Python 后端。
 *   - 后端返回格式不统一：
 *       · 大多数模块返回 { code: 0, msg: '...', ...data }（code === 0 表示成功）
 *       · system 等模块返回 { success: true, message: '...', ...data }（success === true 表示成功）
 *   - pywebview 就绪时机不确定（需等待 `pywebviewready` 事件）。
 *
 * 本模块对外提供：
 *   1) isPyEnv()       —— 当前是否处于 pywebview 桌面环境（window.pywebview 是否存在）。
 *   2) hasPyApi()      —— window.pywebview.api 是否已注入（同步、即时判断）。
 *   3) whenPyReady()   —— 等待 window.pywebview.api 就绪，返回 Promise<true>，超时/非桌面环境则 reject。
 *   4) callApi()       —— 等就绪 → 调用后端方法 → 归一化返回。
 *   5) callApiRaw()    —— 等就绪 → 调用后端方法 → 返回后端原始结果（不做归一化），用于特殊场景。
 *   6) normalizeResult() —— 将后端原始返回归一化为 { ok, message, data }。
 *
 * 归一化约定（callApi 的返回值）：
 *   {
 *     ok: boolean,      // code === 0 || success === true 时为 true
 *     message: string,  // 优先取 msg，其次 message，否则 ''
 *     data: any         // 后端原始返回（保留全部字段，调用方可继续读取 res.data.xxx）
 *   }
 *
 * 错误处理约定：
 *   callApi **不会 throw 业务失败**（后端返回 ok:false 时仍返回 { ok:false, ... }），
 *   仅在以下"环境/调用层"异常时 **throw Error（带 message）**：
 *     · 非桌面环境（window.pywebview 不存在）或就绪超时；
 *     · 指定的 method 在 api 上不存在；
 *     · 后端方法执行抛出异常（网络/序列化/Python 端异常）。
 *   这样调用方可用一次 try/catch 统一捕获"调不通"的情况，
 *   而用 res.ok 判断"调通了但业务失败"，与既有组件逻辑等价。
 */

import { beginApiTask, isTaskMethod, settleApiTask, observeTask, hydrateBackendTasks } from './taskCenter'
import { consumeIncomingFiles, currentIncomingAssets, getDraft } from './workspace'

// 轮询兜底间隔（毫秒）与默认超时（毫秒）
const POLL_INTERVAL = 50
const DEFAULT_TIMEOUT = 15000
/**
 * 当前是否处于 pywebview 桌面环境。
 * @returns {boolean}
 */
export function isPyEnv() {
  return typeof window !== 'undefined' && !!window.pywebview
}

/**
 * window.pywebview.api 是否已就绪（同步判断，不等待）。
 * @returns {boolean}
 */
export function hasPyApi() {
  return typeof window !== 'undefined' && !!(window.pywebview && window.pywebview.api)
}

/**
 * 等待 window.pywebview.api 就绪。
 * 策略：若已就绪立即 resolve；否则同时监听 `pywebviewready` 事件 + 轮询兜底 + 超时保护。
 *
 * @param {number} [timeout=DEFAULT_TIMEOUT] 超时时间（毫秒）
 * @returns {Promise<true>} 就绪时 resolve(true)；非桌面环境或超时则 reject(Error)
 */
export function whenPyReady(timeout = DEFAULT_TIMEOUT) {
  // 已就绪：直接返回
  if (hasPyApi()) {
    return Promise.resolve(true)
  }

  // 非浏览器/非桌面环境：无法就绪
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('当前不在桌面客户端环境中'))
  }

  return new Promise((resolve, reject) => {
    let settled = false
    let timer = null
    let poller = null

    const cleanup = () => {
      window.removeEventListener('pywebviewready', onReady)
      if (timer) clearTimeout(timer)
      if (poller) clearInterval(poller)
    }

    const done = () => {
      if (settled) return
      settled = true
      cleanup()
      resolve(true)
    }

    const fail = (message) => {
      if (settled) return
      settled = true
      cleanup()
      reject(new Error(message))
    }

    const onReady = () => {
      // pywebviewready 触发后 api 仍可能稍晚注入，做一次确认
      if (hasPyApi()) {
        done()
      }
    }

    // 监听就绪事件
    window.addEventListener('pywebviewready', onReady)

    // 轮询兜底（事件可能在监听前已触发）
    poller = setInterval(() => {
      if (hasPyApi()) done()
    }, POLL_INTERVAL)

    // 超时保护
    timer = setTimeout(() => {
      if (hasPyApi()) {
        done()
      } else if (isPyEnv()) {
        fail('桌面客户端 API 初始化超时')
      } else {
        fail('当前不在桌面客户端环境中，该功能仅在桌面客户端可用')
      }
    }, timeout)
  })
}

/**
 * 将后端原始返回归一化为 { ok, message, data }。
 * 同时兼容 { code, msg, ... } 与 { success, message, ... } 两种格式。
 *
 * @param {any} res 后端原始返回
 * @returns {{ ok: boolean, message: string, data: any }}
 */
export function normalizeResult(res) {
  // 后端未返回有效对象时，视为失败但不阻断调用方
  if (res === null || res === undefined || typeof res !== 'object') {
    return { ok: false, message: '', data: res }
  }
  const ok = res.code === 0 || res.success === true
  // 文案优先级：msg（多数模块） > message（system 等模块）
  const message = res.msg !== undefined && res.msg !== null ? res.msg : res.message !== undefined && res.message !== null ? res.message : ''
  return { ok, message, data: res }
}

/**
 * 调用后端方法并归一化返回。
 *
 * @param {string} method 后端方法名（window.pywebview.api 上的方法）
 * @param  {...any} args  传给后端方法的参数
 * @returns {Promise<{ ok: boolean, message: string, data: any }>}
 * @throws {Error} 非桌面环境/就绪超时/方法不存在/后端执行异常 时抛出（带 message）
 */
export async function callApi(method, ...args) {
  let taskId = null
  try {
    await whenPyReady()
    const api = window.pywebview.api
    if (method.startsWith('excel_') && args[0]) args[0] = { ...(getDraft('excel/options') || {}), ...args[0] }
    if (typeof api[method] !== 'function') {
      throw new Error(`当前客户端缺少能力：${method}`)
    }
    const previewOnly = args[0]?.dryRun || ['file_search', 'file_deduplicate', 'excel_column_profile'].includes(method) || (method === 'ocr_table' && args[0]?.saveFile === false) || (method === 'seal_generate' && args[0]?.mode !== 'export')
    const shouldQueue = isTaskMethod(method) && !previewOnly && typeof api.task_submit === 'function' && typeof api.task_get === 'function'
    if (shouldQueue) {
      const submitted = normalizeResult(await api.task_submit({ method, args }))
      if (!submitted.ok) return submitted
      taskId = submitted.data.taskId
      beginApiTask(method, args, taskId)
      const task = await observeTask(taskId)
      hydrateBackendTasks([task])
      if (task.status === 'canceled' || task.status === 'interrupted') {
        return { ok: false, message: task.message || '任务已取消', data: task.result }
      }
      return normalizeResult(task.result)
    }
    taskId = previewOnly ? null : beginApiTask(method, args)
    // 未进入队列的方法仍按原调用方式同步执行。
    const res = normalizeResult(await api[method](...args))
    settleApiTask(taskId, res)
    return res
  } catch (error) {
    if (!window.pywebview?.api?.task_submit) settleApiTask(taskId, null, error)
    throw error
  }
}

/**
 * 调用后端方法，返回后端原始结果（不做归一化）。
 * 用于：返回值非 {code}/{success} 约定结构的方法（如文件对话框返回数组、字符串、布尔等）。
 *
 * @param {string} method 后端方法名
 * @param  {...any} args  传给后端方法的参数
 * @returns {Promise<any>} 后端原始返回
 * @throws {Error} 非桌面环境/就绪超时/方法不存在 时抛出（带 message）
 */
export async function callApiRaw(method, ...args) {
  await whenPyReady()
  if (method === 'system_pyCreateFileDialog' && currentIncomingAssets.value.length) return consumeIncomingFiles()
  const api = window.pywebview.api
  if (typeof api[method] !== 'function') {
    throw new Error(`当前客户端缺少能力：${method}`)
  }
  return api[method](...args)
}
