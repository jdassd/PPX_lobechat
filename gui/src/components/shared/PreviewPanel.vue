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
  border: 1px solid #e2e6f2;
  border-radius: 12px;
  padding: 12px;
  background: #fdfdff;
}

.preview-title {
  margin: 0 0 8px;
  font-weight: 600;
  color: #30374f;
}

.preview-body {
  margin: 0;
  padding: 12px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.6;
}
</style>
