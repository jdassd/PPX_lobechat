<!-- gui/src/components/webauto/WebAutoTool.vue
     网页自动化采集 —— 引导式（小白友好）界面。
     通过顶部步骤条带用户走完：环境准备 → 点选内容 → 配置字段 → 导出设置 → 运行结果。
     全部后端调用走 @/utils/pyapi 封装；所有定时器在 onUnmounted 清理。 -->
<script setup>
import { reactive, ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Monitor,
  Pointer,
  Setting,
  Download,
  VideoPlay,
  CircleClose,
  Files,
  FolderOpened,
  Loading,
  CircleCheck
} from '@element-plus/icons-vue'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

/* ============================================================
 * 步骤定义
 * ============================================================ */
const STEP = {
  ENV: 0, // 环境准备
  PICK: 1, // 选择网页内容
  FIELDS: 2, // 配置字段与翻页
  EXPORT: 3, // 导出设置
  RUN: 4 // 运行与结果
}
const activeStep = ref(STEP.ENV)

/* ============================================================
 * 字段类型下拉（面向小白：把 href/src 翻译成人话）
 * ============================================================ */
const ATTR_OPTIONS = [
  { value: '', label: '文本内容' },
  { value: 'href', label: '链接地址' },
  { value: 'src', label: '图片地址' }
]
const attrLabel = (attr) => ATTR_OPTIONS.find((o) => o.value === (attr || ''))?.label || '文本内容'

/* ============================================================
 * 通用：桌面环境校验
 * ============================================================ */
const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

/* ============================================================
 * 定时器集中管理（便于统一清理）
 * ============================================================ */
const timers = reactive({ install: null, pick: null, run: null })
const clearTimer = (key) => {
  if (timers[key]) {
    clearInterval(timers[key])
    timers[key] = null
  }
}
const clearAllTimers = () => {
  Object.keys(timers).forEach(clearTimer)
}
// 离开本工具时，关闭可能仍开着的浏览器会话，避免残留进程
onUnmounted(() => {
  clearAllTimers()
  if (hasPyApi()) {
    try {
      pyCall('webauto_pick_cancel')
    } catch (e) {
      /* 忽略：卸载阶段的清理失败无影响 */
    }
  }
})

/* ============================================================
 * 步骤 0 —— 环境准备
 * ============================================================ */
const env = reactive({
  loading: false, // 首次检测中
  checked: false, // 是否已完成首次检测
  installed: false, // 浏览器内核是否已就绪
  ready: false, // playwright 依赖是否已安装
  installing: false, // 是否正在下载
  progress: 0, // 下载进度 0-100，-1=不确定
  installError: '', // 下载错误
  sources: [], // 后端返回的下载源列表
  source: 'npmmirror', // 当前选中的下载源 id（默认国内镜像）
  customHost: '' // 自定义下载地址
})

// 下载源兜底列表（与后端保持一致；后端不可用时使用）
const FALLBACK_SOURCES = [
  { id: 'npmmirror', name: '国内镜像 · npmmirror（淘宝，推荐国内用户）', host: 'https://cdn.npmmirror.com/binaries/playwright', region: 'cn' },
  { id: 'default', name: '官方默认（海外节点，自动选择）', host: '', region: 'global' },
  { id: 'azure', name: '海外官方 · Azure CDN', host: 'https://playwright.azureedge.net', region: 'global' },
  { id: 'akamai', name: '海外官方 · Akamai 节点', host: 'https://playwright-akamai.azureedge.net', region: 'global' },
  { id: 'verizon', name: '海外官方 · Verizon 节点', host: 'https://playwright-verizon.azureedge.net', region: 'global' }
]
// 自定义来源（始终追加在末尾，让用户可手填任意镜像）
const CUSTOM_SOURCE = { id: 'custom', name: '自定义地址…', host: '', region: 'custom' }

// 下拉可选项 = 后端源（或兜底）+ 自定义
const displaySources = computed(() => {
  const base = env.sources.length ? env.sources : FALLBACK_SOURCES
  return [...base, CUSTOM_SOURCE]
})

// 解析当前选中的实际下载地址（空串=官方默认）
const resolvedHost = computed(() => {
  if (env.source === 'custom') return env.customHost.trim()
  const s = displaySources.value.find((x) => x.id === env.source)
  return s ? s.host || '' : ''
})

