<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApiRaw } from '../../utils/pyapi'
import MappingEditor from './MappingEditor.vue'
const props = defineProps({ modelValue: { type: String, default: '{}' }, fields: { type: Array, default: () => [] }, previous: { type: Array, default: () => [] } })
const emit = defineEmits(['update:modelValue'])
const advanced = ref(false)
const error = ref('')
const values = computed(() => {
  try {
    return JSON.parse(props.modelValue || '{}')
  } catch {
    return {}
  }
})
const set = (name, value) => emit('update:modelValue', JSON.stringify({ ...values.value, [name]: value }, null, 2))
const isReference = (field) => typeof values.value[field.name] === 'string' && values.value[field.name].startsWith('{{')
const display = (field) => values.value[field.name] ?? field.default ?? (field.type === 'boolean' ? false : '')
const choose = async (field) => {
  try {
    if (['directory', 'directories'].includes(field.type)) {
      const directory = await callApiRaw('system_pySelectDirDialog', '')
      if (directory) set(field.name, field.type === 'directories' ? [...new Set([...(values.value[field.name] || []), directory])] : directory)
    } else {
      const files = await callApiRaw('system_pyCreateFileDialog', ['全部文件 (*.*)'])
      if (files?.length) set(field.name, field.type === 'tables' ? [...(values.value[field.name] || []), ...files.map((file) => ({ path: file.path, sheet: '', headerRow: 1, fieldMapping: {} }))] : ['files', 'paths'].includes(field.type) ? files.map((file) => file.path) : files[0].path)
    }
  } catch (err) {
    ElMessage.error(err.message)
  }
}
const reference = (field, stepId) => {
  if (!stepId) return set(field.name, field.default ?? '')
  const key = field.type === 'files' ? 'outputPaths' : field.type === 'file' ? 'outputAssets.0.path' : field.type === 'directory' ? 'outputDir' : 'output'
  set(field.name, '{{steps.' + stepId + '.' + key + '}}')
}
const editJson = (value) => {
  emit('update:modelValue', value)
  try {
    const parsed = JSON.parse(value)
    error.value = parsed && !Array.isArray(parsed) && typeof parsed === 'object' ? '' : '参数必须是对象'
  } catch {
    error.value = 'JSON 尚未完整，请修正后保存'
  }
}
const editObject = (field, value) => {
  try {
    set(field.name, JSON.parse(value || '{}'))
    error.value = ''
  } catch {
    ElMessage.warning(`${field.label}的 JSON 格式不完整，未保存该值`)
  }
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
    <div class="form-mode"><el-switch v-model="advanced" active-text="高级 JSON 编辑" /></div>
    <el-input v-if="advanced" :model-value="modelValue" type="textarea" :rows="8" @update:model-value="editJson" />
    <el-alert v-if="error" :title="error" type="warning" :closable="false" />
    <el-form v-else-if="!advanced" label-position="top">
      <el-form-item v-for="field in fields" :key="field.name" :label="field.label">
        <div class="field-value">
          <el-input v-if="isReference(field)" :model-value="display(field)" readonly />
          <template v-else-if="['file', 'files', 'directory', 'directories', 'paths'].includes(field.type)">
            <el-input :model-value="Array.isArray(display(field)) ? display(field).join('\n') : display(field)" :type="['files', 'directories', 'paths'].includes(field.type) ? 'textarea' : 'text'" :rows="2" placeholder="选择文件或目录" @update:model-value="set(field.name, ['files', 'directories', 'paths'].includes(field.type) ? $event.split(/\r?\n/).filter(Boolean) : $event)" />
            <el-button @click="choose(field)">选择</el-button>
            <el-button v-if="field.type === 'paths'" @click="choose({ ...field, type: 'directories' })">添加目录</el-button>
          </template>
          <el-input-number v-else-if="field.type === 'number'" :model-value="Number(display(field) || 0)" @update:model-value="set(field.name, $event)" />
          <el-switch v-else-if="field.type === 'boolean'" :model-value="Boolean(display(field))" @update:model-value="set(field.name, $event)" />
          <el-select v-else-if="field.type === 'select'" :model-value="display(field)" @update:model-value="set(field.name, $event)"><el-option v-for="option in field.options" :key="typeof option === 'object' ? option.value : option" :label="typeof option === 'object' ? option.label : option" :value="typeof option === 'object' ? option.value : option" /></el-select>
          <el-input v-else-if="field.type === 'list'" :model-value="Array.isArray(display(field)) ? display(field).join('\n') : display(field)" type="textarea" :rows="2" placeholder="每行一个值" @update:model-value="set(field.name, $event.split(/\r?\n/).filter(Boolean))" />
          <MappingEditor v-else-if="['mapping', 'mapping-number'].includes(field.type)" :model-value="values[field.name] || {}" :numeric="field.type === 'mapping-number'" :key-label="field.keyLabel" :value-label="field.valueLabel" @update:model-value="set(field.name, $event)" />
          <div v-else-if="field.type === 'tables'" class="table-parameters">
            <div v-for="(table, index) in values[field.name] || []" :key="index" class="table-parameter">
              <strong>{{ table.path }}</strong>
              <el-input :model-value="table.sheet" placeholder="工作表名称，留空使用第一张表" @update:model-value="updateTable(field, index, 'sheet', $event)" />
              <label>表头所在行 <el-input-number :model-value="table.headerRow || 1" :min="1" @update:model-value="updateTable(field, index, 'headerRow', $event)" /></label>
              <MappingEditor :model-value="table.fieldMapping || {}" @update:model-value="updateTable(field, index, 'fieldMapping', $event)" />
              <el-button text @click="removeTable(field, index)">移除表格</el-button>
            </div>
            <el-button @click="choose(field)">添加表格文件</el-button>
          </div>
          <OperationForm v-else-if="field.type === 'object'" :model-value="JSON.stringify(values[field.name] || {})" :fields="field.fields || []" @update:model-value="editObject(field, $event)" />
          <el-input v-else-if="field.type === 'json'" :model-value="JSON.stringify(display(field) || {}, null, 2)" type="textarea" :rows="3" placeholder="可选高级参数" @change="editObject(field, $event)" />
          <el-input v-else :model-value="typeof display(field) === 'object' ? JSON.stringify(display(field)) : display(field)" :type="field.type === 'password' ? 'password' : 'text'" :show-password="field.type === 'password'" @update:model-value="set(field.name, $event)" />
          <el-select v-if="previous.length" placeholder="引用前一步结果" clearable class="reference" @change="reference(field, $event)"><el-option v-for="step in previous" :key="step.id" :value="step.id" :label="step.name || step.id" /></el-select>
        </div>
      </el-form-item>
      <el-empty v-if="!fields.length" description="此操作无需填写参数，或可在高级编辑中配置兼容参数" :image-size="40" />
    </el-form>
  </div>
</template>
<style scoped>
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
}
.reference {
  width: 180px;
  flex-shrink: 0;
}
.operation-form {
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
