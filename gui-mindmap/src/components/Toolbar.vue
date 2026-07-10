<template>
  <div class="toolbar">
    <button class="toolbar-btn back-btn" @click="$emit('back')">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    </button>
    <div class="toolbar-divider"></div>
    <span class="map-name">{{ store.mapName }}</span>
    <div class="toolbar-actions">
      <button class="toolbar-btn" @click="addChild" :disabled="!store.selectedNodeId" title="Add Child (Tab)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Child
      </button>
      <button class="toolbar-btn" @click="addSibling" :disabled="!canAddSibling" title="Add Sibling (Enter)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Sibling
      </button>
      <button class="toolbar-btn danger" @click="deleteSelected" :disabled="!canDelete" title="Delete (Del)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
      </button>
      <div class="toolbar-divider"></div>
      <button class="toolbar-btn" @click="undoActions.performUndo()" :disabled="!undoActions.canUndo.value" title="Undo (Ctrl+Z)">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
      </button>
      <button class="toolbar-btn" @click="toggleCollapse" :disabled="!store.selectedNodeId" :title="isSelectedCollapsed ? 'Expand' : 'Collapse'">
        <svg v-if="isSelectedCollapsed" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
        <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
      </button>
      <div class="toolbar-divider"></div>
      <div class="export-dropdown" ref="exportDropdownRef">
        <button class="toolbar-btn" @click="showExportMenu = !showExportMenu" title="Export">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Export
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <div v-if="showExportMenu" class="export-menu">
          <button class="export-menu-item" @click="exportAs('docx')" :disabled="exporting">Word (.docx)</button>
          <button class="export-menu-item" @click="exportAs('xlsx')" :disabled="exporting">Excel (.xlsx)</button>
          <button class="export-menu-item" @click="exportAs('xmind')" :disabled="exporting">XMind (.xmind)</button>
        </div>
      </div>
    </div>
    <div class="toolbar-status">
      <span :class="['status-dot', syncing ? 'online' : 'offline']"></span>
      {{ syncing ? 'Synced' : 'Offline' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'
import { useMindmapStore } from '../stores/mindmap'
import { getAccessToken } from '../services/api'
import type { MindNode } from '../utils/tree'
import type { UndoEntry } from '../composables/useUndo'

const store = useMindmapStore()

const actions = inject<{
  createNode: (parentId: string, content: string, id: string) => void
  updateNode: (nodeId: string, changes: Record<string, any>) => void
  deleteNode: (nodeId: string) => void
  lockNode: (nodeId: string) => Promise<boolean>
  unlockNode: (nodeId: string) => Promise<void>
}>('syncActions')!

const syncing = inject<Ref<boolean>>('syncing')!

const undoActions = inject<{
  pushUndo: (entry: UndoEntry) => void
  canUndo: ComputedRef<boolean>
  performUndo: () => void
}>('undoActions')!

defineEmits<{ (e: 'back'): void }>()

const showExportMenu = ref(false)
const exporting = ref(false)
const exportDropdownRef = ref<HTMLElement | null>(null)

function onClickOutside(e: MouseEvent) {
  if (exportDropdownRef.value && !exportDropdownRef.value.contains(e.target as Node)) {
    showExportMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))

async function exportAs(format: string) {
  if (!store.mapId || exporting.value) return
  exporting.value = true
  showExportMenu.value = false
  try {
    const token = getAccessToken()
    const res = await fetch(`/api/maps/${store.mapId}/export/${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error(`Export failed: ${res.statusText}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const ext = format === 'docx' ? '.docx' : format === 'xlsx' ? '.xlsx' : '.xmind'
    a.download = `${store.mapName || 'mindmap'}${ext}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Export error:', err)
    alert('Export failed. Please try again.')
  } finally {
    exporting.value = false
  }
}
const canAddSibling = computed(() => {
  const node = store.selectedNode
  return node && node.parent_id !== null
})

const canDelete = computed(() => {
  const node = store.selectedNode
  return node && node.parent_id !== null
})

const isSelectedCollapsed = computed(() => {
  return store.selectedNode?.collapsed ?? false
})

function addChild() {
  if (!store.selectedNodeId) return
  const id = crypto.randomUUID()
  const content = 'New Node'
  store.applyNodeCreate({
    id,
    map_id: store.mapId!,
    parent_id: store.selectedNodeId,
    content,
    position: store.getNextPosition(store.selectedNodeId),
    style: '{}',
    collapsed: false,
  })
  actions.createNode(store.selectedNodeId, content, id)
  undoActions.pushUndo({ type: 'create', nodeId: id })
  store.selectNode(id)
}

function addSibling() {
  const node = store.selectedNode
  if (!node || !node.parent_id) return
  const id = crypto.randomUUID()
  const content = 'New Node'
  store.applyNodeCreate({
    id,
    map_id: store.mapId!,
    parent_id: node.parent_id,
    content,
    position: store.getNextPosition(node.parent_id),
    style: '{}',
    collapsed: false,
  })
  actions.createNode(node.parent_id, content, id)
  undoActions.pushUndo({ type: 'create', nodeId: id })
  store.selectNode(id)
}

function collectSubtreeSnapshot(nodeId: string): MindNode[] {
  const result: MindNode[] = []
  const node = store.nodes.get(nodeId)
  if (!node) return result
  result.push({ ...node })
  for (const n of store.nodes.values()) {
    if (n.parent_id === nodeId) {
      result.push(...collectSubtreeSnapshot(n.id))
    }
  }
  return result
}

function deleteSelected() {
  if (!store.selectedNodeId || !canDelete.value) return
  const id = store.selectedNodeId
  const snapshot = collectSubtreeSnapshot(id)
  undoActions.pushUndo({ type: 'delete', nodeId: id, deletedNodes: snapshot })
  store.applyNodeDelete(id)
  actions.deleteNode(id)
}

function toggleCollapse() {
  if (!store.selectedNodeId) return
  const node = store.selectedNode
  if (!node) return
  const newCollapsed = !node.collapsed
  node.collapsed = newCollapsed
  store.rebuildTree()
  actions.updateNode(store.selectedNodeId, { collapsed: newCollapsed })
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  z-index: 10;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--border-default);
  margin: 0 4px;
}

.map-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 16px;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--font-body);
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--accent);
  color: var(--accent);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.toolbar-btn:active:not(:disabled) {
  transform: translateY(0);
}

.toolbar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.back-btn {
  padding: 8px 10px;
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

.back-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--border-default);
  color: var(--text-primary);
}

.toolbar-btn.danger:hover:not(:disabled) {
  background: var(--color-error-bg);
  border-color: var(--color-error);
  color: var(--color-error);
}

.toolbar-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-left: 8px;
  padding: 6px 14px;
  background: var(--bg-hover);
  border-radius: 100px;
  border: 1px solid var(--border-subtle);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online {
  background: var(--accent-green);
  box-shadow: 0 0 8px var(--accent-green-glow);
}

.status-dot.offline {
  background: var(--color-error);
  box-shadow: 0 0 8px var(--color-error-bg);
}

.export-dropdown {
  position: relative;
}

.export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  z-index: 100;
  min-width: 160px;
  overflow: hidden;
}

.export-menu-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-body);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.export-menu-item:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.export-menu-item:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