// 拉取后端下载源列表（失败则用前端兜底）
const loadSources = async () => {
  try {
    const { ok, data } = await pyCall('webauto_download_sources')
    if (ok && data && Array.isArray(data.sources) && data.sources.length) {
      env.sources = data.sources
      // 当前选中项不在列表中时回退到第一项
      if (env.source !== 'custom' && !data.sources.some((s) => s.id === env.source)) {
        env.source = data.sources[0].id
      }
    }
  } catch (e) {
    /* 忽略：使用前端兜底列表 */
  }
}

// 检测后端状态
const checkEnv = async () => {
  if (!ensurePyReady()) return
  env.loading = true
  try {
    await loadSources()
    const { ok, data, message } = await pyCall('webauto_status')
    if (ok && data) {
      env.installed = !!data.installed
      env.ready = !!data.ready
    } else if (!ok) {
      ElMessage.error(message || '环境检测失败')
    }
  } catch (e) {
    ElMessage.error(e?.message || '环境检测失败，请确认桌面客户端')
  } finally {
    env.checked = true
    env.loading = false
    // 已就绪则直接进入下一步
    if (env.installed) activeStep.value = STEP.PICK
  }
}

// 开始下载浏览器内核
const startInstall = async () => {
  if (!ensurePyReady()) return
  if (env.source === 'custom' && !env.customHost.trim()) {
    ElMessage.warning('请填写自定义下载地址')
    return
  }
  env.installError = ''
  env.installing = true
  env.progress = -1
  try {
    const { ok, message } = await pyCall('webauto_install_browser', {
      host: resolvedHost.value,
      source: env.source
    })
    if (!ok) {
      env.installing = false
      ElMessage.error(message || '无法开始下载')
      return
    }
    pollInstall()
  } catch (e) {
    env.installing = false
    ElMessage.error(e?.message || '无法开始下载')
  }
}

// 轮询下载进度
const pollInstall = () => {
  clearTimer('install')
  timers.install = setInterval(async () => {
    try {
      const { ok, data } = await pyCall('webauto_install_status')
      if (!ok || !data) return
      env.installing = !!data.installing
      env.progress = typeof data.progress === 'number' ? data.progress : -1
      if (data.error) env.installError = data.error
      if (data.done) {
        clearTimer('install')
        env.installing = false
        if (data.success) {
          env.installed = true
          ElMessage.success('浏览器内核已就绪')
          activeStep.value = STEP.PICK
        } else {
          env.installError = data.error || '下载失败，请重试'
        }
      }
    } catch (e) {
      clearTimer('install')
      env.installing = false
      env.installError = e?.message || '下载过程中断'
    }
  }, 1000)
}

const installProgressText = computed(() => {
  if (env.progress < 0) return '正在下载，请耐心等待（无法预估剩余时间）…'
  return `已完成 ${env.progress}%`
})

/* ============================================================
 * 步骤 1 —— 点选网页内容
 * ============================================================ */
const pick = reactive({
  url: '',
  starting: false, // 点击“打开浏览器”后的过渡态
  active: false, // 点选会话是否进行中
  state: null, // webauto_pick_state 的原始 data
  finishing: false // 完成选取 loading
})

// 命中数量（容器/重复块）
const containerCount = computed(() => pick.state?.containerSample || 0)
const pickFields = computed(() => pick.state?.fields || [])
const hasPagination = computed(() => !!pick.state?.pagination)
const pickDetailActive = computed(() => !!pick.state?.detailActive)
const pickDetailFields = computed(() => pick.state?.detailFields || [])

// 打开浏览器开始点选
const startPick = async () => {
  if (!ensurePyReady()) return
  if (!pick.url.trim()) {
    ElMessage.warning('请先填写要采集的网址')
    return
  }
  pick.starting = true
  try {
    const { ok, message } = await pyCall('webauto_pick_start', { url: pick.url.trim() })
    if (!ok) {
      ElMessage.error(message || '打开浏览器失败')
      return
    }
    pick.active = true
    pick.state = null
    pollPick()
    ElMessage.success('浏览器已打开，请按提示在页面上点选')
  } catch (e) {
    ElMessage.error(e?.message || '打开浏览器失败')
  } finally {
    pick.starting = false
  }
}

// 轮询点选状态
const pollPick = () => {
  clearTimer('pick')
  timers.pick = setInterval(async () => {
    try {
      const { ok, data } = await pyCall('webauto_pick_state')
      if (!ok || !data) return
      pick.state = data
      if (data.error) {
        ElMessage.error(data.error)
      }
      // 用户在浏览器里点了“完成” → 自动收尾
      if (data.done) {
        clearTimer('pick')
        await finishPick()
      }
      // 浏览器被关掉等导致会话失效
      if (data.active === false && !data.done) {
        clearTimer('pick')
        pick.active = false
      }
    } catch (e) {
      // 轮询期间的偶发异常不打断用户，仅在严重时停止
    }
  }, 800)
}

