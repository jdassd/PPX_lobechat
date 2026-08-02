<script setup>
import { computed } from 'vue'
import { ArrowRight, Clock, Grid, Lock, Search, Star, StarFilled } from '@element-plus/icons-vue'

import { FEATURED_ACTIONS, featureById, toolById } from '@/config/tools'
import { useToolRegistry } from '@/composables/useToolRegistry'
import { favoriteIds, toggleFavorite } from '@/utils/favorites'
import { recentActions, relativeTime } from '@/utils/recent'
import { recentTasks, runningTasks } from '@/utils/taskCenter'

const emit = defineEmits(['open', 'search', 'modules', 'tasks'])
const { enabledTools } = useToolRegistry()

const enabledIds = computed(() => new Set(enabledTools.value.map((tool) => tool.id)))
const favoriteSet = computed(() => new Set(favoriteIds.value))
const actionKey = (action) => `${action.tool}:${action.id || action.feature || ''}`
const isActionFavorite = (action) => favoriteSet.value.has(actionKey(action)) || favoriteSet.value.has(action.tool)
const featured = computed(() =>
  FEATURED_ACTIONS.filter((item) => enabledIds.value.has(item.tool))
    .sort((left, right) => Number(isActionFavorite(right)) - Number(isActionFavorite(left)))
    .slice(0, 8)
)
const recentItems = computed(() => recentActions.value.map((item) => ({ ...item, toolMeta: toolById(item.tool), featureMeta: featureById(item.tool, item.feature) })).filter((item) => item.toolMeta && enabledIds.value.has(item.tool)))
const taskItems = computed(() =>
  recentTasks.value
    .slice(0, 5)
    .map((task) => ({ ...task, toolMeta: toolById(task.tool) }))
    .filter((task) => task.toolMeta)
)
const statusLabel = { running: '处理中', success: '已完成', failed: '失败', interrupted: '已中断' }
const statusType = { running: 'warning', success: 'success', failed: 'danger', interrupted: 'info' }

const openAction = (action) => emit('open', { tool: action.tool, feature: action.id || action.feature })
const toggleActionFavorite = (action) => toggleFavorite(actionKey(action))
</script>

