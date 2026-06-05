<script setup>
import { ref } from 'vue'

const emit = defineEmits(['minimize', 'close'])

const isMinimizeHovered = ref(false)
const isCloseHovered = ref(false)

const handleMinimize = () => {
  emit('minimize')
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.minimize_window()
  }
}

const handleClose = () => {
  emit('close')
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.close_window()
  }
}
</script>

<template>
  <div class="window-titlebar">
    <div class="titlebar-drag-region pywebview-drag-region"></div>

    <!-- 左侧内容区域（logo 等） -->
    <div class="titlebar-content-left pywebview-drag-region">
      <slot name="left"></slot>
    </div>

    <!-- 中间可拖拽区域 -->
    <div class="titlebar-content-center pywebview-drag-region"></div>

    <!-- 右侧内容区域（更新按钮等） -->
    <div class="titlebar-content-right">
      <slot name="right"></slot>
    </div>

    <!-- 窗口控制按钮 -->
    <div class="titlebar-controls">
      <button
        class="titlebar-btn minimize-btn"
        @click="handleMinimize"
        @mouseenter="isMinimizeHovered = true"
        @mouseleave="isMinimizeHovered = false"
        aria-label="最小化"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
          <line x1="2" y1="6" x2="10" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
      <button
        class="titlebar-btn close-btn"
        @click="handleClose"
        @mouseenter="isCloseHovered = true"
        @mouseleave="isCloseHovered = false"
        aria-label="关闭"
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M2.5 2.5L9.5 9.5M9.5 2.5L2.5 9.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.window-titlebar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--titlebar-height, 35px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--ppx-bg-elevated);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--ppx-glass-border);
  z-index: 99999;
  user-select: none;
  -webkit-user-select: none;
  box-shadow: var(--ppx-shadow-sm);
}

.titlebar-drag-region {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  -webkit-app-region: drag;
  app-region: drag;
}

.titlebar-content-left {
  display: flex;
  align-items: center;
  padding-left: 18px;
  -webkit-app-region: no-drag;
  app-region: no-drag;
  position: relative;
  z-index: 1;
}

.titlebar-content-center {
  flex: 1;
  -webkit-app-region: drag;
  app-region: drag;
}

.titlebar-content-right {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-right: 8px;
  -webkit-app-region: no-drag;
  app-region: no-drag;
  position: relative;
  z-index: 1;
}

.titlebar-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 12px;
  -webkit-app-region: no-drag;
  app-region: no-drag;
  position: relative;
  z-index: 1;
}

.titlebar-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ppx-text-secondary);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.titlebar-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--ppx-bg-hover);
  border-radius: 6px;
  opacity: 0;
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.titlebar-btn:hover::before {
  opacity: 1;
}

.titlebar-btn:active {
  transform: scale(0.95);
}

.minimize-btn:hover {
  color: var(--ppx-text-primary);
}

.minimize-btn:hover::before {
  background: var(--ppx-bg-hover);
}

.close-btn:hover {
  color: #ffffff;
}

.close-btn:hover::before {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  opacity: 1;
}

.close-btn:active::before {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

/* SVG 图标动画 */
.titlebar-btn svg {
  position: relative;
  z-index: 1;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.minimize-btn:hover svg {
  transform: translateY(1px);
}

.close-btn:hover svg {
  transform: rotate(90deg);
}

/* 深色模式由根元素 data-theme 驱动，标题栏配色已使用 --ppx-* 变量自动适配 */

/* 响应式调整 */
@media (max-width: 600px) {
  .titlebar-content-left {
    padding-left: 12px;
  }

  .titlebar-content-right {
    gap: 8px;
    padding-right: 6px;
  }

  .titlebar-controls {
    gap: 6px;
    padding-right: 8px;
  }

  .titlebar-btn {
    width: 26px;
    height: 26px;
  }
}
</style>