// 完成选取 → 拉取 config
const finishPick = async () => {
  if (!ensurePyReady()) return
  if (pick.finishing) return
  pick.finishing = true
  clearTimer('pick')
  try {
    const { ok, data, message } = await pyCall('webauto_pick_finish')
    if (!ok || !data?.config) {
      ElMessage.error(message || '完成选取失败，请重试')
      return
    }
    applyConfig(data.config)
    // 浏览器会话保持打开：采集将在这个已通过 CF/登录的同一浏览器里就地进行
    pick.active = true
    ElMessage.success('已记住你选择的内容，浏览器先别关')
    activeStep.value = STEP.FIELDS
  } catch (e) {
    ElMessage.error(e?.message || '完成选取失败')
  } finally {
    pick.finishing = false
  }
}

// 取消点选
const cancelPick = async () => {
  clearTimer('pick')
  pick.active = false
  pick.state = null
  if (!hasPyApi()) return
  try {
    await pyCall('webauto_pick_cancel')
  } catch (e) {
    /* 忽略：取消失败不影响用户 */
  }
}

/* ============================================================
 * 步骤 2 —— 配置字段与翻页（本地可编辑的配置中心）
 * ============================================================ */
const config = reactive({
  url: '',
  container: '',
  fields: [], // [{name, selector, attr}]
  pagination: { enabled: false, selector: '', maxPages: 5, waitMs: 800 },
  detail: { enabled: false, linkField: '', fields: [] }, // detail.fields: [{name, selector, attr}]
  limit: 0
})

// 把后端 pick_finish 的 config 灌进本地状态
const applyConfig = (cfg) => {
  config.url = cfg.url || pick.url || ''
  config.container = cfg.container || ''
  config.fields = (cfg.fields || []).map((f) => ({
    id: f.id || '',
    name: f.name || '',
    selector: f.selector || '',
    attr: f.attr || ''
  }))
  const pg = cfg.pagination || {}
  config.pagination = {
    enabled: !!pg.enabled,
    selector: pg.selector || '',
    maxPages: pg.maxPages || 5,
    waitMs: pg.waitMs ?? 800
  }
  config.detail = {
    enabled: !!cfg.detailEnabled,
    linkField: cfg.detailLinkField || '',
    fields: (cfg.detailFields || []).map((f) => ({
      name: f.name || '',
      selector: f.selector || '',
      attr: f.attr || ''
    }))
  }
}

const removeField = (idx) => {
  config.fields.splice(idx, 1)
}
const removeDetailField = (idx) => {
  config.detail.fields.splice(idx, 1)
}

// 详情页“用哪个链接字段进入” —— 只取链接类字段
const linkFieldOptions = computed(() =>
  config.fields.filter((f) => f.attr === 'href').map((f) => f.name).filter(Boolean)
)

// 校验字段配置
// 注意：列表块（container）是可选的——后端无容器时会把整页当作 1 条记录采集，
// 点选工具条也提示“未选（整页当 1 条）”，故此处不强制要求 container。
const fieldsValid = computed(() => {
  if (!config.fields.length) return false
  return config.fields.every((f) => f.name.trim())
})

const goExport = () => {
  if (!fieldsValid.value) {
    ElMessage.warning('请至少选择一个字段，并给每个字段填写名称')
    return
  }
  if (config.detail.enabled && !config.detail.linkField) {
    ElMessage.warning('开启了详情页采集，请选择用哪个链接进入详情页')
    return
  }
  activeStep.value = STEP.EXPORT
}

/* ============================================================
 * 步骤 3 —— 导出设置
 * ============================================================ */
const exportCfg = reactive({
  format: 'excel', // 'excel' | 'word'
  outputDir: '',
  fileName: '采集结果'
})

const selectOutputDir = async () => {
  if (!ensurePyReady()) return
  try {
    const dir = await callApiRaw('system_pySelectDirDialog', exportCfg.outputDir)
    if (dir) exportCfg.outputDir = dir
  } catch (e) {
    ElMessage.error(e?.message || '选择目录失败')
  }
}

const exportValid = computed(() => !!exportCfg.outputDir && !!exportCfg.fileName.trim())

const goRun = () => {
  if (!exportValid.value) {
    ElMessage.warning('请填写输出目录和文件名')
    return
  }
  activeStep.value = STEP.RUN
}

/* ============================================================
 * 步骤 4 —— 运行与结果
 * ============================================================ */
