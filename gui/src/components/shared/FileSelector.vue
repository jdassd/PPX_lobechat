<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: {
    type: String,
    default: ''
  },
  description: {
    type: String,
    default: ''
  },
  files: {
    type: Array,
    default: () => []
  },
  buttonText: {
    type: String,
    default: '选择文件'
  },
  placeholder: {
    type: String,
    default: '尚未选择'
  },
  maxDisplay: {
    type: Number,
    default: 4
  },
  removable: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select', 'remove'])

const displayFiles = computed(() => {
  if (!Array.isArray(props.files)) return []
  return props.files.slice(0, props.maxDisplay)
})

const overflowCount = computed(() => {
  if (!Array.isArray(props.files)) return 0
  return Math.max(0, props.files.length - props.maxDisplay)
})

const resolveLabel = (file) => {
  if (!file) return ''
  if (typeof file === 'string') return file.split(/[\\/]/).pop()
  return file.filename || file.name || file.path || ''
}
</script>

<template>
  <div class="file-selector">
    <div class="selector-head">
      <div>
        <p v-if="label" class="selector-label">{{ label }}</p>
        <p v-if="description" class="selector-desc">{{ description }}</p>
      </div>
      <el-button size="small" @click="$emit('select')">
        {{ buttonText }}
      </el-button>
    </div>
    <div v-if="displayFiles.length" class="file-chips">
      <el-tag
        v-for="file in displayFiles"
        :key="resolveLabel(file)"
        :closable="removable"
        type="info"
        effect="plain"
        @close="$emit('remove', file)"
      >
        {{ resolveLabel(file) }}
      </el-tag>
      <el-tag v-if="overflowCount" type="primary" effect="plain">
        +{{ overflowCount }}
      </el-tag>
    </div>
    <el-tag v-else type="info" effect="plain">{{ placeholder }}</el-tag>
  </div>
</template>

<style scoped>
.file-selector {
  padding: 12px 16px;
  border: 1px dashed var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-base);
  box-shadow: var(--ppx-shadow-sm);
}

.selector-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.selector-label {
  margin: 0;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.selector-desc {
  margin: 4px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.file-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
