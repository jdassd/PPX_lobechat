<!-- gui/src/components/shared/ToolWorkspace.vue
     通用工作区外壳: 左侧竖向子标签栏 + 右侧滚动内容区。
     用法(包裹现有 panel, 复用真实 API 逻辑):
       <ToolWorkspace v-model="activeTab" :tabs="tabs" accent="#2b6fff">
         <FormatPanel v-show="activeTab === 'convert'" ... />
         <CompressPanel v-show="activeTab === 'compress'" ... />
       </ToolWorkspace>
     - tabs: [{ name, label, icon? }]
     - 内容用 v-show 切换以保留各 panel 的内部状态。 -->
<script setup>
defineProps({
  modelValue: { type: String, required: true },
  tabs: { type: Array, required: true },
  accent: { type: String, default: 'var(--accent)' },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div class="ws" :style="{ '--accent': accent }">
    <nav class="subtabs">
      <button
        v-for="t in tabs"
        :key="t.name"
        class="subtab"
        :class="{ on: t.name === modelValue }"
        @click="emit('update:modelValue', t.name)"
      >
        <el-icon v-if="t.icon" :size="16" class="subtab-ico"><component :is="t.icon" /></el-icon>
        <span>{{ t.label }}</span>
      </button>
    </nav>

    <div class="form-area">
      <div class="form-inner">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.ws { display: flex; height: 100%; min-height: 0; }
.subtabs {
  width: 188px;
  flex-shrink: 0;
  border-right: 1px solid var(--ppx-glass-border);
  padding: 14px 10px;
  overflow-y: auto;
  background: var(--ppx-bg-base);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.subtab {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 11px;
  border: none;
  background: transparent;
  border-radius: var(--ppx-radius-sm);
  color: var(--ppx-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: all var(--ppx-transition-fast);
}
.subtab-ico { flex-shrink: 0; }
.subtab:hover { background: var(--ppx-bg-hover); color: var(--ppx-text-primary); }
.subtab.on { background: var(--ppx-bg-active); color: var(--accent); font-weight: 600; }
.form-area { flex: 1; min-width: 0; overflow-y: auto; overflow-x: hidden; padding: 24px; }
.form-inner { max-width: 760px; margin: 0 auto; }
</style>
