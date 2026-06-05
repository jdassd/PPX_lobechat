<!-- gui/src/components/CommandPalette.vue —— ⌘K 命令面板 -->
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { TOOLS, HOME } from '../config/tools'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'select'])

const q = ref('')
const idx = ref(0)
const inputRef = ref(null)
const items = computed(() => [
  { id: 'home', name: '首页', desc: '返回工具总览', icon: HOME.icon, hue: 'var(--accent)' },
  ...TOOLS,
])
const filtered = computed(() => {
  const k = q.value.trim().toLowerCase()
  if (!k) return items.value
  return items.value.filter((t) => (t.name + (t.desc || '') + (t.points || []).join('')).toLowerCase().includes(k))
})

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      q.value = ''
      idx.value = 0
      nextTick(() => inputRef.value?.focus())
    }
  },
)
watch(q, () => { idx.value = 0 })

const close = () => emit('update:modelValue', false)
const choose = (t) => { emit('select', t.id); close() }
const onKey = (e) => {
  if (e.key === 'ArrowDown') { e.preventDefault(); idx.value = Math.min(idx.value + 1, filtered.value.length - 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); idx.value = Math.max(idx.value - 1, 0) }
  else if (e.key === 'Enter') { e.preventDefault(); filtered.value[idx.value] && choose(filtered.value[idx.value]) }
  else if (e.key === 'Escape') close()
}
</script>

<template>
  <teleport to="body">
    <div v-if="modelValue" class="cp-scrim" @click="close">
      <div class="cp-box" @click.stop>
        <div class="cp-head">
          <el-icon :size="19" color="var(--ppx-text-muted)"><Search /></el-icon>
          <input ref="inputRef" v-model="q" @keydown="onKey" class="cp-input" placeholder="跳转到工具，或搜索功能…" />
          <kbd>ESC</kbd>
        </div>
        <div class="cp-list">
          <div v-if="!filtered.length" class="cp-empty">没有匹配项</div>
          <button
            v-for="(t, i) in filtered"
            :key="t.id"
            class="cp-item"
            :class="{ on: i === idx }"
            @mouseenter="idx = i"
            @click="choose(t)"
          >
            <span class="cp-ico" :style="{ background: t.id === 'home' ? 'var(--ppx-bg-active)' : (t.hue || 'var(--accent)') + '1f', color: t.hue || 'var(--accent)' }">
              <el-icon :size="18"><component :is="t.icon" /></el-icon>
            </span>
            <span class="cp-meta"><b>{{ t.name }}</b><small>{{ t.desc }}</small></span>
            <el-icon v-if="i === idx" :size="15" color="var(--accent)"><ArrowRight /></el-icon>
          </button>
        </div>
        <div class="cp-foot"><span><kbd>↑</kbd><kbd>↓</kbd> 选择</span><span><kbd>↵</kbd> 打开</span></div>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.cp-scrim {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(20, 24, 30, 0.32);
  backdrop-filter: blur(3px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 12vh;
}
[data-theme='dark'] .cp-scrim { background: rgba(0, 0, 0, 0.55); }
.cp-box {
  width: min(92vw, 560px);
  background: var(--ppx-bg-surface);
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  box-shadow: var(--ppx-shadow-lg);
  overflow: hidden;
}
.cp-head { display: flex; align-items: center; gap: 12px; padding: 15px 18px; border-bottom: 1px solid var(--ppx-glass-border); }
.cp-input { flex: 1; border: none; background: none; outline: none; font-size: 15.5px; color: var(--ppx-text-primary); }
.cp-list { max-height: 360px; overflow-y: auto; padding: 8px; }
.cp-empty { padding: 28px; text-align: center; color: var(--ppx-text-muted); }
.cp-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  background: transparent;
  border-radius: var(--ppx-radius-sm);
  cursor: pointer;
  text-align: left;
}
.cp-item.on { background: var(--ppx-bg-active); }
.cp-ico { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.cp-meta { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.cp-meta b { font-size: 13.5px; font-weight: 600; }
.cp-item.on .cp-meta b { color: var(--accent); }
.cp-meta small { font-size: 11.5px; color: var(--ppx-text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cp-foot { display: flex; gap: 16px; padding: 10px 18px; border-top: 1px solid var(--ppx-glass-border); font-size: 11.5px; color: var(--ppx-text-muted); }
kbd { font-family: var(--ppx-font-mono); background: var(--ppx-bg-inset); padding: 1px 6px; border-radius: 5px; margin-right: 3px; }
</style>
