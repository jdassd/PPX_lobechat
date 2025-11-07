<script setup>
import { computed } from 'vue'
import { useToolkitStore } from '@/stores/toolkit'

const store = useToolkitStore()
const groups = computed(() => store.navGroups)

const handleSelect = (tool, disabled) => {
  if (disabled) {
    return
  }
  store.setActiveTool(tool.id)
}
</script>

<template>
  <aside class="side-nav glass-panel">
    <div
      v-for="group in groups"
      :key="group.id"
      class="side-nav__group"
    >
      <div class="side-nav__group-title">
        <component :is="group.icon" />
        <span>{{ group.label }}</span>
      </div>

      <div class="side-nav__items">
        <button
          v-for="tool in group.tools"
          :key="tool.id"
          class="side-nav__item"
          :class="{
            'is-active': store.activeTool === tool.id,
            'is-disabled': tool.disabled
          }"
          type="button"
          @click="handleSelect(tool, tool.disabled)"
        >
          <span>{{ tool.label }}</span>
          <template v-if="tool.badge">
            <el-tag type="info" size="small">{{ tool.badge }}</el-tag>
          </template>
          <template v-else-if="tool.status">
            <small>{{ tool.status }}</small>
          </template>
        </button>
      </div>
    </div>
  </aside>
</template>
