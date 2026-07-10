<template>
  <div class="history-panel" v-if="visible">
    <div class="history-header">
      <span class="history-title">{{ nodeId ? 'Node History' : 'Map History' }}</span>
      <button class="history-close" @click="$emit('close')">&times;</button>
    </div>
    <div class="history-list">
      <div v-if="loading" class="history-loading">Loading...</div>
      <div v-else-if="entries.length === 0" class="history-empty">No history</div>
      <div v-else v-for="entry in entries" :key="entry.id" class="history-entry">
        <div class="history-entry-header">
          <span class="history-action" :class="entry.action">{{ actionLabel(entry.action) }}</span>
          <span class="history-user">{{ entry.username || 'Unknown' }}</span>
          <span class="history-time">{{ formatTime(entry.created_at) }}</span>
        </div>
        <div class="history-detail" v-if="entry.action === 'update'">
          <span class="history-old">{{ entry.old_content }}</span>
          <span class="history-arrow">&rarr;</span>
          <span class="history-new">{{ entry.new_content }}</span>
        </div>
        <div class="history-detail" v-else-if="entry.action === 'create'">
          Created: {{ entry.new_content }}
        </div>
        <div class="history-detail" v-else-if="entry.action === 'delete'">
          Deleted: {{ entry.old_content }}
        </div>
        <button class="history-rollback-btn" @click="rollback(entry)">Rollback</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { apiJson } from '../services/api'

const props = defineProps<{
  visible: boolean
  mapId: string
  nodeId?: string | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'rollback'): void
}>()

const entries = ref<any[]>([])
const loading = ref(false)

watch(() => [props.visible, props.nodeId], async () => {
  if (!props.visible) return
  await fetchHistory()
}, { immediate: true })

async function fetchHistory() {
  loading.value = true
  try {
    if (props.nodeId) {
      entries.value = await apiJson(`/api/maps/${props.mapId}/nodes/${props.nodeId}/history`)
    } else {
      entries.value = await apiJson(`/api/maps/${props.mapId}/history`)
    }
  } catch {
    entries.value = []
  } finally {
    loading.value = false
  }
}

function actionLabel(action: string) {
  switch (action) {
    case 'create': return 'Create'
    case 'update': return 'Update'
    case 'delete': return 'Delete'
    default: return action
  }
}

function formatTime(dt: string) {
  if (!dt) return ''
  return new Date(dt).toLocaleString()
}

async function rollback(entry: any) {
  try {
    await apiJson(`/api/maps/${props.mapId}/nodes/${entry.node_id}/history/${entry.id}/rollback`, {
      method: 'POST',
    })
    emit('rollback')
    await fetchHistory()
  } catch (err) {
    console.error('Rollback failed:', err)
  }
}
</script>

<style scoped>
.history-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 360px;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-subtle);
  z-index: 30;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
}

.history-title {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.history-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  font-size: 16px;
  cursor: pointer;
  color: var(--text-tertiary);
  transition: all var(--duration-fast) var(--ease-out);
}

.history-close:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 0;
}

.history-loading,
.history-empty {
  text-align: center;
  color: var(--text-tertiary);
  padding: 32px;
  font-size: 13px;
}

.history-entry {
  padding: 12px 18px;
  border-bottom: 1px solid var(--border-subtle);
  transition: background var(--duration-fast);
}

.history-entry:hover {
  background: var(--bg-elevated);
}

.history-entry-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.history-action {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.history-action.create {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.history-action.update {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.history-action.delete {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.history-user {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.history-time {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-left: auto;
}

.history-detail {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.history-old {
  text-decoration: line-through;
  color: var(--color-error);
  opacity: 0.8;
}

.history-arrow {
  margin: 0 6px;
  color: var(--text-tertiary);
}

.history-new {
  color: var(--color-success);
}

.history-rollback-btn {
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-body);
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-out);
}

.history-rollback-btn:hover {
  background: var(--accent-glow);
  border-color: rgba(56, 189, 248, 0.3);
  color: var(--accent);
}
</style>
