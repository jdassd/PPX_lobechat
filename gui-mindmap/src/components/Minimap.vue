<template>
  <div class="minimap" ref="minimapRef" @mousedown="onMinimapClick">
    <canvas ref="minimapCanvas"></canvas>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import type { LayoutResult } from '../utils/layout'

const props = defineProps<{
  viewport: { x: number; y: number; scale: number }
  layout: LayoutResult | null
}>()

const emit = defineEmits<{
  (e: 'navigate', pos: { x: number; y: number }): void
}>()

const minimapRef = ref<HTMLDivElement>()
const minimapCanvas = ref<HTMLCanvasElement>()

const MINIMAP_W = 180
const MINIMAP_H = 120

function draw() {
  const canvas = minimapCanvas.value
  if (!canvas || !props.layout) return

  const dpr = window.devicePixelRatio || 1
  canvas.width = MINIMAP_W * dpr
  canvas.height = MINIMAP_H * dpr
  canvas.style.width = `${MINIMAP_W}px`
  canvas.style.height = `${MINIMAP_H}px`

  const ctx = canvas.getContext('2d')!
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  // Clear background
  ctx.clearRect(0, 0, MINIMAP_W, MINIMAP_H)

  const tw = props.layout.totalWidth || 1
  const th = props.layout.totalHeight || 1
  const scaleX = (MINIMAP_W - 20) / tw
  const scaleY = (MINIMAP_H - 20) / th
  const s = Math.min(scaleX, scaleY)

  ctx.save()
  // Center the layout in minimap
  const offsetX = (MINIMAP_W - tw * s) / 2
  const offsetY = (MINIMAP_H - th * s) / 2
  ctx.translate(offsetX, offsetY)
  ctx.scale(s, s)

  // Draw nodes as soft rectangles
  ctx.fillStyle = '#cbd5e1' // slate-300
  for (const pos of props.layout.nodePositions.values()) {
    // Use slightly larger dots for visibility
    const w = Math.max(pos.width, 10 / s)
    const h = Math.max(pos.height, 5 / s)
    ctx.beginPath()
    ctx.roundRect(pos.x, pos.y, w, h, 2 / s)
    ctx.fill()
  }

  ctx.restore()

  // Draw viewport rect
  const v = props.viewport
  const parentEl = minimapRef.value?.parentElement
  if (parentEl) {
    const pw = parentEl.clientWidth
    const ph = parentEl.clientHeight
    const vx = (-v.x / v.scale) * s + offsetX
    const vy = (-v.y / v.scale) * s + offsetY
    const vw = (pw / v.scale) * s
    const vh = (ph / v.scale) * s
    
    // Shadow for viewport
    ctx.shadowColor = 'rgba(37, 99, 235, 0.2)'
    ctx.shadowBlur = 4
    
    ctx.strokeStyle = '#3b82f6' // accent blue
    ctx.lineWidth = 2
    ctx.strokeRect(vx, vy, vw, vh)
    
    // Semi-transparent fill for the "outside" or the "inside"
    ctx.fillStyle = 'rgba(59, 130, 246, 0.05)'
    ctx.fillRect(vx, vy, vw, vh)
    
    ctx.shadowBlur = 0
  }
}

function onMinimapClick(e: MouseEvent) {
  const rect = minimapRef.value!.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top

  if (!props.layout) return

  const tw = props.layout.totalWidth || 1
  const th = props.layout.totalHeight || 1
  const scaleX = (MINIMAP_W - 20) / tw
  const scaleY = (MINIMAP_H - 20) / th
  const s = Math.min(scaleX, scaleY)

  const offsetX = (MINIMAP_W - tw * s) / 2
  const offsetY = (MINIMAP_H - th * s) / 2

  const worldX = (mx - offsetX) / s
  const worldY = (my - offsetY) / s

  emit('navigate', { x: worldX, y: worldY })
}

watch(() => [props.viewport, props.layout], () => draw(), { deep: true })
onMounted(() => draw())
</script>

<style scoped>
.minimap {
  position: absolute;
  bottom: 24px;
  right: 24px;
  width: 180px;
  height: 120px;
  background: rgba(255, 255, 255, 0.7);
  border: 1.5px solid rgba(255, 255, 255, 0.8);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  box-shadow: 
    0 10px 15px -3px rgba(0, 0, 0, 0.05),
    0 4px 6px -4px rgba(0, 0, 0, 0.05),
    inset 0 0 0 1px rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(16px) saturate(180%);
  transition: all var(--duration-normal) var(--ease-out);
  z-index: 10;
}

.minimap:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-2px);
  box-shadow: 
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1);
  border-color: var(--accent);
}

canvas {
  display: block;
}
</style>