const run = reactive({
  starting: false,
  running: false,
  done: false,
  success: false,
  page: 0,
  total: 0,
  columns: [], // 动态列
  rows: [], // 预览数据
  outputPath: '',
  error: ''
})

// 组装采集选项：只传可编辑项（字段名/类型、翻页与详情开关、上限、导出）。
// 选择器全部由后端从同一浏览器会话的点选状态里取，无需前端来回传递。
const buildCollectOptions = () => ({
  fields: config.fields.map((f) => ({ id: f.id, name: f.name.trim(), attr: f.attr })),
  pagination: {
    enabled: config.pagination.enabled,
    maxPages: config.pagination.maxPages,
    waitMs: config.pagination.waitMs
  },
  detail: {
    enabled: config.detail.enabled,
    linkField: config.detail.linkField
  },
  limit: config.limit,
  export: {
    format: exportCfg.format,
    outputDir: exportCfg.outputDir,
    fileName: exportCfg.fileName.trim()
  }
})

const startRun = async () => {
  if (!ensurePyReady()) return
  run.starting = true
  run.done = false
  run.success = false
  run.error = ''
  run.page = 0
  run.total = 0
  run.columns = []
  run.rows = []
  run.outputPath = ''
  try {
    const { ok, message } = await pyCall('webauto_collect_start', buildCollectOptions())
    if (!ok) {
      ElMessage.error(message || '启动采集失败')
      return
    }
    run.running = true
    pollRun()
  } catch (e) {
    ElMessage.error(e?.message || '启动采集失败')
  } finally {
    run.starting = false
  }
}

const pollRun = () => {
  clearTimer('run')
  timers.run = setInterval(async () => {
    try {
      const { ok, data } = await pyCall('webauto_run_status')
      if (!ok || !data) return
      run.running = !!data.running
      run.page = data.page || 0
      run.total = data.total || 0
      if (Array.isArray(data.columns)) run.columns = data.columns
      if (Array.isArray(data.rows)) run.rows = data.rows
      if (data.error) run.error = data.error
      if (data.done) {
        clearTimer('run')
        run.running = false
        run.done = true
        run.success = !!data.success
        run.outputPath = data.outputPath || ''
        if (run.success) {
          ElMessage.success('采集完成！')
        } else {
          ElMessage.error(run.error || '采集失败')
        }
      }
    } catch (e) {
      /* 轮询偶发异常忽略 */
    }
  }, 1000)
}

const stopRun = async () => {
  if (!hasPyApi()) return
  try {
    await pyCall('webauto_stop')
    clearTimer('run')
    run.running = false
    ElMessage.info('已停止采集')
  } catch (e) {
    ElMessage.error(e?.message || '停止失败')
  }
}

const openOutput = () => {
  if (!run.outputPath) return
  if (!ensurePyReady()) return
  callApiRaw('system_pyOpenFile', run.outputPath)
}

// 结束整个任务：关闭采集浏览器会话
const closeSession = async () => {
  clearTimer('pick')
  clearTimer('run')
  if (!hasPyApi()) {
    pick.active = false
    return
  }
  try {
    await pyCall('webauto_pick_cancel')
    pick.active = false
    ElMessage.success('已关闭采集浏览器')
  } catch (e) {
    ElMessage.error(e?.message || '关闭失败')
  }
}

/* ============================================================
 * 顶部步骤条配置
 * ============================================================ */
const STEPS_META = [
  { title: '准备环境', desc: '下载浏览器内核' },
  { title: '点选内容', desc: '在网页上点要采集的部分' },
  { title: '核对字段', desc: '改字段名、设置翻页' },
  { title: '导出设置', desc: '存成 Excel / Word' },
  { title: '开始采集', desc: '运行并查看结果' }
]

// 步骤切换时停止无关轮询
const goStep = (step) => {
  if (step !== STEP.ENV) clearTimer('install')
  if (step !== STEP.PICK) clearTimer('pick')
  if (step !== STEP.RUN) clearTimer('run')
  activeStep.value = step
}

// 进入组件即检测一次环境
checkEnv()
</script>

