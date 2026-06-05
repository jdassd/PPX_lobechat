<!-- ============================================================
     App.vue —— 重构后的外壳(固定侧边栏 + 工作区, 替代抽屉模式)
     ============================================================ -->
<script setup>
import { ref, computed, onMounted, onUnmounted, watchEffect } from 'vue'
import { TOOLS } from './config/tools'
import WindowTitleBar from './components/WindowTitleBar.vue'
import WindowResizeHandles from './components/WindowResizeHandles.vue'
import BtnUpdate from './components/BtnUpdate.vue'
import Sidebar from './components/Sidebar.vue'
import CommandPalette from './components/CommandPalette.vue'
import HomeLauncher from './components/home/HomeLauncher.vue'

// 各工具视图(已去抽屉化, 内容直接渲染进工作区)
import ImageTool from './components/image/ImageTool.vue'
import PdfTool from './components/pdf/PdfTool.vue'
import ExcelTool from './components/excel/ExcelTool.vue'
import TextTool from './components/text/TextTool.vue'
import VideoTool from './components/video/VideoTool.vue'
import FileTool from './components/file/FileTool.vue'
import AutomationTool from './components/automation/AutomationTool.vue'
import SealTool from './components/seal/SealTool.vue'
import FinanceTool from './components/finance/FinanceTool.vue'
import SystemCenter from './components/system/SystemCenter.vue'

const VIEWS = {
  image: ImageTool,
  pdf: PdfTool,
  excel: ExcelTool,
  text: TextTool,
  video: VideoTool,
  file: FileTool,
  automation: AutomationTool,
  seal: SealTool,
  finance: FinanceTool,
  system: SystemCenter,
}

const active = ref('home') // 'home' | 工具 id
const collapsed = ref(localStorage.getItem('ppx-sidebar-collapsed') === '1')
const cmdOpen = ref(false)
const theme = ref(localStorage.getItem('ppx-theme') || 'light')
const density = ref(localStorage.getItem('ppx-density') || 'regular')

const activeTool = computed(() => TOOLS.find((t) => t.id === active.value))
const activeView = computed(() => VIEWS[active.value])

watchEffect(() => {
  const el = document.documentElement
  el.dataset.theme = theme.value
  el.dataset.density = density.value
  el.classList.toggle('dark', theme.value === 'dark') // Element Plus 内部暗色变量
  localStorage.setItem('ppx-theme', theme.value)
  localStorage.setItem('ppx-density', density.value)
})

watchEffect(() => {
  localStorage.setItem('ppx-sidebar-collapsed', collapsed.value ? '1' : '0')
})

const onKey = (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    cmdOpen.value = !cmdOpen.value
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))

const go = (id) => { active.value = id }
const toggleTheme = () => { theme.value = theme.value === 'dark' ? 'light' : 'dark' }
</script>

<template>
  <div class="app-shell">
    <WindowTitleBar>
      <template #left>
        <div class="logo-area">
          <img class="logo-image" src="/logo.png" alt="" />
          <span class="logo-label">多功能工具箱</span>
        </div>
      </template>
      <template #right>
        <el-button text circle title="搜索 (Ctrl/⌘ + K)" @click="cmdOpen = true">
          <el-icon :size="18"><Search /></el-icon>
        </el-button>
        <el-button text circle title="切换主题" @click="toggleTheme">
          <el-icon :size="18"><component :is="theme === 'dark' ? 'Sunny' : 'Moon'" /></el-icon>
        </el-button>
        <BtnUpdate />
      </template>
    </WindowTitleBar>

    <WindowResizeHandles />

    <div class="app-body">
      <Sidebar :active="active" :collapsed="collapsed" @select="go" @toggle="collapsed = !collapsed" />

      <main class="workspace">
        <header v-if="active !== 'home' && activeTool" class="tool-bar">
          <span class="tool-ico" :style="{ background: activeTool.hue + '1f', color: activeTool.hue }">
            <el-icon :size="19"><component :is="activeTool.icon" /></el-icon>
          </span>
          <div class="tool-meta">
            <div class="tool-name">{{ activeTool.name }}</div>
            <div class="tool-desc">{{ activeTool.desc }}</div>
          </div>
          <span class="flex1" />
          <el-button text @click="go('home')">
            <el-icon><HomeFilled /></el-icon>&nbsp;返回首页
          </el-button>
        </header>

        <div class="tool-content">
          <HomeLauncher v-if="active === 'home'" @open="go" />
          <component :is="activeView" v-else />
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
.app-body { flex: 1; display: flex; min-height: 0; }
.workspace { flex: 1; min-width: 0; display: flex; flex-direction: column; }
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
.tool-meta { min-width: 0; }
.tool-name { font-size: 15px; font-weight: 700; line-height: 1.1; color: var(--ppx-text-primary); }
.tool-desc { font-size: 11.5px; color: var(--ppx-text-muted); }
.tool-content { flex: 1; min-height: 0; overflow: hidden; }
.flex1 { flex: 1; }
.logo-area { display: flex; align-items: center; gap: 9px; }
.logo-image { width: 18px; height: 18px; object-fit: contain; }
.logo-label { font-size: 13px; font-weight: 600; color: var(--ppx-text-secondary); }
</style>
