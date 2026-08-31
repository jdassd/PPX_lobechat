<script setup>
import { computed } from 'vue'
import { ArrowDown, ArrowUp, Close } from '@element-plus/icons-vue'

const props = defineProps({
  files: { type: Array, default: () => [] },
  sortable: { type: Boolean, default: false },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['remove', 'move'])

const fileName = (file) =>
  file?.filename ||
  file?.name ||
  String(file?.path || file || '')
    .split(/[\\/]/)
    .pop()
const filePath = (file) => file?.path || String(file || '')
const fileExt = (file) => {
  const match = fileName(file).match(/\.([^.]+)$/)
  return match ? match[1].toUpperCase() : 'FILE'
}
const hasFiles = computed(() => props.files.length > 0)
</script>

<template>
  <div v-if="hasFiles" class="queue" aria-label="待处理文件">
    <div v-for="(file, index) in files" :key="`${filePath(file)}-${index}`" class="queue-row">
      <span class="format-mark">{{ fileExt(file) }}</span>
      <span class="file-meta">
        <b>{{ fileName(file) }}</b>
        <small>{{ filePath(file) }}</small>
      </span>
      <span class="row-actions">
        <el-button v-if="sortable" text circle size="small" :disabled="busy || index === 0" aria-label="上移" @click="emit('move', index, -1)">
          <el-icon><ArrowUp /></el-icon>
        </el-button>
        <el-button v-if="sortable" text circle size="small" :disabled="busy || index === files.length - 1" aria-label="下移" @click="emit('move', index, 1)">
          <el-icon><ArrowDown /></el-icon>
        </el-button>
        <el-button text circle size="small" :disabled="busy" aria-label="移除" @click="emit('remove', index)">
          <el-icon><Close /></el-icon>
        </el-button>
      </span>
    </div>
  </div>
</template>

<style scoped>
.queue {
  border-top: 1px solid var(--ppx-glass-border);
}
.queue-row {
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 7px 10px;
  border-bottom: 1px solid var(--ppx-glass-border);
}
.queue-row:last-child {
  border-bottom: none;
}
.format-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  height: 26px;
  padding: 0 5px;
  border-radius: 7px;
  background: color-mix(in srgb, var(--accent) 11%, var(--ppx-bg-inset));
  color: var(--accent);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.03em;
}
.file-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.file-meta b {
  overflow: hidden;
  color: var(--ppx-text-primary);
  font-size: 12.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-meta small {
  overflow: hidden;
  color: var(--ppx-text-muted);
  font: 10.5px var(--ppx-font-mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-actions {
  display: flex;
  align-items: center;
}
@media (max-width: 620px) {
  .queue-row {
    grid-template-columns: 44px minmax(0, 1fr);
  }
  .row-actions {
    grid-column: 2;
    justify-content: flex-end;
  }
}
</style>
