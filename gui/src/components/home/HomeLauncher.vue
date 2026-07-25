<!-- gui/src/components/home/HomeLauncher.vue —— 首页 Dashboard
     问候(按时段) + 搜索框(⌘K 提示) + 最近活动 + 全部工具网格 -->
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { TOOLS, toolById } from '@/config/tools'
import { getFavorites, toggleFavorite as persistFavorite } from '@/utils/favorites'
import { clearRecents, getRecents, relativeTime } from '@/utils/recent'

const emit = defineEmits(['open'])

const hour = new Date().getHours()
const greet = hour < 6 ? '夜深了' : hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好'

const q = ref('')
const favoriteIds = ref(getFavorites())
const recentRevision = ref(0)
const now = ref(Date.now())
let clockTimer = null

const isFavorite = (id) => favoriteIds.value.includes(id)
const filtered = computed(() => {
  const k = q.value.trim().toLowerCase()
  const matches = k ? TOOLS.filter((t) => (t.name + t.desc + t.points.join('')).toLowerCase().includes(k)) : [...TOOLS]
  return matches.sort((a, b) => Number(isFavorite(b.id)) - Number(isFavorite(a.id)))
})

const recents = computed(() => {
  recentRevision.value
  const currentTime = now.value
  return getRecents()
    .map((r) => ({ ...r, tool: toolById(r.tool) }))
    .filter((r) => r.tool)
    .map((r) => ({ ...r, timeLabel: relativeTime(r.ts, currentTime) }))
})

const open = (id) => emit('open', id)
const toggleFavorite = (id) => {
  favoriteIds.value = persistFavorite(id)
}
const clearRecentActivity = () => {
  clearRecents()
  recentRevision.value += 1
}

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 30000)
})
onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})
</script>

<template>
  <div class="home-scroll">
    <div class="home-inner">
      <!-- hero -->
      <div class="hero">
        <div class="eyebrow">
          <el-icon :size="14"><Lock /></el-icon>
          默认本地处理 · 联网与协作功能由你主动开启
        </div>
        <h1 class="greet">{{ greet }}，<span class="accent">欢迎使用工具箱</span></h1>
        <p class="subtitle">{{ TOOLS.length }} 个实用工具，覆盖图片、文档、表格、文本、视频、文件与系统维护。</p>
      </div>

      <!-- search -->
      <div class="search-wrap">
        <el-icon class="search-ico" :size="18"><Search /></el-icon>
        <input v-model="q" class="search-input" placeholder="搜索工具或功能，例如「压缩」「合并 PDF」" />
        <kbd>⌘K</kbd>
      </div>

      <!-- recent -->
      <div v-if="!q && recents.length" class="section">
        <div class="section-label">
          <el-icon :size="16"><Clock /></el-icon><span>最近活动</span>
          <span class="section-spacer" />
          <button class="section-action" type="button" @click="clearRecentActivity">清空</button>
        </div>
        <div class="recent-grid">
          <button v-for="r in recents" :key="r.tool.id" class="recent-card" @click="open(r.tool.id)">
            <span class="ricon" :style="{ background: r.tool.hue + '1f', color: r.tool.hue }">
              <el-icon :size="19"><component :is="r.tool.icon" /></el-icon>
            </span>
            <div class="rmeta">
              <div class="rname">{{ r.tool.name }}</div>
              <div class="rtime">{{ r.timeLabel }}</div>
            </div>
          </button>
        </div>
      </div>

      <!-- all tools -->
      <div class="section">
        <div class="section-label">
          <el-icon :size="16"><Grid /></el-icon>
          <span>{{ q ? `搜索结果 · ${filtered.length}` : '全部工具 · 收藏优先' }}</span>
        </div>
        <el-empty v-if="!filtered.length" description="没有匹配的工具" />
        <div v-else class="tools-grid">
          <article v-for="t in filtered" :key="t.id" class="tcard" :style="{ '--hue': t.hue }">
            <button class="card-open" type="button" :aria-label="`打开${t.name}`" @click="open(t.id)" />
            <span class="tcard-rail" />
            <div class="tcard-head">
              <span class="ticon" :style="{ background: t.hue + '1a', color: t.hue }"
                ><el-icon :size="23"><component :is="t.icon" /></el-icon
              ></span>
              <div class="ttitle">
                <div class="tname">{{ t.name }}</div>
                <div class="tdesc">{{ t.desc }}</div>
              </div>
              <button class="favorite-btn" :class="{ active: isFavorite(t.id) }" type="button" :aria-label="isFavorite(t.id) ? `取消收藏${t.name}` : `收藏${t.name}`" :title="isFavorite(t.id) ? '取消收藏' : '收藏置顶'" @click.stop="toggleFavorite(t.id)">
                <el-icon :size="16"><StarFilled v-if="isFavorite(t.id)" /><Star v-else /></el-icon>
              </button>
              <el-icon class="tarrow" :size="17"><ArrowRight /></el-icon>
            </div>
            <div class="tpoints">
              <div v-for="p in t.points.slice(0, 3)" :key="p" class="tpoint">
                <span class="dot" />
                <span>{{ p }}</span>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}
