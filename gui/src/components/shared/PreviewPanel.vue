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
    <pre class="preview-body">
<code>{{ typeof content === 'string' ? content : JSON.stringify(content, null, 2) }}</code>
    </pre>
  </div>
</template>

<style scoped>
.preview-panel {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 14px;
  padding: 12px;
  background: var(--ppx-glass-bg);
  box-shadow: var(--ppx-shadow-sm);
}

.preview-title {
  margin: 0 0 8px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.preview-body {
  margin: 0;
  padding: 12px;
  background: #17130f;
  color: #f6f0e6;
  border-radius: 10px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.6;
  font-family: var(--ppx-font-mono);
}
</style>
