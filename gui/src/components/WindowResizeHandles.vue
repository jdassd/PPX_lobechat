<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const apiReady = ref(!!window.pywebview?.api)

const handles = [
  { dir: 'n', class: 'resize-n' },
  { dir: 's', class: 'resize-s' },
  { dir: 'e', class: 'resize-e' },
  { dir: 'w', class: 'resize-w' },
  { dir: 'ne', class: 'resize-ne' },
  { dir: 'nw', class: 'resize-nw' },
  { dir: 'se', class: 'resize-se' },
  { dir: 'sw', class: 'resize-sw' }
]

const FIX_POINT_MAP = {
  n: 'S',
  s: 'N',
  e: 'W',
  w: 'E',
  ne: 'SW',
  nw: 'SE',
  se: 'NW',
  sw: 'NE'
}

const MIN_WIDTH = 360
const MIN_HEIGHT = 240

const getScale = () => window.devicePixelRatio || 1

let resizing = false
let resizeDir = ''
let startX = 0
let startY = 0
let startWidth = 0
let startHeight = 0
let rafId = 0
let pending = null

const startResize = (dir, event) => {
  if (!apiReady.value || !window.pywebview?.api?.resize_window) return
  if (event.pointerType === 'mouse' && event.button !== 0) return
  event.preventDefault()
  event.stopPropagation()

  resizing = true
  resizeDir = dir
  startX = event.clientX
  startY = event.clientY
  startWidth = window.innerWidth
  startHeight = window.innerHeight

  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', stopResize)
  window.addEventListener('pointercancel', stopResize)
  window.addEventListener('blur', stopResize)
}

const scheduleResize = (width, height) => {
  pending = { width, height }
  if (rafId) return
  rafId = window.requestAnimationFrame(() => {
    rafId = 0
    if (!pending) return
    const { width: nextWidth, height: nextHeight } = pending
    pending = null
    const scale = getScale()
    window.pywebview.api.resize_window({
      width: Math.round(nextWidth * scale),
      height: Math.round(nextHeight * scale),
      fixPoint: FIX_POINT_MAP[resizeDir]
    }).catch(() => {})
  })
}

const onPointerMove = (event) => {
  if (!resizing) return
  const deltaX = event.clientX - startX
  const deltaY = event.clientY - startY

  let nextWidth = startWidth
  let nextHeight = startHeight

  if (resizeDir.includes('e')) {
    nextWidth = startWidth + deltaX
  }
  if (resizeDir.includes('w')) {
    nextWidth = startWidth - deltaX
  }
  if (resizeDir.includes('s')) {
    nextHeight = startHeight + deltaY
  }
  if (resizeDir.includes('n')) {
    nextHeight = startHeight - deltaY
  }

  nextWidth = Math.max(MIN_WIDTH, Math.round(nextWidth))
  nextHeight = Math.max(MIN_HEIGHT, Math.round(nextHeight))

  scheduleResize(nextWidth, nextHeight)
}

const stopResize = () => {
  if (!resizing) return
  resizing = false
  resizeDir = ''
  pending = null
  if (rafId) {
    window.cancelAnimationFrame(rafId)
    rafId = 0
  }
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', stopResize)
  window.removeEventListener('pointercancel', stopResize)
  window.removeEventListener('blur', stopResize)
}

const onPywebviewReady = () => {
  apiReady.value = true
}

onMounted(() => {
  window.addEventListener('pywebviewready', onPywebviewReady)
})

onBeforeUnmount(() => {
  window.removeEventListener('pywebviewready', onPywebviewReady)
  stopResize()
})
</script>

<template>
  <div v-if="apiReady" class="window-resize-handles">
    <div
      v-for="handle in handles"
      :key="handle.dir"
      class="resize-handle"
      :class="handle.class"
      @pointerdown="startResize(handle.dir, $event)"
    ></div>
  </div>
</template>

<style scoped>
.window-resize-handles {
  position: fixed;
  inset: 0;
  z-index: 100000;
  pointer-events: none;
}

.resize-handle {
  position: fixed;
  pointer-events: auto;
  background: transparent;
  touch-action: none;
}

.resize-n,
.resize-s {
  left: 8px;
  right: 8px;
  height: 6px;
}

.resize-n {
  top: 0;
  cursor: ns-resize;
}

.resize-s {
  bottom: 0;
  cursor: ns-resize;
}

.resize-e,
.resize-w {
  top: 8px;
  bottom: 8px;
  width: 6px;
}

.resize-e {
  right: 0;
  cursor: ew-resize;
}

.resize-w {
  left: 0;
  cursor: ew-resize;
}

.resize-ne,
.resize-nw,
.resize-se,
.resize-sw {
  width: 12px;
  height: 12px;
}

.resize-ne {
  top: 0;
  right: 0;
  cursor: nesw-resize;
}

.resize-nw {
  top: 0;
  left: 0;
  cursor: nwse-resize;
}

.resize-se {
  bottom: 0;
  right: 0;
  cursor: nwse-resize;
}

.resize-sw {
  bottom: 0;
  left: 0;
  cursor: nesw-resize;
}
</style>