.home-inner {
  max-width: 1080px;
  margin: 0 auto;
  padding: clamp(24px, 4vw, 44px) clamp(20px, 4vw, 40px) 48px;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ppx-text-muted);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 10px;
}
.greet {
  margin: 0;
  font-size: clamp(28px, 4vw, 38px);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ppx-text-primary);
}
.greet .accent {
  color: var(--accent);
}
.subtitle {
  margin: 10px 0 0;
  font-size: 15px;
  color: var(--ppx-text-muted);
}

.search-wrap {
  position: relative;
  max-width: 560px;
  margin: 28px 0;
}
.search-ico {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ppx-text-muted);
}
.search-input {
  width: 100%;
  height: 50px;
  box-sizing: border-box;
  padding: 0 46px;
  font-size: 14.5px;
  border-radius: var(--ppx-radius-md);
  border: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-surface);
  color: var(--ppx-text-primary);
  outline: none;
  box-shadow: var(--ppx-shadow-sm);
  transition: border var(--ppx-transition-fast);
  font-family: var(--ppx-font-body);
}
.search-input:focus {
  border-color: var(--accent);
}
.search-input::placeholder {
  color: var(--ppx-text-disabled);
}
.search-wrap kbd {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  font-weight: 600;
  color: var(--ppx-text-muted);
  background: var(--ppx-bg-inset);
  padding: 3px 8px;
  border-radius: 6px;
  font-family: var(--ppx-font-mono);
}

.section {
  margin-bottom: 34px;
}
.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  color: var(--ppx-text-secondary);
}
.section-label span {
  font-size: 13.5px;
  font-weight: 700;
}
.section-spacer {
  flex: 1;
}
.section-action {
  border: none;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 5px;
  font: inherit;
  font-size: 12px;
}
.section-action:hover {
  background: var(--ppx-bg-hover);
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(248px, 1fr));
  gap: var(--ppx-gap);
}
.recent-card {
  text-align: left;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: var(--ppx-radius-md);
  border: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-surface);
  cursor: pointer;
  transition: all var(--ppx-transition-fast);
}
.recent-card:hover {
  border-color: var(--ppx-glass-border-hover);
  transform: translateY(-2px);
  box-shadow: var(--ppx-shadow-sm);
}
.ricon {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rmeta {
  min-width: 0;
}
.rname {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rtime {
  font-size: 11.5px;
  color: var(--ppx-text-muted);
  margin-top: 2px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--ppx-gap);
}
.tcard {
  text-align: left;
  display: flex;
  flex-direction: column;
  padding: calc(var(--ppx-pad) + 2px);
  border-radius: var(--ppx-radius-lg);
  border: 1px solid var(--ppx-glass-border);
  background: var(--ppx-bg-surface);
  box-shadow: var(--ppx-shadow-sm);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all var(--ppx-transition-normal);
}
.tcard:hover {
  transform: translateY(-4px);
  box-shadow: var(--ppx-shadow-md);
  border-color: var(--hue);
}
.tcard-rail {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--hue);
  opacity: 0;
  transition: opacity var(--ppx-transition-normal);
}
.tcard:hover .tcard-rail {
  opacity: 1;
}
.tcard-head {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  margin-bottom: 13px;
}
.ticon {
  width: 46px;
  height: 46px;
  flex-shrink: 0;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ttitle {
  flex: 1;
  min-width: 0;
}
.tname {
  font-size: 16px;
  font-weight: 700;
  color: var(--ppx-text-primary);
}
.tdesc {
  font-size: 12.5px;
  color: var(--ppx-text-muted);
  margin-top: 2px;
}
.tarrow {
  color: var(--hue);
  opacity: 0;
  transform: translateX(-6px);
  transition: all var(--ppx-transition-normal);
}
.card-open {
  position: absolute;
  inset: 0;
  z-index: 1;
  border: none;
  border-radius: inherit;
  background: transparent;
  cursor: pointer;
}
.card-open:focus-visible {
  outline: 2px solid var(--hue);
  outline-offset: -3px;
}
.favorite-btn {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--ppx-text-disabled);
  cursor: pointer;
  transition: all var(--ppx-transition-fast);
  position: relative;
  z-index: 2;
}
.favorite-btn:hover,
.favorite-btn.active {
  color: #e0a500;
  background: #e0a50018;
}
.tcard:hover .tarrow {
  opacity: 1;
  transform: none;
}
.tpoints {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tpoint {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 12.5px;
  color: var(--ppx-text-secondary);
}
.tpoint .dot {
  width: 5px;
  height: 5px;
  border-radius: 99px;
  background: var(--hue);
  margin-top: 6.5px;
  flex-shrink: 0;
}
</style>
