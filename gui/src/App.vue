<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watchEffect } from 'vue'
import { List, Moon, Search, SetUp, Sunny } from '@element-plus/icons-vue'

import { toolById } from './config/tools'
import { pushRecent } from './utils/recent'
import BtnUpdate from './components/BtnUpdate.vue'
import CommandPalette from './components/CommandPalette.vue'
import HomeLauncher from './components/home/HomeLauncher.vue'
import ModuleCenter from './components/ModuleCenter.vue'
import Sidebar from './components/Sidebar.vue'
import TaskCenter from './components/TaskCenter.vue'
import WindowResizeHandles from './components/WindowResizeHandles.vue'
import WindowTitleBar from './components/WindowTitleBar.vue'

import ExcelTool from './components/excel/ExcelTool.vue'
import DocumentTool from './components/document/DocumentTool.vue'
import FileTool from './components/file/FileTool.vue'
import ImageTool from './components/image/ImageTool.vue'
import MindMapTool from './components/mindmap/MindMapTool.vue'
import MaintenanceTool from './components/maintenance/MaintenanceTool.vue'
import PdfTool from './components/pdf/PdfTool.vue'
import SealTool from './components/seal/SealTool.vue'
import SystemCenter from './components/system/SystemCenter.vue'
import TextTool from './components/text/TextTool.vue'
import VideoTool from './components/video/VideoTool.vue'
import WebAutoTool from './components/webauto/WebAutoTool.vue'
import WordTool from './components/word/WordTool.vue'
import WorkflowTool from './components/workflow/WorkflowTool.vue'

const VIEWS = {
  image: ImageTool,
  pdf: PdfTool,
  word: WordTool,
  excel: ExcelTool,
  document: DocumentTool,
  text: TextTool,
  video: VideoTool,
  file: FileTool,
  webauto: WebAutoTool,
  mindmap: MindMapTool,
  maintenance: MaintenanceTool,
  seal: SealTool,
  workflow: WorkflowTool,
  system: SystemCenter
}

const active = ref('home')
const activeFeature = ref('')
const collapsed = ref(localStorage.getItem('ppx-sidebar-collapsed') === '1')
const cmdOpen = ref(false)
const theme = ref(localStorage.getItem('ppx-theme') || 'light')
const density = ref(localStorage.getItem('ppx-density') || 'regular')

const activeTool = computed(() => toolById(active.value))
const activeView = computed(() => VIEWS[active.value])

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
  const id = typeof target === 'string' ? target : target?.tool || target?.id
  if (!id) return
  const feature = typeof target === 'object' ? target.feature || '' : ''
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
    const route = ['pdf'].includes(extension)
      ? { tool: 'pdf', feature: 'pages' }
      : ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'tif', 'tiff'].includes(extension)
        ? { tool: 'image', feature: 'convert' }
        : ['doc', 'docx'].includes(extension)
          ? { tool: 'word', feature: 'split' }
          : ['xls', 'xlsx', 'xlsm', 'csv'].includes(extension)
            ? { tool: 'excel', feature: 'structure' }
            : ['mp4', 'mov', 'mkv', 'avi', 'webm'].includes(extension)
              ? { tool: 'video', feature: 'convert' }
              : ['txt', 'md', 'markdown', 'json', 'log'].includes(extension)
                ? { tool: 'text', feature: extension === 'json' ? 'json' : 'transform' }
                : { tool: 'file', feature: 'search' }
    go(route)
    await nextTick()
    window.dispatchEvent(new CustomEvent('ppx-open-files', { detail: { files } }))
  } catch {
    // Ignore malformed launch parameters; the normal home page remains usable.
  }
}

onMounted(routeLaunchFiles)

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
          <span class="logo-label">多功能工具箱 <small>2.5</small></span>
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
          <el-tag v-if="activeTool.badge" class="tool-badge" size="small" effect="plain">{{ activeTool.badge }}</el-tag>
        </header>

        <div class="tool-content">
          <HomeLauncher v-if="active === 'home'" @open="go" @search="cmdOpen = true" @modules="go('modules')" @tasks="go('tasks')" />
          <TaskCenter v-else-if="active === 'tasks'" @open="go" />
          <ModuleCenter v-else-if="active === 'modules'" @open="go" />
          <component :is="activeView" v-else-if="activeView" :initial-tab="activeFeature" />
          <el-empty v-else description="该模块暂不可用" />
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
