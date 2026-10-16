<script setup>
const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  content: {
    type: [String, Object],
    default: ''
  },
  language: {
    type: String,
    default: 'text'
  }
})
</script>

<template>
  <div class="preview-panel">
    <p v-if="title" class="preview-title">{{ title }}</p>
    <p v-if="content === ''" class="preview-empty">处理后在此查看结果</p>
    <pre v-else class="preview-body">
<code>{{ typeof content === 'string' ? content : JSON.stringify(content, null, 2) }}</code>
    </pre>
  </div>
</template>

<style scoped>
.preview-panel {
  min-width: 0;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 14px;
  padding: 12px;
  background: var(--ppx-glass-bg);
}

.preview-title {
  margin: 0 0 8px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.preview-body {
  margin: 0;
  padding: 12px;
  background: var(--ppx-bg-inset);
  color: var(--ppx-text-primary);
  border-radius: 10px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: var(--ppx-font-mono);
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 96px;
  margin: 0;
  padding: 12px;
  box-sizing: border-box;
  border-radius: 10px;
  background: var(--ppx-bg-inset);
  color: var(--ppx-text-secondary);
  font-size: 13px;
}
</style>
