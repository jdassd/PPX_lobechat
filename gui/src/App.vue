<script setup>
import { ref, onMounted } from 'vue'
import WindowTitleBar from './components/WindowTitleBar.vue'
import WindowResizeHandles from './components/WindowResizeHandles.vue'
import BtnUpdate from './components/BtnUpdate.vue'
import HomeLauncher from './components/home/HomeLauncher.vue'
import PdfTool from './components/pdf/PdfTool.vue'
import ExcelTool from './components/excel/ExcelTool.vue'
import SealTool from './components/seal/SealTool.vue'
import SystemCenter from './components/system/SystemCenter.vue'
import ImageTool from './components/image/ImageTool.vue'
import TextTool from './components/text/TextTool.vue'
import VideoTool from './components/video/VideoTool.vue'
import FileTool from './components/file/FileTool.vue'
import FinanceTool from './components/finance/FinanceTool.vue'
import AutomationTool from './components/automation/AutomationTool.vue'

const isLoaded = ref(false)

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
})

const pdfToolVisible = ref(false)
const excelToolVisible = ref(false)
const sealToolVisible = ref(false)
const systemToolVisible = ref(false)
const imageToolVisible = ref(false)
const textToolVisible = ref(false)
const videoToolVisible = ref(false)
const fileToolVisible = ref(false)
const financeToolVisible = ref(false)
const automationToolVisible = ref(false)

const onOpenTool = (toolId) => {
  const visibilityMap = {
    excel: excelToolVisible,
    pdf: pdfToolVisible,
    seal: sealToolVisible,
    system: systemToolVisible,
    image: imageToolVisible,
    text: textToolVisible,
    video: videoToolVisible,
    file: fileToolVisible,
    finance: financeToolVisible,
    automation: automationToolVisible
  }

  if (visibilityMap[toolId]) {
    visibilityMap[toolId].value = true
  }
}
</script>

<template>
  <div class="app-container" :class="{ loaded: isLoaded }">
    <!-- 自定义窗口控制顶栏（融合原有顶栏内容） -->
    <WindowTitleBar>
      <!-- 左侧：Logo 和标题 -->
      <template #left>
        <div class="logo-area">
          <div class="logo-icon">
            <img class="logo-image" src="/logo.png" alt="PPX Logo" />
          </div>
          <span class="logo-label">工具箱</span>
        </div>
      </template>

      <!-- 右侧：更新按钮 -->
      <template #right>
        <BtnUpdate />
      </template>
    </WindowTitleBar>

    <WindowResizeHandles />

    <!-- 背景装饰 -->
    <div class="bg-decorations">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="grid-pattern"></div>
      <div class="grain"></div>
    </div>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <HomeLauncher @open="onOpenTool" />
    </div>
  </div>

  <!-- 工具弹窗 -->
  <ImageTool v-model="imageToolVisible" />
  <TextTool v-model="textToolVisible" />
  <VideoTool v-model="videoToolVisible" />
  <FileTool v-model="fileToolVisible" />
  <AutomationTool v-model="automationToolVisible" />
  <PdfTool v-model="pdfToolVisible" />
  <ExcelTool v-model="excelToolVisible" />
  <SealTool v-model="sealToolVisible" />
  <SystemCenter v-model="systemToolVisible" />
  <FinanceTool v-model="financeToolVisible" />
</template>

<style scoped>
/* =============================
   Atelier Paper UI Shell
   ============================= */

.app-container {
  width: 100%;
  height: 100%;
  background: var(--ppx-bg-deep);
  position: relative;
  overflow: hidden;
  --titlebar-height: 35px;
}

.app-container::before {
  content: '';
  position: absolute;
  inset: -20% -10% -10% -10%;
  background:
    radial-gradient(55% 55% at 10% 10%, rgba(249, 115, 22, 0.18) 0%, transparent 60%),
    radial-gradient(40% 40% at 90% 0%, rgba(14, 165, 164, 0.2) 0%, transparent 65%),
    radial-gradient(45% 45% at 60% 100%, rgba(132, 204, 22, 0.16) 0%, transparent 60%);
  z-index: 0;
  pointer-events: none;
}

.bg-decorations {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.5;
  animation: float 18s ease-in-out infinite;
}

.orb-1 {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, rgba(249, 115, 22, 0.25) 0%, transparent 70%);
  top: -140px;
  left: -120px;
  animation-delay: 0s;
}

.orb-2 {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(14, 165, 164, 0.28) 0%, transparent 70%);
  top: 40%;
  right: -120px;
  animation-delay: -6s;
}

.orb-3 {
  width: 320px;
  height: 320px;
  background: radial-gradient(circle, rgba(132, 204, 22, 0.24) 0%, transparent 70%);
  bottom: -120px;
  left: 35%;
  animation-delay: -12s;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(44, 36, 29, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(44, 36, 29, 0.05) 1px, transparent 1px);
  background-size: 80px 80px;
  mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
  opacity: 0.4;
}

.grain {
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(44, 36, 29, 0.03), rgba(44, 36, 29, 0.03) 1px, transparent 1px, transparent 4px),
    repeating-linear-gradient(90deg, rgba(44, 36, 29, 0.02), rgba(44, 36, 29, 0.02) 1px, transparent 1px, transparent 3px);
  opacity: 0.4;
  mix-blend-mode: multiply;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(-20px, 10px) scale(0.95); }
  75% { transform: translate(10px, 30px) scale(1.02); }
}

.main-wrapper {
  width: 100%;
  height: calc(100% - var(--titlebar-height, 35px)); /* 减去顶栏高度 */
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
  margin-top: var(--titlebar-height, 35px); /* 为融合后的自定义窗口控制顶栏留出空间 */
}

/* Logo 区域样式（现在在 WindowTitleBar 中） */
.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--ppx-shadow-sm);
  position: relative;
  overflow: hidden;
}

.logo-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.logo-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  letter-spacing: 0.5px;
}

/* ??? */
@media (max-width: 600px) {
  .app-container {
    --titlebar-height: 48px;
  }
}
</style>
