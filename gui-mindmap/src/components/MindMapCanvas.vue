<template>
  <div
    class="canvas-container"
    ref="containerRef"
    @wheel="onWheel"
    @mousedown="onCanvasMouseDown"
    @mousemove="onCanvasMouseMove"
    @mouseup="onCanvasMouseUp"
    @dblclick="onDoubleClick"
    @contextmenu.prevent="onContextMenu"
  >
    <canvas ref="canvasRef"></canvas>
    <!-- Context menu -->
    <div v-if="contextMenu.visible" class="context-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
      <div class="context-menu-item" @click="onContextViewHistory">View History</div>
      <div class="context-menu-item" @click="onContextViewMapHistory">Map History</div>
    </div>
    <!-- Inline text editing -->
    <input
      v-if="editing"
      ref="editInputRef"
      class="edit-input"
      :style="editInputStyle"
      v-model="editText"
      @blur="finishEdit"
      @keyup.enter="finishEdit"
      @keyup.escape="cancelEdit"
    />
    <Minimap :viewport="viewport" :layout="store.layout" @navigate="onMinimapNavigate" />
    <!-- Toast notification -->
    <Transition name="toast">
      <div v-if="toastVisible" class="toast">{{ toastMessage }}</div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, inject } from 'vue'
import { useMindmapStore } from '../stores/mindmap'
import type { MindNode } from '../utils/tree'
import type { UndoEntry } from '../composables/useUndo'
import Minimap from './Minimap.vue'

const store = useMindmapStore()

const ws = inject<{
  createNode: (parentId: string, content: string, id: string) => void
  updateNode: (nodeId: string, changes: Record<string, any>) => void
  deleteNode: (nodeId: string) => void
  lockNode: (nodeId: string) => Promise<{ success: boolean; lockedBy?: string }>
  unlockNode: (nodeId: string) => Promise<void>
}>('syncActions')!

const undoActions = inject<{
  pushUndo: (entry: UndoEntry) => void
  canUndo: { value: boolean }
  performUndo: () => void
}>('undoActions')!

const containerRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()

// Viewport state
const viewport = ref({ x: 0, y: 0, scale: 1 })
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const panViewportStart = ref({ x: 0, y: 0 })

// Edit state
const editing = ref(false)
const editNodeId = ref<string | null>(null)
const editText = ref('')
const editInputRef = ref<HTMLInputElement>()

// Single-click-to-edit timer
let singleClickTimer: ReturnType<typeof setTimeout> | null = null

// Hover state
const hoveredNodeId = ref<string | null>(null)

// Context menu state
const contextMenu = ref({ visible: false, x: 0, y: 0, nodeId: null as string | null })

// Toast state
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(msg: string) {
  toastMessage.value = msg
  toastVisible.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastVisible.value = false
    toastTimer = null
  }, 3000)
}

const emit = defineEmits<{
  (e: 'showHistory', nodeId: string | null): void
}>()

const editInputStyle = computed(() => {
  if (!editing.value || !editNodeId.value || !store.layout) return {}
  const pos = store.layout.nodePositions.get(editNodeId.value)
  if (!pos) return {}
  const v = viewport.value
  return {
    left: `${pos.x * v.scale + v.x}px`,
    top: `${pos.y * v.scale + v.y}px`,
    width: `${pos.width * v.scale}px`,
    height: `${pos.height * v.scale}px`,
    fontSize: `${14 * v.scale}px`,
  }
})

// Colors — light theme
const COLORS = {
  bg: '#f8fafc',
  nodeFill: '#ffffff',
  nodeStroke: '#e2e8f0',
  nodeText: '#1e293b',
  selectedStroke: '#3b82f6',
  rootFill: '#2563eb',
  rootText: '#ffffff',
  line: '#cbd5e1',
  collapsedDot: '#f59e0b',
}

