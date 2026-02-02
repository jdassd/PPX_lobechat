<script setup>
import { ref } from 'vue'

const props = defineProps({
  app: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['launch', 'remove'])

const showMenu = ref(false)
const menuX = ref(0)
const menuY = ref(0)

const handleClick = () => {
  emit('launch', props.app.id)
}

const handleContextMenu = (event) => {
  event.preventDefault()
  showMenu.value = true
  menuX.value = event.clientX
  menuY.value = event.clientY
  
  // 点击其他地方关闭菜单
  const closeMenu = () => {
    showMenu.value = false
    document.removeEventListener('click', closeMenu)
  }
  setTimeout(() => document.addEventListener('click', closeMenu), 0)
}

const handleRemove = () => {
  if (confirm(`确定要删除 "${props.app.name}" 吗？`)) {
    emit('remove', props.app.id)
  }
  showMenu.value = false
}
</script>

<template>
  <div 
    class="app-icon"
    @click="handleClick"
    @contextmenu="handleContextMenu"
  >
    <div class="icon-wrapper">
      <img 
        v-if="app.icon" 
        :src="`data:image/png;base64,${app.icon}`" 
        :alt="app.name"
        class="icon-image"
      />
      <div v-else class="icon-placeholder">
        📦
      </div>
    </div>
    <div class="app-name">{{ app.name }}</div>

    <!-- 右键菜单 -->
    <Teleport to="body">
      <div 
        v-if="showMenu" 
        class="context-menu"
        :style="{ left: menuX + 'px', top: menuY + 'px' }"
      >
        <div class="menu-item" @click="handleRemove">
          <span>🗑️</span>
          <span>删除</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.app-icon {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 15px;
  cursor: pointer;
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.app-icon:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-5px);
}

.app-icon:active {
  transform: translateY(-2px) scale(0.98);
}

.icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transition: all 0.3s;
}

.app-icon:hover .icon-wrapper {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  transform: scale(1.1);
}

.icon-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.icon-placeholder {
  font-size: 32px;
}

.app-name {
  color: white;
  font-size: 12px;
  text-align: center;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.context-menu {
  position: fixed;
  background: rgba(30, 30, 30, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  min-width: 120px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  color: white;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.menu-item span:first-child {
  font-size: 16px;
}
</style>
