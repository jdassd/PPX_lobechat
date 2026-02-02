<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  currentHotkey: {
    type: String,
    default: 'ctrl+shift+space'
  }
})

const emit = defineEmits(['close'])

const config = ref({
  hotkey: props.currentHotkey,
  window_always_on_top: true,
  auto_start: false,
  theme: 'dark'
})

const newHotkey = ref(props.currentHotkey)
const isSaving = ref(false)

onMounted(async () => {
  await loadConfig()
})

const loadConfig = async () => {
  try {
    const result = await window.pywebview.api.get_launcher_config()
    if (result.code === 200) {
      config.value = result.data
      newHotkey.value = result.data.hotkey
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const saveConfig = async () => {
  try {
    isSaving.value = true
    
    // 更新快捷键
    if (newHotkey.value !== config.value.hotkey) {
      const hotkeyResult = await window.pywebview.api.update_hotkey(newHotkey.value)
      if (hotkeyResult.code !== 200) {
        alert('更新快捷键失败: ' + hotkeyResult.message)
        return
      }
      config.value.hotkey = newHotkey.value
    }
    
    // 更新其他配置
    const result = await window.pywebview.api.update_launcher_config(config.value)
    if (result.code === 200) {
      alert('保存成功！')
    } else {
      alert('保存失败: ' + result.message)
    }
  } catch (error) {
    console.error('保存配置失败:', error)
    alert('保存失败')
  } finally {
    isSaving.value = false
  }
}

const closeSettings = () => {
  emit('close')
}
</script>

<template>
  <div class="settings-panel">
    <div class="settings-header">
      <h2>⚙️ 设置</h2>
      <button class="close-btn" @click="closeSettings">✕</button>
    </div>

    <div class="settings-content">
      <!-- 快捷键设置 -->
      <div class="setting-group">
        <h3>全局快捷键</h3>
        <p class="setting-desc">用于显示/隐藏启动器窗口</p>
        <input 
          v-model="newHotkey" 
          type="text" 
          class="hotkey-input"
          placeholder="例如: ctrl+shift+space"
        />
        <p class="setting-hint">支持的组合键: ctrl, shift, alt, 字母和数字</p>
      </div>

      <!-- 窗口设置 -->
      <div class="setting-group">
        <h3>窗口设置</h3>
        <label class="checkbox-label">
          <input 
            v-model="config.window_always_on_top" 
            type="checkbox"
          />
          <span>窗口始终置顶</span>
        </label>
      </div>

      <!-- 启动设置 -->
      <div class="setting-group">
        <h3>启动设置</h3>
        <label class="checkbox-label">
          <input 
            v-model="config.auto_start" 
            type="checkbox"
          />
          <span>开机自动启动</span>
        </label>
        <p class="setting-hint">需要管理员权限</p>
      </div>

      <!-- 关于 -->
      <div class="setting-group">
        <h3>关于</h3>
        <p class="about-text">QuickLauncher v1.0.0</p>
        <p class="about-text">基于 PPX 框架构建的快速应用启动器</p>
      </div>

      <!-- 保存按钮 -->
      <div class="setting-actions">
        <button 
          class="save-btn" 
          @click="saveConfig"
          :disabled="isSaving"
        >
          {{ isSaving ? '保存中...' : '💾 保存设置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.settings-header h2 {
  color: white;
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.8);
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.setting-group {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 15px;
}

.setting-group h3 {
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.setting-desc {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  margin: 0 0 15px 0;
}

.setting-hint {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  margin: 8px 0 0 0;
}

.hotkey-input {
  width: 100%;
  padding: 12px 15px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-family: monospace;
  transition: all 0.2s;
}

.hotkey-input:focus {
  outline: none;
  border-color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.15);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
  cursor: pointer;
  margin-bottom: 10px;
}

.checkbox-label:last-child {
  margin-bottom: 0;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.about-text {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  margin: 5px 0;
}

.setting-actions {
  margin-top: 20px;
}

.save-btn {
  width: 100%;
  padding: 15px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.save-btn:active:not(:disabled) {
  transform: translateY(0);
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 自定义滚动条 */
.settings-content::-webkit-scrollbar {
  width: 8px;
}

.settings-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.settings-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.settings-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
