<script setup>
import { ref, onMounted } from 'vue'
import LauncherGrid from './components/LauncherGrid.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const showSettings = ref(false)
const currentHotkey = ref('ctrl+shift+space')

onMounted(async () => {
  // 获取当前快捷键配置
  try {
    const result = await window.pywebview.api.get_current_hotkey()
    if (result.code === 200) {
      currentHotkey.value = result.data.hotkey
    }
  } catch (error) {
    console.error('获取快捷键配置失败:', error)
  }
})

const closeWindow = () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.toggle_window_visibility()
  }
}

const minimizeWindow = () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.toggle_window_visibility()
  }
}

const toggleSettings = () => {
  showSettings.value = !showSettings.value
}
</script>

<template>
  <div class="launcher-container">
    <!-- 自定义标题栏 -->
    <div class="title-bar" data-drag>
      <div class="title">
        <span class="title-icon">🚀</span>
        <span>QuickLauncher</span>
      </div>
      <div class="title-buttons">
        <button class="title-btn settings-btn" @click="toggleSettings" title="设置">
          ⚙️
        </button>
        <button class="title-btn minimize-btn" @click="minimizeWindow" title="最小化">
          ─
        </button>
        <button class="title-btn close-btn" @click="closeWindow" title="关闭">
          ✕
        </button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <LauncherGrid v-if="!showSettings" />
      <SettingsPanel v-else :current-hotkey="currentHotkey" @close="toggleSettings" />
    </div>

    <!-- 快捷键提示 -->
    <div class="hotkey-hint">
      按 <kbd>{{ currentHotkey.toUpperCase() }}</kbd> 隐藏
    </div>
  </div>
</template>

<style scoped>
.launcher-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}

.title-bar {
  height: 40px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  -webkit-app-region: drag;
}

.title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  user-select: none;
}

.title-icon {
  font-size: 18px;
}

.title-buttons {
  display: flex;
  gap: 8px;
  -webkit-app-region: no-drag;
}

.title-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.title-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.05);
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.8);
}

.main-content {
  flex: 1;
  overflow: hidden;
}

.hotkey-hint {
  padding: 8px 15px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

kbd {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 11px;
  margin: 0 2px;
}
</style>

