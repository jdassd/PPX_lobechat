<script setup>
import { computed, defineAsyncComponent, nextTick, onMounted, onUnmounted, ref, watchEffect } from 'vue'
import WorkspacePresets from './components/shared/WorkspacePresets.vue'
import ResultActions from './components/shared/ResultActions.vue'
import { currentIncomingAssets as incomingAssets, clearIncomingFiles, workspaceTool } from './utils/workspace'
import { loadOperationCatalog, tasks } from './utils/taskCenter'
import { List, Moon, Search, SetUp, Sunny } from '@element-plus/icons-vue'

import { toolById } from './config/tools'
import { pushRecent } from './utils/recent'
import BtnUpdate from './components/BtnUpdate.vue'
import CommandPalette from './components/CommandPalette.vue'
const HomeLauncher = defineAsyncComponent(() => import('./components/home/HomeLauncher.vue'))
const ModuleCenter = defineAsyncComponent(() => import('./components/ModuleCenter.vue'))
import Sidebar from './components/Sidebar.vue'
const TaskCenter = defineAsyncComponent(() => import('./components/TaskCenter.vue'))
import WindowResizeHandles from './components/WindowResizeHandles.vue'
import WindowTitleBar from './components/WindowTitleBar.vue'

const ExcelTool = defineAsyncComponent(() => import('./components/excel/ExcelTool.vue'))
const ConversionCenter = defineAsyncComponent(() => import('./components/conversion/ConversionCenter.vue'))
const DocumentTool = defineAsyncComponent(() => import('./components/document/DocumentTool.vue'))
const FileTool = defineAsyncComponent(() => import('./components/file/FileTool.vue'))
const ImageTool = defineAsyncComponent(() => import('./components/image/ImageTool.vue'))
const MaintenanceTool = defineAsyncComponent(() => import('./components/maintenance/MaintenanceTool.vue'))
const PdfTool = defineAsyncComponent(() => import('./components/pdf/PdfTool.vue'))
const SealTool = defineAsyncComponent(() => import('./components/seal/SealTool.vue'))
const SystemCenter = defineAsyncComponent(() => import('./components/system/SystemCenter.vue'))
const TextTool = defineAsyncComponent(() => import('./components/text/TextTool.vue'))
const VideoTool = defineAsyncComponent(() => import('./components/video/VideoTool.vue'))
const WebAutoTool = defineAsyncComponent(() => import('./components/webauto/WebAutoTool.vue'))
const WordTool = defineAsyncComponent(() => import('./components/word/WordTool.vue'))
const WorkflowTool = defineAsyncComponent(() => import('./components/workflow/WorkflowTool.vue'))

const VIEWS = {
  home: HomeLauncher,
  tasks: TaskCenter,
  modules: ModuleCenter,
  conversion: ConversionCenter,
  image: ImageTool,
  pdf: PdfTool,
  word: WordTool,
  excel: ExcelTool,
  document: DocumentTool,
  text: TextTool,
  video: VideoTool,
  file: FileTool,
  webauto: WebAutoTool,
  maintenance: MaintenanceTool,
  seal: SealTool,
  workflow: WorkflowTool,
  system: SystemCenter
}

const active = ref('home')
watchEffect(() => {
  workspaceTool.value = active.value
})
const activeFeature = ref('')
const collapsed = ref(localStorage.getItem('ppx-sidebar-collapsed') === '1')
const cmdOpen = ref(false)
const theme = ref(localStorage.getItem('ppx-theme') || 'light')
const density = ref(localStorage.getItem('ppx-density') || 'regular')

const activeTool = computed(() => toolById(active.value))
const activeView = computed(() => VIEWS[active.value] || HomeLauncher)
const latestOutputs = computed(() => tasks.value.find((task) => task.tool === active.value && task.outputs?.length)?.outputs || [])
onMounted(() => {
  if (window.pywebview?.api) loadOperationCatalog()
  else window.addEventListener('pywebviewready', loadOperationCatalog, { once: true })
})

const LEGACY_CONVERSION_ROUTES = {
  'image:convert': { tool: 'conversion', feature: 'universal' },
  'image:pdf': { tool: 'conversion', feature: 'images-pdf' },
  'pdf:image': { tool: 'conversion', feature: 'universal' },
  'pdf:word': { tool: 'conversion', feature: 'universal' },
  'video:convert': { tool: 'conversion', feature: 'universal' }
}

const CONVERSION_EXTENSIONS = new Set([
  'jpg',
  'jpeg',
  'png',
  'webp',
  'gif',
  'avif',
  'tif',
  'tiff',
  'bmp',
  'heic',
  'heif',
  'ico',
  'tga',
  'cr2',
  'cr3',
  'crw',
  'nef',
  'arw',
  'dng',
  'raf',
  'rw2',
  'orf',
  'pef',
  'srw',
  '3fr',
  'erf',
  'fff',
  'iiq',
  'kdc',
  'mef',
  'mrw',
  'x3f',
  'txt',
  'md',
  'markdown',
  'html',
  'htm',
  'json',
  'csv',
  'log',
  'xml',
  'yaml',
  'yml',
  'epub',
  'mobi',
  'doc',
  'docx',
  'odt',
  'rtf',
  'wps',
  'wpt',
  'wpd',
  'ofd',
  'xls',
  'xlsx',
  'xlsm',
  'ods',
  'tsv',
  'et',
  'ett',
  'ppt',
  'pptx',
  'odp',
  'dps',
  'dpt',
  'pdf',
  'mp3',
  'wav',
  'flac',
  'm4a',
  'aac',
  'ogg',
  'opus',
  'wma',
  'mp4',
  'mov',
  'mkv',
  'webm',
  'avi',
  'm4v',
  'wmv',
  'flv',
  'zip'
])