<template>
  <div class="webauto">
    <!-- 顶部步骤条 -->
    <header class="wa-head">
      <div class="wa-title">
        <el-icon :size="20"><Monitor /></el-icon>
        <span>网页自动化采集</span>
      </div>
      <el-steps :active="activeStep" align-center finish-status="success" class="wa-steps">
        <el-step v-for="s in STEPS_META" :key="s.title" :title="s.title" :description="s.desc" />
      </el-steps>
    </header>

    <!-- 内容滚动区 -->
    <div class="wa-body">
      <!-- ============ 步骤 0：环境准备 ============ -->
      <section v-show="activeStep === STEP.ENV" class="wa-step">
        <div v-if="env.loading" class="wa-empty">
          <el-icon class="spin" :size="28"><Loading /></el-icon>
          <p>正在检测运行环境…</p>
        </div>

        <template v-else>
          <!-- 依赖没装好 -->
          <el-alert
            v-if="env.checked && !env.ready"
            type="warning"
            :closable="false"
            show-icon
            title="还缺少必要的程序组件"
            description="请先在命令行运行 pnpm run init 安装依赖后再使用本功能。"
          />

          <!-- 需要下载浏览器内核 -->
          <div v-else class="wa-card">
            <div class="wa-card-head">
              <el-icon :size="22"><Download /></el-icon>
              <div>
                <h4>首次使用需要下载浏览器内核</h4>
                <p class="muted">大约 150MB，只需下载这一次，以后就不用再下了。</p>
              </div>
            </div>

            <!-- 下载来源（国内/海外多地址，避免下载失败） -->
            <div class="wa-source">
              <div class="wa-source-row">
                <span class="wa-source-label">下载来源</span>
                <el-select v-model="env.source" :disabled="env.installing" class="wa-source-select">
                  <el-option v-for="s in displaySources" :key="s.id" :label="s.name" :value="s.id" />
                </el-select>
              </div>
              <el-input
                v-if="env.source === 'custom'"
                v-model="env.customHost"
                class="mt8"
                placeholder="镜像地址，如 https://cdn.npmmirror.com/binaries/playwright"
                :disabled="env.installing"
                clearable
              />
              <p class="muted hint mt8">国内用户建议选「npmmirror」镜像；若某个来源下载失败，换一个再试即可。</p>
            </div>

            <template v-if="env.installing || env.progress >= 0">
              <el-progress
                :percentage="env.progress < 0 ? 100 : env.progress"
                :indeterminate="env.progress < 0"
                :duration="2"
                :stroke-width="14"
                :status="env.installError ? 'exception' : undefined"
              />
              <p class="muted hint">{{ installProgressText }}</p>
            </template>

            <el-alert
              v-if="env.installError"
              type="error"
              :closable="false"
              show-icon
              :title="env.installError"
              class="mt"
            />

            <div class="wa-actions">
              <el-button
                type="primary"
                :icon="Download"
                :loading="env.installing"
                @click="startInstall"
              >
                {{ env.installing ? '正在下载…' : (env.installError ? '重新下载' : '开始下载') }}
              </el-button>
              <el-button :icon="Loading" plain :disabled="env.installing" @click="checkEnv">重新检测</el-button>
            </div>
          </div>
        </template>
      </section>

      <!-- ============ 步骤 1：点选网页内容 ============ -->
      <section v-show="activeStep === STEP.PICK" class="wa-step">
        <div class="wa-card">
          <h4>第一步：告诉我要采集哪个网页</h4>
          <p class="muted">输入网址，点下面的按钮会自动打开一个浏览器，你只要用鼠标点选页面上想要的内容即可。</p>
          <div class="field-row mt">
            <el-input v-model="pick.url" placeholder="例如：https://example.com/list" clearable :disabled="pick.active" />
            <el-button
              type="primary"
              :icon="Pointer"
              :loading="pick.starting"
              :disabled="pick.active"
              @click="startPick"
            >
              打开浏览器开始点选
            </el-button>
          </div>
        </div>

        <!-- 操作说明 -->
        <el-alert type="info" :closable="false" show-icon class="mt" title="操作很简单，跟着做就行：">
          <ol class="guide">
            <li>浏览器打开后，左上角会出现一个小工具条。</li>
            <li>① 先点一条列表里的内容（比如一条新闻），系统会自动找出页面上所有相似的条目。</li>
            <li>② 再挨个点你想要的内容（标题、价格、图片、链接…），每点一个就会变成一个字段。</li>
            <li>③ 如果列表有“下一页”，点一下那个翻页按钮（不需要可跳过）。</li>
            <li>④ 全部点完后，回到这里点“完成选取”。</li>
          </ol>
        </el-alert>

        <!-- 实时点选状态 -->
        <div v-if="pick.active" class="wa-card mt">
          <div class="wa-card-head between">
            <h4 class="row-center"><el-icon class="spin" :size="16"><Loading /></el-icon>&nbsp;正在点选中…</h4>
            <div>
              <el-button :icon="CircleClose" plain @click="cancelPick">取消</el-button>
              <el-button type="success" :icon="CircleCheck" :loading="pick.finishing" @click="finishPick">完成选取</el-button>
            </div>
          </div>

          <!-- 列表块 -->
          <div class="pick-block">
            <span class="pick-label">已识别列表块：</span>
            <el-tag v-if="pick.state?.container" type="success" effect="light">
              共找到 {{ containerCount }} 条相似内容
            </el-tag>
            <el-tag v-else type="info" effect="plain">还没点选 —— 请先点一条列表内容</el-tag>
          </div>

          <!-- 字段 -->
          <div class="pick-block">
            <span class="pick-label">已选字段：</span>
            <template v-if="pickFields.length">
              <el-tag v-for="f in pickFields" :key="f.id" class="pick-tag" effect="light">
                {{ f.name || '未命名' }}（{{ attrLabel(f.attr) }}）<em v-if="f.sample">：{{ f.sample }}</em>
              </el-tag>
            </template>
            <el-tag v-else type="info" effect="plain">还没选字段</el-tag>
          </div>

          <!-- 翻页 -->
          <div class="pick-block">
            <span class="pick-label">翻页按钮：</span>
            <el-tag v-if="hasPagination" type="success" effect="light">已设置</el-tag>
            <el-tag v-else type="info" effect="plain">未设置（可选）</el-tag>
          </div>

          <!-- 详情字段 -->
          <div v-if="pickDetailActive" class="pick-block">
            <span class="pick-label">详情页字段：</span>
            <template v-if="pickDetailFields.length">
              <el-tag v-for="f in pickDetailFields" :key="'d-' + f.id" class="pick-tag" type="warning" effect="light">
                {{ f.name || '未命名' }}（{{ attrLabel(f.attr) }}）
              </el-tag>
            </template>
            <el-tag v-else type="info" effect="plain">还没选</el-tag>
          </div>
        </div>
      </section>

      <!-- ============ 步骤 2：配置字段与翻页 ============ -->
      <section v-show="activeStep === STEP.FIELDS" class="wa-step">
        <!-- 列表块（每条记录的范围，可选） -->
        <div class="wa-card">
          <div class="wa-card-head between">
            <h4>列表块（每条记录的范围）</h4>
            <el-button v-if="config.container" type="danger" link size="small" @click="config.container = ''">清除</el-button>
          </div>
          <p v-if="config.container" class="mono muted">{{ config.container }}</p>
          <p v-else class="muted">未选列表块 —— 将把整页当作 1 条记录采集。如需逐条采集列表，请点“上一步”先点选“①列表块”。</p>
        </div>

        <div class="wa-card mt">
          <h4>第二步：核对要采集的内容</h4>
          <p class="muted">字段名可以改成你看得懂的叫法。类型决定取“文字”还是“链接/图片地址”。</p>

          <el-table :data="config.fields" border size="small" class="mt" empty-text="还没有字段，请回到上一步点选">
            <el-table-column label="字段名" min-width="140">
              <template #default="{ row }">
                <el-input v-model="row.name" size="small" placeholder="如：标题" />
              </template>
            </el-table-column>
            <el-table-column label="类型" width="130">
              <template #default="{ row }">
                <el-select v-model="row.attr" size="small">
                  <el-option v-for="o in ATTR_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="定位规则" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="mono muted">{{ row.selector }}</span>
              </template>
            </el-table-column>
            <el-table-column label="示例" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="muted">{{ row.sample || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70" align="center">
              <template #default="{ $index }">
                <el-button type="danger" link size="small" @click="removeField($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 翻页设置 -->
        <div class="wa-card mt">
          <div class="wa-card-head between">
            <h4>自动翻页</h4>
            <el-switch v-model="config.pagination.enabled" />
          </div>
          <p class="muted">开启后，会自动点“下一页”继续采集，直到达到设定的页数。</p>
          <el-form v-if="config.pagination.enabled" label-width="120px" class="mt">
            <el-form-item label="最多采集页数">
              <el-input-number v-model="config.pagination.maxPages" :min="1" :max="500" />
            </el-form-item>
            <el-form-item label="每页等待(毫秒)">
              <el-input-number v-model="config.pagination.waitMs" :min="0" :max="20000" :step="100" />
              <span class="muted hint">&nbsp;网速慢可以调大一点，让页面加载完再采。</span>
            </el-form-item>
            <el-form-item label="下一页按钮">
              <span class="mono muted">{{ config.pagination.selector || '（未设置）' }}</span>
            </el-form-item>
          </el-form>
        </div>

        <!-- 详情页设置 -->
        <div class="wa-card mt">
          <div class="wa-card-head between">
            <h4>进入详情页采集更多内容</h4>
            <el-switch v-model="config.detail.enabled" />
          </div>
          <p class="muted">开启后，会点开每一条的详情页，再采集里面更详细的内容。</p>
          <template v-if="config.detail.enabled">
            <el-form label-width="120px" class="mt">
              <el-form-item label="用哪个链接进入">
                <el-select v-model="config.detail.linkField" placeholder="选择一个链接字段" style="width: 220px">
                  <el-option v-for="name in linkFieldOptions" :key="name" :label="name" :value="name" />
                </el-select>
                <span v-if="!linkFieldOptions.length" class="muted hint">&nbsp;没有“链接”类型的字段，请在上方把某个字段类型改成“链接地址”。</span>
              </el-form-item>
            </el-form>
            <el-table :data="config.detail.fields" border size="small" empty-text="详情页暂无字段（在点选时进入详情页选取）">
              <el-table-column label="字段名" min-width="140">
                <template #default="{ row }">
                  <el-input v-model="row.name" size="small" placeholder="如：正文" />
                </template>
              </el-table-column>
              <el-table-column label="类型" width="130">
                <template #default="{ row }">
                  <el-select v-model="row.attr" size="small">
                    <el-option v-for="o in ATTR_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="定位规则" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="mono muted">{{ row.selector }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" align="center">
                <template #default="{ $index }">
                  <el-button type="danger" link size="small" @click="removeDetailField($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </div>

        <!-- 采集上限 -->
        <div class="wa-card mt">
          <el-form label-width="120px">
            <el-form-item label="最多采集条数">
              <el-input-number v-model="config.limit" :min="0" :max="100000" :step="50" />
              <span class="muted hint">&nbsp;填 0 表示不限制。建议先抓少量（如 50 条）试试效果，别一次抓太多。</span>
            </el-form-item>
          </el-form>
        </div>

        <div class="wa-actions end">
          <el-button @click="goStep(STEP.PICK)">上一步</el-button>
          <el-button type="primary" :icon="Setting" @click="goExport">下一步：导出设置</el-button>
        </div>
      </section>

      <!-- ============ 步骤 3：导出设置 ============ -->
      <section v-show="activeStep === STEP.EXPORT" class="wa-step">
        <div class="wa-card">
          <h4>第三步：采集结果存成什么</h4>
          <el-form label-width="120px" class="mt">
            <el-form-item label="保存格式">
              <el-radio-group v-model="exportCfg.format">
                <el-radio-button label="excel">Excel 表格</el-radio-button>
                <el-radio-button label="word">Word 文档</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="保存到">
              <div class="field-row">
                <el-input v-model="exportCfg.outputDir" placeholder="选择一个文件夹" readonly />
                <el-button :icon="FolderOpened" @click="selectOutputDir">选择目录</el-button>
              </div>
            </el-form-item>
            <el-form-item label="文件名">
              <el-input v-model="exportCfg.fileName" placeholder="如：采集结果" clearable>
                <template #append>{{ exportCfg.format === 'excel' ? '.xlsx' : '.docx' }}</template>
              </el-input>
            </el-form-item>
          </el-form>
        </div>

        <div class="wa-actions end">
          <el-button @click="goStep(STEP.FIELDS)">上一步</el-button>
          <el-button type="primary" :icon="VideoPlay" @click="goRun">下一步：开始采集</el-button>
        </div>
      </section>

      <!-- ============ 步骤 4：运行与结果 ============ -->
      <section v-show="activeStep === STEP.RUN" class="wa-step">
        <div class="wa-card">
          <div class="wa-card-head between">
            <h4>第四步：开始采集</h4>
            <div>
              <el-button
                v-if="!run.running"
                type="primary"
                :icon="VideoPlay"
                :loading="run.starting"
                @click="startRun"
              >
                {{ run.done ? '重新采集' : '开始采集' }}
              </el-button>
              <el-button v-else type="danger" :icon="CircleClose" @click="stopRun">停止</el-button>
            </div>
          </div>

          <!-- 进度 -->
          <div v-if="run.running || run.done || run.total" class="run-stat">
            <el-tag v-if="run.running" type="primary" effect="light">
              <el-icon class="spin"><Loading /></el-icon>&nbsp;采集中
            </el-tag>
            <el-tag v-else-if="run.done && run.success" type="success" effect="light">已完成</el-tag>
            <el-tag v-else-if="run.done" type="danger" effect="light">已结束</el-tag>
            <span class="muted">已采集 <b>{{ run.total }}</b> 条 · 第 <b>{{ run.page }}</b> 页</span>
          </div>

          <el-alert
            v-if="run.error"
            type="error"
            :closable="false"
            show-icon
            :title="run.error"
            class="mt"
          />

          <!-- 完成后的导出文件 -->
          <div v-if="run.done && run.success && run.outputPath" class="wa-result mt">
            <el-icon :size="20" color="var(--el-color-success)"><CircleCheck /></el-icon>
            <span class="muted">文件已保存到：</span>
            <span class="mono">{{ run.outputPath }}</span>
            <el-button type="primary" link :icon="Files" @click="openOutput">打开文件</el-button>
          </div>
        </div>

        <!-- 结果预览 -->
        <div class="wa-card mt">
          <h4>结果预览</h4>
          <el-table
            v-if="run.columns.length"
            :data="run.rows"
            border
            size="small"
            height="360"
            class="mt"
            empty-text="暂无数据"
          >
            <el-table-column
              v-for="col in run.columns"
              :key="col"
              :prop="col"
              :label="col"
              min-width="140"
              show-overflow-tooltip
            />
          </el-table>
          <div v-else class="wa-empty">
            <el-icon :size="26"><Files /></el-icon>
            <p>点击“开始采集”后，这里会实时显示抓到的数据。</p>
          </div>
        </div>

        <div class="wa-actions between">
          <el-button @click="goStep(STEP.EXPORT)">上一步</el-button>
          <el-button v-if="pick.active" type="warning" plain :icon="CircleClose" @click="closeSession">
            完成并关闭浏览器
          </el-button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.webauto {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--ppx-bg-base);
}

/* 顶部 */
.wa-head {
  flex-shrink: 0;
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--ppx-glass-border);
  background: var(--ppx-glass-bg);
}
.wa-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  margin-bottom: 14px;
}
.wa-steps {
  max-width: 920px;
  margin: 0 auto;
}

