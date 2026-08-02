<script setup>
import { ArrowRight, List, SetUp } from '@element-plus/icons-vue'

import { HOME } from '@/config/tools'
import { useToolRegistry } from '@/composables/useToolRegistry'

defineProps({
  active: { type: String, default: 'home' },
  collapsed: { type: Boolean, default: false }
})
const emit = defineEmits(['select', 'toggle'])
const { groupedTools } = useToolRegistry()
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }" aria-label="主导航">
    <div class="top">
      <button class="nav home" :class="{ on: active === 'home' }" :aria-current="active === 'home' ? 'page' : undefined" :aria-label="collapsed ? '首页' : undefined" @click="emit('select', 'home')">
        <el-icon :size="18"><component :is="HOME.icon" /></el-icon>
        <span v-if="!collapsed">首页</span>
      </button>
    </div>

    <nav class="groups" aria-label="工具">
      <div v-for="group in groupedTools" :key="group.id" class="group">
        <div v-if="!collapsed" class="group-label">{{ group.label }}</div>
        <div v-else class="divider" />
        <button v-for="tool in group.tools" :key="tool.id" class="nav" :class="{ on: active === tool.id }" :style="{ '--hue': tool.hue }" :aria-current="active === tool.id ? 'page' : undefined" :aria-label="collapsed ? tool.name : undefined" @click="emit('select', tool.id)">
          <span v-if="active === tool.id && !collapsed" class="rail" />
          <el-icon :size="18"><component :is="tool.icon" /></el-icon>
          <span v-if="!collapsed" class="nav-label">{{ tool.name }}</span>
          <span v-if="!collapsed && tool.experimental" class="beta-dot" title="实验性模块" />
        </button>
      </div>
    </nav>

    <div class="sidebar-utilities">
      <button class="nav muted" :class="{ on: active === 'tasks' }" :aria-current="active === 'tasks' ? 'page' : undefined" :aria-label="collapsed ? '任务中心' : undefined" @click="emit('select', 'tasks')">
        <el-icon :size="18"><List /></el-icon>
        <span v-if="!collapsed">任务中心</span>
      </button>
      <button class="nav muted" :class="{ on: active === 'modules' }" :aria-current="active === 'modules' ? 'page' : undefined" :aria-label="collapsed ? '工具与能力' : undefined" @click="emit('select', 'modules')">
        <el-icon :size="18"><SetUp /></el-icon>
        <span v-if="!collapsed">工具与能力</span>
      </button>
    </div>

    <button class="nav muted foot" :aria-expanded="!collapsed" :aria-label="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('toggle')">
      <el-icon :size="18" :style="{ transform: collapsed ? 'none' : 'rotate(180deg)' }"><ArrowRight /></el-icon>
      <span v-if="!collapsed">收起侧栏</span>
    </button>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 224px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--ppx-bg-elevated);
  border-right: 1px solid var(--ppx-glass-border);
  transition: width var(--ppx-transition-normal);
  overflow: hidden;
}
.sidebar.collapsed {
  width: 64px;
}
.top {
  padding: 12px;
}
.groups {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}
.sidebar.collapsed .groups,
.sidebar.collapsed .top,
.sidebar.collapsed .sidebar-utilities {
  padding-left: 8px;
  padding-right: 8px;
}
.group {
  margin-bottom: 12px;
}
.group-label {
  padding: 6px 11px 5px;
  color: var(--ppx-text-disabled);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.divider {
  height: 1px;
  margin: 8px 6px;
  background: var(--ppx-glass-border);
}
.nav {
  position: relative;
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  margin-bottom: 2px;
  padding: 9px 11px;
  border: none;
  border-radius: var(--ppx-radius-sm);
  background: transparent;
  color: var(--ppx-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all var(--ppx-transition-fast);
}
.sidebar.collapsed .nav {
  justify-content: center;
  padding: 10px;
}
.nav:hover,
.nav:focus-visible {
  background: var(--ppx-bg-hover);
  color: var(--ppx-text-primary);
  outline: none;
}
.nav.on {
  background: var(--ppx-bg-active);
  color: var(--hue, var(--accent));
  font-weight: 600;
}
.nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rail {
  position: absolute;
  left: 0;
  top: 50%;
  width: 3px;
  height: 18px;
  border-radius: 99px;
  background: var(--hue, var(--accent));
  transform: translateY(-50%);
}
.beta-dot {
  width: 6px;
  height: 6px;
  margin-left: auto;
  border-radius: 50%;
  background: #8a5cf5;
}
.sidebar-utilities {
  flex-shrink: 0;
  padding: 8px 12px;
  border-top: 1px solid var(--ppx-glass-border);
}
.muted {
  color: var(--ppx-text-muted);
}
.foot {
  flex-shrink: 0;
  margin: 0;
  padding: 12px;
  border-top: 1px solid var(--ppx-glass-border);
  border-radius: 0;
}
</style>