watchEffect(() => {
  const el = document.documentElement
  el.dataset.theme = theme.value
  el.dataset.density = density.value
  el.classList.toggle('dark', theme.value === 'dark')
  localStorage.setItem('ppx-theme', theme.value)
  localStorage.setItem('ppx-density', density.value)
})

watchEffect(() => {
  localStorage.setItem('ppx-sidebar-collapsed', collapsed.value ? '1' : '0')
})

const onKey = (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    cmdOpen.value = !cmdOpen.value
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

const go = (target) => {
  const rawId = typeof target === 'string' ? target : target?.tool || target?.id
  const rawFeature = typeof target === 'object' ? target.feature || '' : ''
  const redirect = LEGACY_CONVERSION_ROUTES[`${rawId}:${rawFeature}`]
  const id = redirect?.tool || rawId
  if (!id) return
  const feature = redirect?.feature || rawFeature
  active.value = id
  activeFeature.value = feature
  if (toolById(id)) pushRecent(id, feature)
}

const routeLaunchFiles = async () => {
  const encoded = new URLSearchParams(window.location.search).get('openFiles')
  if (!encoded) return
  try {
    const files = JSON.parse(encoded)
    if (!Array.isArray(files) || !files.length) return
    window.__PPX_OPEN_FILES__ = files
    const extension = String(files[0]).split('.').pop().toLowerCase()
    const route = CONVERSION_EXTENSIONS.has(extension) ? { tool: 'conversion', feature: 'universal' } : { tool: 'file', feature: 'search' }
    go(route)
    await nextTick()
    window.dispatchEvent(new CustomEvent('ppx-open-files', { detail: { files } }))
  } catch {
    // Ignore malformed launch parameters; the normal home page remains usable.
  }
}

onMounted(routeLaunchFiles)

const onNavigate = (event) => go(event.detail)
onMounted(() => window.addEventListener('ppx-navigate', onNavigate))
onUnmounted(() => window.removeEventListener('ppx-navigate', onNavigate))

const toggleTheme = () => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <div class="app-shell">
    <WindowTitleBar>
      <template #left>
        <div class="logo-area">
          <img class="logo-image" src="/logo.png" alt="" />
          <span class="logo-label">多功能工具箱 <small>2.8.0</small></span>
        </div>
      </template>
      <template #right>
        <el-button text circle title="任务中心" aria-label="打开任务中心" @click="go('tasks')">
          <el-icon :size="18"><List /></el-icon>
        </el-button>
        <el-button text circle title="模块管理" aria-label="打开模块管理" @click="go('modules')">
          <el-icon :size="18"><SetUp /></el-icon>
        </el-button>
        <el-button text circle title="搜索 (Ctrl/⌘ + K)" aria-label="搜索功能" @click="cmdOpen = true">
          <el-icon :size="18"><Search /></el-icon>
        </el-button>
        <el-button text circle title="切换主题" aria-label="切换主题" @click="toggleTheme">
          <el-icon :size="18"><component :is="theme === 'dark' ? Sunny : Moon" /></el-icon>
        </el-button>
        <BtnUpdate />
      </template>
    </WindowTitleBar>

    <WindowResizeHandles />

    <div class="app-body">
      <Sidebar :active="active" :collapsed="collapsed" @select="go" @toggle="collapsed = !collapsed" />

      <main class="workspace">
        <header v-if="activeTool" class="tool-bar">
          <span class="tool-ico" :style="{ background: activeTool.hue + '1f', color: activeTool.hue }">
            <el-icon :size="19"><component :is="activeTool.icon" /></el-icon>
          </span>
          <div class="tool-meta">
            <div class="tool-name">{{ activeTool.name }}</div>
            <div class="tool-desc">{{ activeTool.desc }}</div>
          </div>
          <WorkspacePresets :tool="active" />
          <ResultActions :assets="latestOutputs" />
          <el-tag v-if="activeTool.badge" class="tool-badge" size="small" effect="plain">{{ activeTool.badge }}</el-tag>
        </header>

        <div class="tool-content">
          <el-alert v-if="incomingAssets.length" :title="`已带入 ${incomingAssets.length} 个结果；点击此工具的选择文件按钮即可使用`" type="info" show-icon @close="clearIncomingFiles" />
          <transition name="view" mode="out-in">
            <KeepAlive>
              <component :is="activeView" :key="active" :initial-tab="activeFeature" @open="go" @search="cmdOpen = true" @modules="go('modules')" @tasks="go('tasks')" />
            </KeepAlive>
          </transition>
        </div>
      </main>
    </div>

    <CommandPalette v-model="cmdOpen" @select="go" />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding-top: var(--titlebar-height, 35px);
  box-sizing: border-box;
  background: var(--ppx-bg-deep);
  --titlebar-height: 35px;
}
.app-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.workspace {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.tool-bar {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 22px;
  border-bottom: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-elevated);
}
.tool-ico {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tool-meta {
  min-width: 0;
}
.tool-name {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--ppx-text-primary);
}
.tool-desc {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--ppx-text-muted);
}
.tool-badge {
  margin-left: auto;
}
.tool-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.logo-area {
  display: flex;
  align-items: center;
  gap: 9px;
}
.logo-image {
  width: 18px;
  height: 18px;
  object-fit: contain;
}
.logo-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ppx-text-secondary);
}
.logo-label small {
  margin-left: 4px;
  color: var(--accent);
  font-size: 10px;
}
</style>