/* 内容滚动区 */
.wa-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 22px 24px 40px;
}
.wa-step {
  max-width: 880px;
  margin: 0 auto;
}

/* 卡片 */
.wa-card {
  background: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  padding: 20px 22px;
}
.wa-card h4 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}
.wa-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  color: var(--ppx-text-primary);
}
.wa-card-head.between {
  justify-content: space-between;
}
.wa-card-head h4 {
  margin: 0;
}

/* 文案 */
.muted {
  color: var(--ppx-text-muted);
  font-size: 13px;
}
.hint {
  font-size: 12.5px;
}
.mono {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  word-break: break-all;
}

/* 行布局 */
.field-row {
  display: flex;
  gap: 10px;
  width: 100%;
}
.field-row .el-input {
  flex: 1;
}
.row-center {
  display: inline-flex;
  align-items: center;
}

/* 间距工具类 */
.mt {
  margin-top: 14px;
}
.mt8 {
  margin-top: 8px;
}

/* 下载来源选择 */
.wa-source {
  margin-top: 14px;
  padding: 12px 14px;
  background: var(--ppx-bg-hover);
  border-radius: var(--ppx-radius-md, 8px);
}
.wa-source-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.wa-source-label {
  flex: 0 0 auto;
  font-size: 13px;
  font-weight: 500;
  color: var(--ppx-text-secondary);
}
.wa-source-select {
  flex: 1;
}

/* 操作区 */
.wa-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}
.wa-actions.end {
  justify-content: flex-end;
  margin-top: 22px;
}

/* 操作指南列表 */
.guide {
  margin: 6px 0 0;
  padding-left: 18px;
  line-height: 1.9;
  font-size: 13px;
  color: var(--ppx-text-secondary);
}

/* 点选实时状态块 */
.pick-block {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px dashed var(--ppx-glass-border);
}
.pick-label {
  font-size: 13px;
  color: var(--ppx-text-secondary);
  font-weight: 500;
  min-width: 92px;
}
.pick-tag em {
  font-style: normal;
  color: var(--ppx-text-muted);
}

/* 运行统计 */
.run-stat {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  font-size: 13px;
}
.run-stat b {
  color: var(--ppx-text-primary);
}

/* 结果文件行 */
.wa-result {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 14px;
  background: var(--ppx-bg-hover);
  border-radius: var(--ppx-radius-md, 8px);
}

/* 空态 */
.wa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}

/* 加载旋转 */
.spin {
  animation: wa-spin 1s linear infinite;
}
@keyframes wa-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
