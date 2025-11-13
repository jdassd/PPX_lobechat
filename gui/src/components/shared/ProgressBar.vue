<script setup>
import { computed } from 'vue'

const props = defineProps({
  current: {
    type: Number,
    default: 0
  },
  total: {
    type: Number,
    default: 0
  },
  message: {
    type: String,
    default: ''
  }
})

const percent = computed(() => {
  if (!props.total) return 0
  return Math.min(100, Math.round((props.current / props.total) * 100))
})
</script>

<template>
  <div v-if="total" class="progress-wrap">
    <div class="progress-track">
      <div class="progress-inner" :style="{ width: `${percent}%` }"></div>
    </div>
    <div class="progress-text">
      <span>{{ message || '处理中' }}</span>
      <span>{{ current }}/{{ total }} · {{ percent }}%</span>
    </div>
  </div>
</template>

<style scoped>
.progress-wrap {
  margin-top: 10px;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: #eef1f8;
  border-radius: 999px;
  overflow: hidden;
}

.progress-inner {
  height: 100%;
  background: linear-gradient(90deg, #5a8bff, #7fc8ff);
  transition: width 0.3s ease;
}

.progress-text {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #798098;
}
</style>
