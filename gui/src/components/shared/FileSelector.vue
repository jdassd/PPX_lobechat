<script setup>
import { computed, getCurrentInstance, ref, watch } from 'vue'
import { consumeIncomingFiles, currentIncomingAssets as incomingAssets, mergeFileQueue } from '../../utils/workspace'

const props = defineProps({
  label: { type: String, default: '' },
  description: { type: String, default: '' },
  files: { type: Array, default: () => [] },
  buttonText: { type: String, default: '选择文件' },
  placeholder: { type: String, default: '尚未选择' },
  maxDisplay: { type: Number, default: 8 },
  removable: { type: Boolean, default: false }
})
const emit = defineEmits(['select', 'remove', 'update:files'])
const instance = getCurrentInstance()
const managed = computed(() => Boolean(instance.vnode.props?.['onUpdate:files']))
const page = ref(1)
const selected = ref([])
const dragPath = ref('')
const pathOf = (file) => (typeof file === 'string' ? file : file?.path || '')
const nameOf = (file) => file?.filename || file?.name || pathOf(file).split(/[\\/]/).pop()
const size = computed(() => Math.max(4, Math.min(50, props.maxDisplay)))
const displayFiles = computed(() => props.files.slice((page.value - 1) * size.value, page.value * size.value))
watch(
  () => props.files.length,
  () => {
    page.value = Math.min(page.value, Math.max(1, Math.ceil(props.files.length / size.value)))
    selected.value = selected.value.filter((path) => props.files.some((item) => pathOf(item) === path))
  }
)
const move = (file, delta) => {
  const result = [...props.files]
  const from = result.findIndex((item) => pathOf(item) === pathOf(file))
  const to = from + delta
  if (to < 0 || to >= result.length) return
  result.splice(to, 0, result.splice(from, 1)[0])
  emit('update:files', result)
}
const drop = (file) => {
  const from = props.files.findIndex((item) => pathOf(item) === dragPath.value)
  const to = props.files.findIndex((item) => pathOf(item) === pathOf(file))
  if (from >= 0) move(props.files[from], to - from)
}
const remove = (file) => {
  if (managed.value)
    emit(
      'update:files',
      props.files.filter((item) => pathOf(item) !== pathOf(file))
    )
  else emit('remove', file)
}
const acceptIncoming = () => {
  emit('update:files', mergeFileQueue(props.files, consumeIncomingFiles()))
}
</script>

<template>
  <div class="file-selector">
    <div class="selector-head">
      <div>
        <strong>{{ label }}</strong>
        <p v-if="description">{{ description }}</p>
      </div>
      <el-button size="small" @click="emit('select')">{{ files.length ? '追加文件' : buttonText }}</el-button>
    </div>
    <el-button v-if="managed && incomingAssets.length" type="primary" plain size="small" @click="acceptIncoming">使用上一步的 {{ incomingAssets.length }} 个结果</el-button>
    <div v-if="managed && files.length > 1" class="queue-tools">
      <el-checkbox :model-value="selected.length === files.length" :indeterminate="selected.length > 0 && selected.length < files.length" @change="selected = $event ? files.map(pathOf) : []">全选 {{ files.length }} 个文件</el-checkbox>
      <el-button
        size="small"
        text
        :disabled="!selected.length"
        @click="
          emit(
            'update:files',
            files.filter((file) => !selected.includes(pathOf(file)))
          )
        "
        >移除所选 {{ selected.length || '' }}</el-button
      >
    </div>
    <el-checkbox-group v-model="selected">
      <div v-for="file in displayFiles" :key="pathOf(file)" class="queue-row" :draggable="managed" @dragstart="dragPath = pathOf(file)" @dragover.prevent @drop.prevent="drop(file)">
        <el-checkbox v-if="managed" :label="pathOf(file)"
          ><span class="sr-only">选择 {{ nameOf(file) }}</span></el-checkbox
        >
        <div class="file-name">
          <strong>{{ nameOf(file) }}</strong
          ><small :title="pathOf(file)">{{ pathOf(file) }}</small>
        </div>
        <slot name="options" :file="file" />
        <el-button v-if="managed" text size="small" :aria-label="'上移 ' + nameOf(file)" @click="move(file, -1)">↑</el-button>
        <el-button v-if="managed" text size="small" :aria-label="'下移 ' + nameOf(file)" @click="move(file, 1)">↓</el-button>
        <el-button v-if="removable || managed" text size="small" :aria-label="'移除 ' + nameOf(file)" @click="remove(file)">移除</el-button>
      </div>
    </el-checkbox-group>
    <el-pagination v-if="files.length > size" v-model:current-page="page" :total="files.length" :page-size="size" small layout="prev, pager, next, total" />
    <span v-if="!files.length" class="empty">{{ placeholder }}</span>
  </div>
</template>

<style scoped>
.file-selector {
  padding: 12px 16px;
  border: 1px dashed var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-base);
}
.selector-head,
.queue-tools,
.queue-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.selector-head,
.queue-tools {
  justify-content: space-between;
  margin-bottom: 8px;
}
.selector-head p,
.empty {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.queue-row {
  padding: 6px 0;
  border-top: 1px solid var(--ppx-glass-border);
}
.file-name {
  flex: 1;
  min-width: 0;
  font-size: 12px;
}
.file-name small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ppx-text-muted);
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
</style>
