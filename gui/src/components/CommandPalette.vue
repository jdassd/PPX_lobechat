<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowRight, Clock, Grid, HomeFilled, Search, StarFilled } from '@element-plus/icons-vue'

import { useToolRegistry } from '@/composables/useToolRegistry'
import { favoriteIds } from '@/utils/favorites'
import { recentActions } from '@/utils/recent'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'select'])
const { enabledTools } = useToolRegistry()

const q = ref('')
const idx = ref(0)
const inputRef = ref(null)
const favoriteSet = computed(() => new Set(favoriteIds.value))
const recentRank = computed(() => new Map(recentActions.value.map((item, index) => [`${item.tool}:${item.feature || ''}`, index])))

const items = computed(() => {
  const pages = [
    { key: 'page-home', name: '首页', desc: '返回工作台', target: 'home', icon: HomeFilled, hue: '#2b6fff', keywords: [] },
    { key: 'page-tasks', name: '任务中心', desc: '查看处理记录与输出', target: 'tasks', icon: Clock, hue: '#5d6b7a', keywords: ['历史', '结果'] },
    { key: 'page-modules', name: '模块管理', desc: '开启可选工具与检查依赖', target: 'modules', icon: Grid, hue: '#7c5cff', keywords: ['功能', '依赖', '设置'] }
  ]
  const tools = enabledTools.value.flatMap((tool) => [
    {
      key: `tool-${tool.id}`,
      name: tool.name,
      desc: tool.desc,
      target: { tool: tool.id },
      icon: tool.icon,
      hue: tool.hue,
      keywords: tool.points || [],
      favoriteId: tool.id
    },
    ...(tool.features || []).map((feature) => ({
      key: `${tool.id}-${feature.id}`,
      name: feature.label,
      desc: tool.name,
      target: { tool: tool.id, feature: feature.id },
      icon: tool.icon,
      hue: tool.hue,
      keywords: feature.keywords || [],
      favoriteId: `${tool.id}:${feature.id}`
    }))
  ])
  return [...pages, ...tools].map((item) => ({ ...item, favorite: item.favoriteId ? favoriteSet.value.has(item.favoriteId) || favoriteSet.value.has(item.target?.tool) : false, recent: item.favoriteId ? recentRank.value.get(item.favoriteId) : undefined })).sort((left, right) => Number(right.favorite) - Number(left.favorite) || (left.recent ?? 99) - (right.recent ?? 99))
})

const filtered = computed(() => {
  const keyword = q.value.trim().toLowerCase()
  if (!keyword) return items.value.slice(0, 18)
  return items.value.filter((item) => `${item.name} ${item.desc} ${(item.keywords || []).join(' ')}`.toLowerCase().includes(keyword)).slice(0, 30)
})

watch(
  () => props.modelValue,
  (value) => {
    if (!value) return
    q.value = ''
    idx.value = 0
    nextTick(() => inputRef.value?.focus())
  }
)
watch(q, () => {
  idx.value = 0
})

const close = () => emit('update:modelValue', false)
const choose = (item) => {
  emit('select', item.target)
  close()
}
const onKey = (event) => {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    idx.value = Math.min(idx.value + 1, filtered.value.length - 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    idx.value = Math.max(idx.value - 1, 0)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    if (filtered.value[idx.value]) choose(filtered.value[idx.value])
  } else if (event.key === 'Escape') close()
}
</script>

<template>
  <teleport to="body">
    <div v-if="modelValue" class="cp-scrim" @click="close">
      <div class="cp-box" role="dialog" aria-modal="true" aria-label="搜索功能" @click.stop>
        <div class="cp-head">
          <el-icon :size="19" color="var(--ppx-text-muted)"><Search /></el-icon>
          <input ref="inputRef" v-model="q" class="cp-input" aria-label="搜索工具和功能" placeholder="搜索工具或具体动作，例如「OCR」「合并 PDF」" @keydown="onKey" />
          <kbd>ESC</kbd>
        </div>
        <div class="cp-list" role="listbox" aria-label="搜索结果">
          <div v-if="!filtered.length" class="cp-empty">没有匹配项</div>
          <button v-for="(item, index) in filtered" :key="item.key" class="cp-item" :class="{ on: index === idx }" role="option" :aria-selected="index === idx" @mouseenter="idx = index" @click="choose(item)">
            <span class="cp-ico" :style="{ background: item.hue + '1f', color: item.hue }">
              <el-icon :size="18"><component :is="item.icon" /></el-icon>
            </span>
            <span class="cp-meta"
              ><b>{{ item.name }}</b
              ><small>{{ item.desc }}</small></span
            >
            <el-icon v-if="item.favorite" class="cp-favorite" :size="14"><StarFilled /></el-icon>
            <el-icon v-if="index === idx" :size="15" color="var(--accent)"><ArrowRight /></el-icon>
          </button>
        </div>
        <div class="cp-foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span><span><kbd>↵</kbd> 打开</span>
        </div>
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
[data-theme='dark'] .cp-scrim {
  background: rgba(0, 0, 0, 0.55);
}
.cp-box {
  width: min(92vw, 600px);
  background: var(--ppx-bg-surface);
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  box-shadow: var(--ppx-shadow-lg);
  overflow: hidden;
}
.cp-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 18px;
  border-bottom: 1px solid var(--ppx-glass-border);
}
.cp-input {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  font-size: 15.5px;
  color: var(--ppx-text-primary);
}
.cp-list {
  max-height: 420px;
  overflow-y: auto;
  padding: 8px;
}
.cp-empty {
  padding: 28px;
  text-align: center;
  color: var(--ppx-text-muted);
}
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
  color: var(--ppx-text-primary);
}
.cp-item.on {
  background: var(--ppx-bg-active);
}
.cp-ico {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.cp-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.cp-meta b {
  font-size: 13.5px;
  font-weight: 600;
}
.cp-item.on .cp-meta b {
  color: var(--accent);
}
.cp-meta small {
  font-size: 11.5px;
  color: var(--ppx-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cp-favorite {
  color: var(--el-color-warning);
}
.cp-foot {
  display: flex;
  gap: 16px;
  padding: 10px 18px;
  border-top: 1px solid var(--ppx-glass-border);
  font-size: 11.5px;
  color: var(--ppx-text-muted);
}
kbd {
  font-family: var(--ppx-font-mono);
  background: var(--ppx-bg-inset);
  padding: 1px 6px;
  border-radius: 5px;
  margin-right: 3px;
}
</style>