function draw() {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return

  const dpr = window.devicePixelRatio || 1
  const w = container.clientWidth
  const h = container.clientHeight
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`

  const ctx = canvas.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  // Clear
  ctx.fillStyle = COLORS.bg
  ctx.fillRect(0, 0, w, h)

  // Draw dot grid pattern
  const v = viewport.value
  const gridSize = 40
  const dotRadius = 1
  ctx.fillStyle = '#e2e8f0'
  const startX = ((v.x % (gridSize * v.scale)) - gridSize * v.scale)
  const startY = ((v.y % (gridSize * v.scale)) - gridSize * v.scale)
  for (let gx = startX; gx < w + gridSize * v.scale; gx += gridSize * v.scale) {
    for (let gy = startY; gy < h + gridSize * v.scale; gy += gridSize * v.scale) {
      ctx.beginPath()
      ctx.arc(gx, gy, dotRadius * v.scale, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  if (!store.root || !store.layout) return

  ctx.save()
  ctx.translate(v.x, v.y)
  ctx.scale(v.scale, v.scale)

  // Viewport culling bounds
  const vx0 = -v.x / v.scale
  const vy0 = -v.y / v.scale
  const vx1 = (w - v.x) / v.scale
  const vy1 = (h - v.y) / v.scale

  const positions = store.layout.nodePositions

  // Draw connections
  ctx.strokeStyle = COLORS.line
  ctx.lineWidth = 2
  ctx.lineJoin = 'round'
  for (const node of store.nodes.values()) {
    if (node.parent_id === null) continue
    const childPos = positions.get(node.id)
    const parentPos = positions.get(node.parent_id)
    if (!childPos || !parentPos) continue

    const minX = Math.min(parentPos.x, childPos.x)
    const maxX = Math.max(parentPos.x + parentPos.width, childPos.x + childPos.width)
    const minY = Math.min(parentPos.y, childPos.y)
    const maxY = Math.max(parentPos.y + parentPos.height, childPos.y + childPos.height)
    if (maxX < vx0 || minX > vx1 || maxY < vy0 || minY > vy1) continue

    const x1 = parentPos.x + parentPos.width
    const y1 = parentPos.y + parentPos.height / 2
    const x2 = childPos.x
    const y2 = childPos.y + childPos.height / 2
    const cx = (x1 + x2) / 2

    ctx.beginPath()
    ctx.moveTo(x1, y1)
    ctx.bezierCurveTo(cx, y1, cx, y2, x2, y2)
    ctx.stroke()
  }

  // Draw nodes
  for (const [nodeId, pos] of positions) {
    if (pos.x + pos.width < vx0 || pos.x > vx1 || pos.y + pos.height < vy0 || pos.y > vy1) continue

    const node = store.nodes.get(nodeId)
    if (!node) continue
    const isRoot = node.parent_id === null
    const isSelected = nodeId === store.selectedNodeId
    const lockInfo = store.locks.get(nodeId)

    // Node shadow for depth
    if (!isRoot) {
      ctx.shadowColor = 'rgba(0, 0, 0, 0.05)'
      ctx.shadowBlur = 4
      ctx.shadowOffsetY = 2
    }

    // Node background
    ctx.fillStyle = isRoot ? COLORS.rootFill : COLORS.nodeFill
    if (isSelected && !lockInfo) {
      ctx.shadowColor = 'rgba(37, 99, 235, 0.2)'
      ctx.shadowBlur = 15
      ctx.shadowOffsetY = 4
    }
    
    if (lockInfo) {
      ctx.strokeStyle = '#ef4444'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 3])
    } else {
      ctx.strokeStyle = isSelected ? COLORS.selectedStroke : COLORS.nodeStroke
      ctx.lineWidth = isSelected ? 2.5 : 1.5
      ctx.setLineDash([])
    }
    
    const r = 10
    ctx.beginPath()
    ctx.roundRect(pos.x, pos.y, pos.width, pos.height, r)
    ctx.fill()
    ctx.stroke()
    ctx.setLineDash([])
    ctx.shadowColor = 'transparent'
    ctx.shadowBlur = 0
    ctx.shadowOffsetY = 0

    // Lock label
    if (lockInfo) {
      ctx.font = "600 10px 'Inter', sans-serif"
      ctx.fillStyle = '#ef4444'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      ctx.fillText(`Editing: ${lockInfo.username}`, pos.x + pos.width / 2, pos.y - 4)
    }

    // Text
    ctx.fillStyle = isRoot ? COLORS.rootText : COLORS.nodeText
    ctx.font = isRoot ? "600 15px 'Inter', sans-serif" : "500 14px 'Inter', sans-serif"
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const text = node.content || ''
    // Show full text since layout will be updated to accommodate it
    ctx.fillText(text, pos.x + pos.width / 2, pos.y + pos.height / 2)

    // Collapsed indicator
    if (node.collapsed) {
      ctx.fillStyle = COLORS.collapsedDot
      ctx.beginPath()
      ctx.arc(pos.x + pos.width + 10, pos.y + pos.height / 2, 5, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

    // Hover tooltip
    if (nodeId === hoveredNodeId.value && node.last_edited_by_name) {
      const timeStr = node.last_edited_at
        ? new Date(node.last_edited_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : ''
      const infoText = `${node.last_edited_by_name} ${timeStr}`
      ctx.font = "500 11px 'Inter', sans-serif"
      ctx.fillStyle = '#64748b'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(infoText, pos.x + pos.width / 2, pos.y + pos.height + 6)
    }
  }

  ctx.restore()
}

function screenToWorld(sx: number, sy: number) {
  const v = viewport.value
  return {
    x: (sx - v.x) / v.scale,
    y: (sy - v.y) / v.scale,
  }
}

function hitTest(sx: number, sy: number): string | null {
  if (!store.layout) return null
  const world = screenToWorld(sx, sy)
  for (const [nodeId, pos] of store.layout.nodePositions) {
    if (world.x >= pos.x && world.x <= pos.x + pos.width &&
        world.y >= pos.y && world.y <= pos.y + pos.height) {
      return nodeId
    }
  }
  return null
}

function onCanvasMouseDown(e: MouseEvent) {
  if (editing.value) return
  contextMenu.value.visible = false
  const rect = containerRef.value!.getBoundingClientRect()
  const sx = e.clientX - rect.left
  const sy = e.clientY - rect.top
  const nodeId = hitTest(sx, sy)

  if (nodeId) {
    if (nodeId === store.selectedNodeId) {
      // Already selected — start edit after delay (cancelled if double-click)
      singleClickTimer = setTimeout(() => {
        singleClickTimer = null
        startEdit(nodeId)
      }, 250)
    } else {
      store.selectNode(nodeId)
    }
    draw()
  } else {
    store.selectNode(null)
    isPanning.value = true
    panStart.value = { x: e.clientX, y: e.clientY }
    panViewportStart.value = { x: viewport.value.x, y: viewport.value.y }
    draw()
  }
}

function onCanvasMouseMove(e: MouseEvent) {
  if (isPanning.value) {
    viewport.value.x = panViewportStart.value.x + (e.clientX - panStart.value.x)
    viewport.value.y = panViewportStart.value.y + (e.clientY - panStart.value.y)
    draw()
    return
  }
  // Update hover state
  const rect = containerRef.value!.getBoundingClientRect()
  const sx = e.clientX - rect.left
  const sy = e.clientY - rect.top
  const nodeId = hitTest(sx, sy)
  if (nodeId !== hoveredNodeId.value) {
    hoveredNodeId.value = nodeId
    draw()
  }
}

function onCanvasMouseUp() {
  isPanning.value = false
}

function onWheel(e: WheelEvent) {
  e.preventDefault()
  const rect = containerRef.value!.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top

  const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1
  const newScale = Math.min(3, Math.max(0.1, viewport.value.scale * zoomFactor))

  // Zoom toward cursor
  viewport.value.x = mx - (mx - viewport.value.x) * (newScale / viewport.value.scale)
  viewport.value.y = my - (my - viewport.value.y) * (newScale / viewport.value.scale)
  viewport.value.scale = newScale
  draw()
}

function onDoubleClick(e: MouseEvent) {
  if (singleClickTimer) {
    clearTimeout(singleClickTimer)
    singleClickTimer = null
  }
  const rect = containerRef.value!.getBoundingClientRect()
  const sx = e.clientX - rect.left
  const sy = e.clientY - rect.top
  const nodeId = hitTest(sx, sy)
  if (nodeId) {
    startEdit(nodeId)
  }
}

async function startEdit(nodeId: string) {
  const node = store.nodes.get(nodeId)
  if (!node) return
  // Try to acquire lock
  const result = await ws.lockNode(nodeId)
  if (!result.success) {
    if (result.lockedBy) {
      showToast(`${result.lockedBy} 正在编辑，请等待操作结束后再进行操作`)
    }
    return
  }
  editNodeId.value = nodeId
  editText.value = node.content
  editing.value = true
  store.selectNode(nodeId)
  nextTick(() => {
    editInputRef.value?.focus()
    editInputRef.value?.select()
  })
}

function finishEdit() {
  if (!editing.value || !editNodeId.value) return
  const node = store.nodes.get(editNodeId.value)
  if (node && editText.value !== node.content) {
    const oldContent = node.content
    undoActions.pushUndo({ type: 'update', nodeId: editNodeId.value, previousState: { content: oldContent } })
    node.content = editText.value
    store.rebuildTree()
    ws.updateNode(editNodeId.value, { content: editText.value })
  }
  ws.unlockNode(editNodeId.value)
  editing.value = false
  editNodeId.value = null
  draw()
}

function cancelEdit() {
  if (editNodeId.value) {
    ws.unlockNode(editNodeId.value)
  }
  editing.value = false
  editNodeId.value = null
  draw()
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

function onKeydown(e: KeyboardEvent) {
  if (editing.value) return

  // Ctrl+Z / Cmd+Z undo
  if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
    e.preventDefault()
    undoActions.performUndo()
    draw()
    return
  }

  if (!store.selectedNodeId) return

  if (e.key === 'Tab') {
    e.preventDefault()
    // Add child
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
    ws.createNode(store.selectedNodeId, content, id)
    undoActions.pushUndo({ type: 'create', nodeId: id })
    store.selectNode(id)
    draw()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const node = store.selectedNode
    if (node?.parent_id) {
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
      ws.createNode(node.parent_id, content, id)
      undoActions.pushUndo({ type: 'create', nodeId: id })
      store.selectNode(id)
      draw()
    }
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    const node = store.selectedNode
    if (node && node.parent_id !== null) {
      const snapshot = collectSubtreeSnapshot(node.id)
      undoActions.pushUndo({ type: 'delete', nodeId: node.id, deletedNodes: snapshot })
      store.applyNodeDelete(node.id)
      ws.deleteNode(node.id)
      draw()
    }
  } else if (e.key === 'F2' || e.key === ' ') {
    e.preventDefault()
    startEdit(store.selectedNodeId)
  }
}

function onContextMenu(e: MouseEvent) {
  const rect = containerRef.value!.getBoundingClientRect()
  const sx = e.clientX - rect.left
  const sy = e.clientY - rect.top
  const nodeId = hitTest(sx, sy)
  contextMenu.value = { visible: true, x: sx, y: sy, nodeId }
}

function onContextViewHistory() {
  const nodeId = contextMenu.value.nodeId
  contextMenu.value.visible = false
  emit('showHistory', nodeId)
}

function onContextViewMapHistory() {
  contextMenu.value.visible = false
  emit('showHistory', null)
}

function onMinimapNavigate(pos: { x: number; y: number }) {
  const container = containerRef.value
  if (!container) return
  viewport.value.x = -pos.x * viewport.value.scale + container.clientWidth / 2
  viewport.value.y = -pos.y * viewport.value.scale + container.clientHeight / 2
  draw()
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  draw()

  resizeObserver = new ResizeObserver(() => draw())
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }

  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('keydown', onKeydown)
})

// Redraw when layout changes
watch(() => store.layout, () => draw(), { deep: false })
</script>

<style scoped>
.canvas-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  cursor: grab;
  background: var(--bg-base);
}

.canvas-container:active {
  cursor: grabbing;
}

canvas {
  display: block;
}

.edit-input {
  position: absolute;
  border: 2px solid var(--accent);
  border-radius: var(--radius-sm);
  padding: 2px 8px;
  outline: none;
  text-align: center;
  font-family: var(--font-body);
  background: var(--bg-elevated);
  color: var(--text-primary);
  z-index: 20;
  box-shadow: 0 0 0 4px var(--accent-glow);
}

.context-menu {
  position: absolute;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 25;
  min-width: 160px;
  padding: 4px;
  backdrop-filter: blur(12px);
}

.context-menu-item {
  padding: 9px 14px;
  font-size: 13px;
  font-family: var(--font-body);
  cursor: pointer;
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.context-menu-item:hover {
  background: var(--accent-glow);
  color: var(--accent);
}

.toast {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #1e293b;
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-family: var(--font-body);
  z-index: 30;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  white-space: nowrap;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
</style>