<template>
  <div class="home-scroll">
    <div class="home-inner">
      <section class="hero">
        <div class="eyebrow">
          <el-icon><Lock /></el-icon>本地优先 · 文件默认不离开电脑
        </div>
        <div class="hero-row">
          <div>
            <h1>从一个动作开始，<span>批量完成工作。</span></h1>
            <p>图片、PDF、Word、Excel 与文件整理汇集在同一个任务工作台。</p>
          </div>
          <button class="search-command" type="button" @click="emit('search')">
            <el-icon :size="19"><Search /></el-icon><span>搜索功能或动作</span><kbd>⌘ K</kbd>
          </button>
        </div>
      </section>

      <section class="section">
        <div class="section-head"><span>常用动作</span><small>直接进入具体步骤</small></div>
        <div class="action-grid">
          <article v-for="action in featured" :key="`${action.tool}-${action.id}`" class="action-card" :style="{ '--hue': action.hue }" role="button" tabindex="0" @click="openAction(action)" @keydown.enter="openAction(action)">
            <span class="action-icon"
              ><el-icon :size="19"><component :is="action.icon" /></el-icon
            ></span>
            <span class="action-meta"
              ><b>{{ action.label }}</b
              ><small>{{ action.toolName }}</small></span
            >
            <el-icon class="arrow"><ArrowRight /></el-icon>
            <button class="favorite-toggle" :class="{ active: isActionFavorite(action) }" type="button" :title="isActionFavorite(action) ? '取消收藏' : '收藏动作'" @click.stop="toggleActionFavorite(action)">
              <el-icon><StarFilled v-if="isActionFavorite(action)" /><Star v-else /></el-icon>
            </button>
          </article>
        </div>
        <div v-if="recentItems.length" class="recent-actions">
          <span>最近使用</span>
          <button v-for="item in recentItems" :key="`${item.tool}:${item.feature}`" type="button" @click="emit('open', { tool: item.tool, feature: item.feature })">
            <b>{{ item.featureMeta?.label || item.toolMeta.name }}</b
            ><small>{{ relativeTime(item.ts) }}</small>
          </button>
        </div>
      </section>

      <section class="work-grid">
        <div class="panel task-panel">
          <div class="panel-head">
            <div>
              <span>最近任务</span><small v-if="runningTasks.length">{{ runningTasks.length }} 个正在处理</small><small v-else>输出和失败记录都在这里</small>
            </div>
            <button class="panel-link" type="button" @click="emit('tasks')">全部任务</button>
          </div>
          <div v-if="taskItems.length" class="task-list">
            <button v-for="task in taskItems" :key="task.id" type="button" class="task-row" @click="emit('open', { tool: task.tool, feature: task.feature })">
              <span class="task-icon" :style="{ background: task.toolMeta.hue + '18', color: task.toolMeta.hue }"
                ><el-icon><component :is="task.toolMeta.icon" /></el-icon
              ></span>
              <span class="task-meta"
                ><b>{{ task.label }}</b
                ><small>{{ task.message }}</small></span
              >
              <el-tag :type="statusType[task.status]" size="small" effect="plain">{{ statusLabel[task.status] }}</el-tag>
            </button>
          </div>
          <div v-else class="empty-tasks">
            <el-icon :size="24"><Clock /></el-icon><span>完成一次文件处理后，结果会保留在这里</span>
          </div>
        </div>

        <div class="panel module-panel">
          <div class="panel-head">
            <div>
              <span>已启用模块</span><small>{{ enabledTools.length }} 个模块可用</small>
            </div>
            <button class="panel-link" type="button" @click="emit('modules')">管理</button>
          </div>
          <div class="module-list">
            <button v-for="tool in enabledTools.slice(0, 7)" :key="tool.id" type="button" @click="emit('open', { tool: tool.id })">
              <span :style="{ background: tool.hue + '18', color: tool.hue }"
                ><el-icon><component :is="tool.icon" /></el-icon
              ></span>
              <b>{{ tool.name }}</b>
            </button>
          </div>
          <button class="module-cta" type="button" @click="emit('modules')">
            <el-icon><Grid /></el-icon>开启视频、印章或高级模块
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-scroll {
  height: 100%;
  overflow: auto;
}
.home-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: clamp(24px, 4vw, 46px) clamp(20px, 4vw, 42px) 52px;
}
.hero {
  padding: clamp(22px, 3vw, 32px);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 20px;
  background: linear-gradient(135deg, var(--ppx-bg-surface), color-mix(in srgb, var(--accent) 7%, var(--ppx-bg-surface)));
  box-shadow: var(--ppx-shadow-sm);
}
.eyebrow {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--accent);
  font-size: 12.5px;
  font-weight: 650;
}
.hero-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  margin-top: 12px;
}
h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  line-height: 1.15;
  letter-spacing: -0.035em;
  color: var(--ppx-text-primary);
}
h1 span {
  color: var(--accent);
}
.hero p {
  margin: 10px 0 0;
  color: var(--ppx-text-muted);
  font-size: 14px;
}
.search-command {
  min-width: 286px;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 13px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  background: var(--ppx-bg-surface);
  color: var(--ppx-text-muted);
  box-shadow: var(--ppx-shadow-sm);
  cursor: pointer;
  text-align: left;
}
.search-command span {
  flex: 1;
}
kbd {
  padding: 3px 7px;
  border-radius: 6px;
  background: var(--ppx-bg-inset);
  font: 11px var(--ppx-font-mono);
}
.section {
  margin-top: 30px;
}
.section-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 13px;
}
.section-head span,
.panel-head span {
  color: var(--ppx-text-primary);
  font-size: 14px;
  font-weight: 750;
}
.section-head small,
.panel-head small {
  color: var(--ppx-text-muted);
  font-size: 11.5px;
}
.action-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.action-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  background: var(--ppx-bg-surface);
  color: var(--ppx-text-primary);
  cursor: pointer;
  text-align: left;
  transition: 0.18s ease;
}
.favorite-toggle {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 25px;
  height: 25px;
  display: grid;
  place-items: center;
  padding: 0;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--hue);
  cursor: pointer;
  opacity: 0;
}
.action-card:hover .favorite-toggle,
.favorite-toggle:focus-visible {
  opacity: 1;
  background: color-mix(in srgb, var(--hue) 10%, var(--ppx-bg-surface));
}
.favorite-toggle.active {
  opacity: 1;
}
.recent-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 11px;
  overflow-x: auto;
  color: var(--ppx-text-muted);
  font-size: 11px;
}
.recent-actions > span {
  flex: 0 0 auto;
  font-weight: 650;
}
.recent-actions button {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex: 0 0 auto;
  padding: 6px 9px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 8px;
  background: var(--ppx-bg-surface);
  color: var(--ppx-text-primary);
  cursor: pointer;
}
.recent-actions button:hover {
  border-color: var(--accent);
}
.recent-actions b {
  font-size: 11.5px;
}
.recent-actions small {
  color: var(--ppx-text-muted);
  font-size: 10px;
}
.action-card:hover {
  transform: translateY(-2px);
  border-color: var(--hue);
  box-shadow: var(--ppx-shadow-sm);
}
.action-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 10px;
  background: color-mix(in srgb, var(--hue) 11%, transparent);
  color: var(--hue);
}
.action-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.action-meta b {
  font-size: 12.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-meta small {
  margin-top: 2px;
  color: var(--ppx-text-muted);
  font-size: 10.5px;
}
.arrow {
  color: var(--hue);
  opacity: 0.65;
}
.work-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
  gap: 14px;
  margin-top: 28px;
}
.panel {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 16px;
  background: var(--ppx-bg-surface);
  padding: 16px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.panel-head > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.panel-link {
  padding: 5px 8px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}
.panel-link:hover {
  background: var(--ppx-bg-hover);
}
.task-list {
  display: flex;
  flex-direction: column;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 6px;
  border: none;
  border-top: 1px solid var(--ppx-glass-border);
  background: transparent;
  color: var(--ppx-text-primary);
  cursor: pointer;
  text-align: left;
}
.task-row:first-child {
  border-top: none;
}
.task-row:hover {
  background: var(--ppx-bg-hover);
}
.task-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 9px;
}
.task-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.task-meta b {
  font-size: 12.5px;
}
.task-meta small {
  margin-top: 2px;
  color: var(--ppx-text-muted);
  font-size: 10.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty-tasks {
  min-height: 168px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.module-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 7px;
}
.module-list button {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px;
  border: none;
  border-radius: 9px;
  background: var(--ppx-bg-inset);
  color: var(--ppx-text-primary);
  cursor: pointer;
  text-align: left;
}
.module-list button:hover {
  background: var(--ppx-bg-hover);
}
.module-list button span {
  width: 27px;
  height: 27px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
}
.module-list button b {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11.5px;
}
.module-cta {
  width: 100%;
  margin-top: 10px;
  padding: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px dashed var(--ppx-glass-border-hover);
  border-radius: 9px;
  background: transparent;
  color: var(--accent);
  cursor: pointer;
  font-size: 11.5px;
}
@media (max-width: 900px) {
  .hero-row {
    align-items: stretch;
    flex-direction: column;
  }
  .search-command {
    width: 100%;
    min-width: 0;
  }
  .action-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .work-grid {
    grid-template-columns: 1fr;
  }
}
</style>
