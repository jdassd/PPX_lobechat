<!-- gui/src/components/Sidebar.vue —— 固定侧边栏导航(可收起) -->
<script setup>
import { TOOLS, GROUPS, HOME } from '../config/tools'

defineProps({ active: String, collapsed: Boolean })
const emit = defineEmits(['select', 'toggle'])
const toolsOf = (g) => TOOLS.filter((t) => t.group === g)
</script>

<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="top">
      <button class="nav home" :class="{ on: active === 'home' }" @click="emit('select', 'home')" :title="collapsed ? '首页' : ''">
        <el-icon :size="18"><component :is="HOME.icon" /></el-icon>
        <span v-if="!collapsed">首页</span>
      </button>
    </div>

    <nav class="groups">
      <div v-for="g in GROUPS" :key="g.id" class="group">
        <div v-if="!collapsed" class="group-label">{{ g.label }}</div>
        <div v-else class="divider" />
        <button v-for="t in toolsOf(g.id)" :key="t.id" class="nav" :class="{ on: active === t.id }" :style="{ '--hue': t.hue }" @click="emit('select', t.id)" :title="collapsed ? t.name : ''">
          <span v-if="active === t.id && !collapsed" class="rail" />
          <el-icon :size="18"><component :is="t.icon" /></el-icon>
          <span v-if="!collapsed">{{ t.name }}</span>
        </button>
      </div>
    </nav>

    <button class="nav muted foot" @click="emit('toggle')">
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
.sidebar.collapsed .top {
  padding-left: 8px;
  padding-right: 8px;
}
.group {
  margin-bottom: 14px;
}
.group-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--ppx-text-disabled);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 6px 11px 5px;
}
.divider {
  height: 1px;
  background: var(--ppx-glass-border);
  margin: 8px 6px;
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
  background: transparent;
  border-radius: var(--ppx-radius-sm);
  color: var(--ppx-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--ppx-transition-fast);
  text-align: left;
}
.sidebar.collapsed .nav {
  justify-content: center;
  padding: 10px;
}
.nav:hover {
  background: var(--ppx-bg-hover);
  color: var(--ppx-text-primary);
}
.nav.on {
  background: var(--ppx-bg-active);
  color: var(--hue, var(--accent));
  font-weight: 600;
}
.nav.home.on {
  color: var(--accent);
}
.rail {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 99px;
  background: var(--hue, var(--accent));
}
.foot {
  flex-shrink: 0;
  margin: 0;
  border-top: 1px solid var(--ppx-glass-border);
  border-radius: 0;
  padding: 14px 12px;
  color: var(--ppx-text-muted);
}
.muted {
  color: var(--ppx-text-muted);
}
</style>
