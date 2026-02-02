<script setup>
defineProps({
  isDragging: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div class="drop-zone" :class="{ 'drop-zone-active': isDragging }">
    <div class="drop-zone-content">
      <div class="drop-icon">
        {{ isDragging ? '📥' : '➕' }}
      </div>
      <h3>{{ isDragging ? '松开以添加应用' : '拖放应用到这里' }}</h3>
      <p>支持拖入 .lnk 快捷方式或 .exe 可执行文件</p>
    </div>
  </div>
</template>

<style scoped>
.drop-zone {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 3px dashed rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  transition: all 0.3s;
  background: rgba(255, 255, 255, 0.05);
}

.drop-zone-active {
  border-color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.15);
  transform: scale(0.98);
}

.drop-zone-content {
  text-align: center;
  color: white;
  padding: 40px;
}

.drop-icon {
  font-size: 64px;
  margin-bottom: 20px;
  animation: bounce 2s infinite;
}

.drop-zone-active .drop-icon {
  animation: pulse 0.5s infinite;
}

h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 10px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

p {
  font-size: 14px;
  opacity: 0.8;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}
</style>
