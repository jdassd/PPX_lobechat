<script setup>
import { ref, onMounted } from 'vue'
import AppIcon from './AppIcon.vue'
import DropZone from './DropZone.vue'

const apps = ref([])
const isDragging = ref(false)
const loading = ref(false)

onMounted(async () => {
  await loadApps()
})

const loadApps = async () => {
  try {
    loading.value = true
    const result = await window.pywebview.api.get_applications()
    if (result.code === 200) {
      apps.value = result.data
    }
  } catch (error) {
    console.error('加载应用失败:', error)
  } finally {
    loading.value = false
  }
}

const handleDrop = async (event) => {
  event.preventDefault()
  isDragging.value = false
  
  const files = event.dataTransfer.files
  if (files.length === 0) return
  
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const filePath = file.path
    
    // 检查文件类型
    if (filePath.endsWith('.lnk') || filePath.endsWith('.exe')) {
      try {
        const result = await window.pywebview.api.add_application(filePath)
        if (result.code === 200) {
          console.log('添加成功:', result.data.name)
        } else {
          console.error('添加失败:', result.message)
        }
      } catch (error) {
        console.error('添加应用时出错:', error)
      }
    }
  }
  
  // 重新加载应用列表
  await loadApps()
}

const handleDragOver = (event) => {
  event.preventDefault()
  isDragging.value = true
}

const handleDragLeave = (event) => {
  // 检查是否真的离开了拖放区域
  if (!event.currentTarget.contains(event.relatedTarget)) {
    isDragging.value = false
  }
}

const handleLaunch = async (appId) => {
  try {
    const result = await window.pywebview.api.launch_application(appId)
    if (result.code === 200) {
      console.log('启动成功')
      // 可选：启动后自动隐藏窗口
      // window.pywebview.api.toggle_window_visibility()
    } else {
      console.error('启动失败:', result.message)
    }
  } catch (error) {
    console.error('启动应用时出错:', error)
  }
}

const handleRemove = async (appId) => {
  try {
    const result = await window.pywebview.api.remove_application(appId)
    if (result.code === 200) {
      console.log('删除成功')
      await loadApps()
    } else {
      console.error('删除失败:', result.message)
    }
  } catch (error) {
    console.error('删除应用时出错:', error)
  }
}
</script>

<template>
  <div 
    class="launcher-grid-container"
    @drop="handleDrop"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
  >
    <DropZone v-if="apps.length === 0 || isDragging" :is-dragging="isDragging" />
    
    <div v-if="apps.length > 0 && !isDragging" class="apps-grid">
      <AppIcon 
        v-for="app in apps" 
        :key="app.id"
        :app="app"
        @launch="handleLaunch"
        @remove="handleRemove"
      />
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
  </div>
</template>

<style scoped>
.launcher-grid-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow-y: auto;
  padding: 20px;
}

.apps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 20px;
  padding: 10px;
}

.loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: white;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 自定义滚动条 */
.launcher-grid-container::-webkit-scrollbar {
  width: 8px;
}

.launcher-grid-container::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.launcher-grid-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 4px;
}

.launcher-grid-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
