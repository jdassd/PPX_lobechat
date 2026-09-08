<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { callApiRaw } from '../../utils/pyapi'
import MappingEditor from './MappingEditor.vue'
import { referenceOptions } from '@/utils/workflowResults.mjs'
const props = defineProps({ modelValue: { type: String, default: '{}' }, fields: { type: Array, default: () => [] }, previous: { type: Array, default: () => [] }, disabled: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue'])
const advanced = ref(false)
const error = ref('')
const jsonDrafts = ref({})
const availableReferences = computed(() => Object.fromEntries(props.fields.map((field) => [field.name, referenceOptions(props.previous, field)])))
let revision = 0
watch(
  () => [props.modelValue, props.disabled, props.fields],
  () => {
    revision += 1
    try {
      const parsed = JSON.parse(props.modelValue || '{}')
      if (parsed && !Array.isArray(parsed) && typeof parsed === 'object') error.value = ''
    } catch {
      /* Preserve the current editing error until valid input arrives. */
    }
  },
  { flush: 'sync' }
)
onBeforeUnmount(() => {
  revision += 1
})
const values = computed(() => {
  try {
    const parsed = JSON.parse(props.modelValue || '{}')
    return parsed && !Array.isArray(parsed) && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
})
const set = (name, value) => {
  if (!props.disabled) emit('update:modelValue', JSON.stringify({ ...values.value, [name]: value }, null, 2))
}
const isReference = (field) => typeof values.value[field.name] === 'string' && values.value[field.name].startsWith('{{')
const display = (field) => values.value[field.name] ?? field.default ?? (field.type === 'boolean' ? false : '')
const choose = async (field) => {
  if (props.disabled) return
  const requestRevision = revision
  try {
    if (['directory', 'directories'].includes(field.type)) {
      const directory = await callApiRaw('system_pySelectDirDialog', '')
      if (props.disabled || revision !== requestRevision) return
      if (directory) set(field.name, field.type === 'directories' ? [...new Set([...(values.value[field.name] || []), directory])] : directory)
    } else {
      const files = await callApiRaw('system_pyCreateFileDialog', ['全部文件 (*.*)'])
      if (props.disabled || revision !== requestRevision) return
      if (files?.length) set(field.name, field.type === 'tables' ? [...(values.value[field.name] || []), ...files.map((file) => ({ path: file.path, sheet: '', headerRow: 1, fieldMapping: {} }))] : ['files', 'paths'].includes(field.type) ? files.map((file) => file.path) : files[0].path)
    }
  } catch (err) {
    ElMessage.error(err.message)
  }
}
const reference = (field, binding) => {
  if (props.disabled) return
  set(field.name, binding || (field.default ?? (['files', 'list', 'paths', 'directories', 'tables'].includes(field.type) ? [] : '')))
}
const editJson = (value) => {
  if (props.disabled) return
  emit('update:modelValue', value)
  try {
    const parsed = JSON.parse(value)
    error.value = parsed && !Array.isArray(parsed) && typeof parsed === 'object' ? '' : '参数必须是对象'
  } catch {
    error.value = 'JSON 尚未完整，请修正后保存'
  }
}
const editObject = (field, value) => {
  let parsed
  try {
    parsed = JSON.parse(value || '{}')
    error.value = ''
  } catch {
    parsed = value
  }
  // Keep the user's spacing and caret stable while still submitting the latest
  // value (including invalid JSON) for validation instead of the previous rules.
  jsonDrafts.value[field.name] = { text: value, stamp: JSON.stringify(parsed) }
  set(field.name, parsed)
}
const jsonText = (field) => {
  const value = display(field)
  const draft = jsonDrafts.value[field.name]
  return draft?.stamp === JSON.stringify(value) ? draft.text : typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}
const jsonFieldError = (field) => {
  const value = values.value[field.name]
  if (field.type !== 'json' || value == null || isReference(field)) return ''
  if (field.jsonType === 'array' && !Array.isArray(value)) return '请填写 JSON 列表，例如 [{"search":"原文","replace":"新文"}]'
  if (typeof value !== 'object') return '请填写合法的 JSON 对象或列表'
  return ''
}
const updateTable = (field, index, key, value) =>
  set(
    field.name,
    (values.value[field.name] || []).map((table, position) => (position === index ? { ...table, [key]: value } : table))
  )
const removeTable = (field, index) =>
  set(
    field.name,
    (values.value[field.name] || []).filter((_, position) => position !== index)
  )
</script>

<template>
  <div class="operation-form">
    <div class="form-mode"><el-switch v-model="advanced" active-text="高级 JSON 编辑" :disabled="disabled" /></div>
    <el-input v-if="advanced" :model-value="modelValue" type="textarea" :rows="8" :disabled="disabled" @update:model-value="editJson" />
    <el-alert v-if="error" :title="error" type="warning" :closable="false" />
    <el-form v-else-if="!advanced" label-position="top" :disabled="disabled">
      <el-form-item v-for="field in fields" :key="field.name" :label="field.label" :data-field-name="field.name" :data-field-type="field.type">
        <template #label
          >{{ field.label }} <small v-if="['files', 'paths', 'directories', 'list', 'tables', 'json'].includes(field.type) && Array.isArray(values[field.name])" class="item-count">{{ values[field.name].length }} 项</small></template
        >
        <div class="field-value">
          <el-input v-if="isReference(field)" :model-value="display(field)" readonly />
          <template v-else-if="['file', 'files', 'directory', 'directories', 'paths'].includes(field.type)">
            <el-input :model-value="Array.isArray(display(field)) ? display(field).join('\n') : display(field)" :type="['files', 'directories', 'paths'].includes(field.type) ? 'textarea' : 'text'" :rows="2" placeholder="选择文件或目录" @update:model-value="set(field.name, ['files', 'directories', 'paths'].includes(field.type) ? $event.split(/\r?\n/).filter(Boolean) : $event)" />
            <el-button :disabled="disabled" @click="choose(field)">选择</el-button>
            <el-button v-if="field.type === 'paths'" :disabled="disabled" @click="choose({ ...field, type: 'directories' })">添加目录</el-button>
          </template>
          <!-- This Element Plus version writes aria-disabled only at mount. Remount
               numeric controls on lock changes so their accessible state stays current. -->
          <el-input-number v-else-if="field.type === 'number'" :key="disabled ? 'locked-number' : 'editable-number'" :disabled="disabled" :model-value="Number(display(field) || 0)" @update:model-value="set(field.name, $event)" />
          <el-switch v-else-if="field.type === 'boolean'" :model-value="Boolean(display(field))" @update:model-value="set(field.name, $event)" />
          <el-select v-else-if="field.type === 'select'" :model-value="display(field)" @update:model-value="set(field.name, $event)"><el-option v-for="option in field.options" :key="typeof option === 'object' ? option.value : option" :label="typeof option === 'object' ? option.label : option" :value="typeof option === 'object' ? option.value : option" /></el-select>
          <el-input v-else-if="field.type === 'textarea'" :model-value="jsonText(field)" type="textarea" :rows="4" placeholder="输入待处理的内容" @update:model-value="set(field.name, $event)" />
          <el-input v-else-if="field.type === 'list'" :model-value="Array.isArray(display(field)) ? display(field).join('\n') : display(field)" type="textarea" :rows="2" placeholder="每行一个值" @update:model-value="set(field.name, $event.split(/\r?\n/).filter(Boolean))" />
          <MappingEditor v-else-if="['mapping', 'mapping-number'].includes(field.type)" :model-value="values[field.name] || {}" :disabled="disabled" :numeric="field.type === 'mapping-number'" :key-label="field.keyLabel" :value-label="field.valueLabel" @update:model-value="set(field.name, $event)" />
          <div v-else-if="field.type === 'tables'" class="table-parameters">
            <div v-for="(table, index) in values[field.name] || []" :key="index" class="table-parameter">
              <strong>{{ table.path }}</strong>
              <el-input :model-value="table.sheet" placeholder="工作表名称，留空使用第一张表" @update:model-value="updateTable(field, index, 'sheet', $event)" />
              <label>表头所在行 <el-input-number :key="disabled ? 'locked-header' : 'editable-header'" :disabled="disabled" :model-value="table.headerRow || 1" :min="1" @update:model-value="updateTable(field, index, 'headerRow', $event)" /></label>
              <MappingEditor :model-value="table.fieldMapping || {}" @update:model-value="updateTable(field, index, 'fieldMapping', $event)" />
              <el-button :disabled="disabled" text @click="removeTable(field, index)">移除表格</el-button>
            </div>
            <el-button :disabled="disabled" @click="choose(field)">添加表格文件</el-button>
          </div>
          <OperationForm v-else-if="field.type === 'object'" :model-value="JSON.stringify(values[field.name] || {})" :fields="field.fields || []" :disabled="disabled" @update:model-value="editObject(field, $event)" />
          <el-input v-else-if="field.type === 'json'" :model-value="jsonText(field)" type="textarea" :rows="4" :placeholder="field.jsonType === 'array' ? '填写 JSON 列表' : '填写 JSON 对象或列表'" @update:model-value="editObject(field, $event)" />
          <el-input v-else :model-value="typeof display(field) === 'object' ? JSON.stringify(display(field)) : display(field)" :type="field.type === 'password' ? 'password' : 'text'" :show-password="field.type === 'password'" @update:model-value="set(field.name, $event)" />
          <el-select v-if="previous.length" :model-value="typeof values[field.name] === 'string' && values[field.name].startsWith('{{steps.') ? values[field.name] : undefined" :disabled="disabled || !availableReferences[field.name]?.length" :placeholder="availableReferences[field.name]?.length ? '选择前序结果字段' : '无兼容的前序结果'" clearable filterable class="reference" @change="reference(field, $event)">
            <el-option v-for="option in availableReferences[field.name] || []" :key="option.value" :value="option.value" :label="option.label" :title="option.description" />
          </el-select>
        </div>
        <small v-if="jsonFieldError(field)" class="field-error">{{ jsonFieldError(field) }}</small>
      </el-form-item>
      <el-empty v-if="!fields.length" description="此操作无需填写参数，或可在高级编辑中配置兼容参数" :image-size="40" />
    </el-form>
  </div>
</template>
<style scoped>
.item-count {
  margin-left: 8px;
  color: var(--ppx-text-muted);
  font-weight: normal;
}
.field-error {
  color: var(--el-color-danger);
  overflow-wrap: anywhere;
}
.form-mode {
  text-align: right;
  margin-bottom: 8px;
}
.field-value {
  display: flex;
  width: 100%;
  gap: 8px;
  align-items: start;
}
.field-value > .el-input,
.field-value > .el-textarea {
  flex: 1;
  min-width: 0;
}
.reference {
  width: 180px;
  flex-shrink: 0;
}
.operation-form {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 8px;
}
.table-parameters {
  width: 100%;
  display: grid;
  gap: 12px;
}
.table-parameter {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 8px;
}
.table-parameter strong {
  overflow-wrap: anywhere;
}
</style>
