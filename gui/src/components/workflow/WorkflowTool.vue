<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi, callApiRaw } from '@/utils/pyapi'

const props = defineProps({ initialTab: { type: String, default: '' } })

const activeTab = ref(props.initialTab || 'workflows')
const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const workflows = ref([])
const templates = ref([])
const methods = ref([])
const schedules = ref([])
const watches = ref([])
const runs = ref([])
const selectedId = ref('')
const runInput = ref('{}')
const runQuery = ref('')
const runStatus = ref('all')
const runTrigger = ref('all')
const triggerActionId = ref('')

const editor = reactive({ id: '', name: '', description: '', enabled: true, steps: [] })
const scheduleForm = reactive({ workflowId: '', name: '', intervalMinutes: 60, input: '{}' })
const watchForm = reactive({ workflowId: '', name: '', path: '', extensions: '', recursive: false, debounceSeconds: 3, input: '{}' })

const workflowOptions = computed(() => workflows.value.map((item) => ({ value: item.id, label: item.name })))
const triggerRows = computed(() => [...schedules.value.map((item) => ({ ...item, kind: 'schedule' })), ...watches.value.map((item) => ({ ...item, kind: 'watch' }))])
const filteredRuns = computed(() => {
  const keyword = runQuery.value.trim().toLowerCase()
  return runs.value.filter((run) => {
    if (runStatus.value !== 'all' && run.status !== runStatus.value) return false
    if (runTrigger.value !== 'all') {
      const trigger = String(run.trigger || '')
      if (runTrigger.value === 'manual' && trigger !== 'manual') return false
      if (runTrigger.value !== 'manual' && !trigger.includes(runTrigger.value)) return false
    }
    if (!keyword) return true
    return `${run.workflowName || ''} ${run.workflowId || ''} ${run.trigger || ''}`.toLowerCase().includes(keyword)
  })
})

const formatTime = (value) => {
  if (!value) return '—'
  return new Date(Number(value) * 1000).toLocaleString()
}

const parseObject = (text, label) => {
  const value = JSON.parse(text || '{}')
  if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error(`${label}必须是 JSON 对象`)
  return value
}

const resetEditor = () => {
  selectedId.value = ''
  Object.assign(editor, {
    id: '',
    name: '新工作流',
    description: '',
    enabled: true,
    steps: [{ id: 'step-1', name: '第一个步骤', method: methods.value[0] || 'image_batch_compress', argsText: '{}', onError: 'stop', retryCount: 0, retryDelaySeconds: 1 }]
  })
  runInput.value = '{}'
}

const loadEditor = (workflow) => {
  selectedId.value = workflow.id
  Object.assign(editor, {
    id: workflow.id,
    name: workflow.name || '',
    description: workflow.description || '',
    enabled: workflow.enabled !== false,
    steps: (workflow.steps || []).map((step) => ({
      ...step,
      retryCount: Number(step.retryCount || 0),
      retryDelaySeconds: Number(step.retryDelaySeconds || 0),
      argsText: JSON.stringify(step.args || {}, null, 2)
    }))
  })
  runInput.value = JSON.stringify(workflow.inputExample || {}, null, 2)
}

const refresh = async (keepSelection = true) => {
  loading.value = true
  try {
    const [listResponse, templateResponse, methodResponse] = await Promise.all([callApi('workflow_list'), callApi('workflow_templates'), callApi('workflow_methods')])
    if (!listResponse.ok) throw new Error(listResponse.message || '读取工作流失败')
    workflows.value = listResponse.data.workflows || []
    schedules.value = listResponse.data.schedules || []
    watches.value = listResponse.data.watches || []
    runs.value = listResponse.data.runs || []
    templates.value = templateResponse.ok ? templateResponse.data.templates || [] : []
    methods.value = methodResponse.ok ? methodResponse.data.methods || [] : []
    if (keepSelection && selectedId.value) {
      const selected = workflows.value.find((item) => item.id === selectedId.value)
      if (selected) loadEditor(selected)
      else resetEditor()
    } else if (workflows.value.length) {
      loadEditor(workflows.value[0])
    } else {
      resetEditor()
    }
    if (!scheduleForm.workflowId && workflows.value.length) scheduleForm.workflowId = workflows.value[0].id
    if (!watchForm.workflowId && workflows.value.length) watchForm.workflowId = workflows.value[0].id
  } catch (error) {
    ElMessage.error(error?.message || '加载自动化中心失败')
  } finally {
    loading.value = false
  }
}

const useTemplate = async (template) => {
  const response = await callApi('workflow_create_from_template', { templateId: template.id })
  if (!response.ok) return ElMessage.error(response.message || '创建失败')
  ElMessage.success('已从模板创建，可继续调整参数')
  selectedId.value = response.data.workflow.id
  await refresh(true)
}

const addStep = () => {
  const index = editor.steps.length + 1
  editor.steps.push({ id: `step-${index}`, name: `步骤 ${index}`, method: methods.value[0] || '', argsText: '{}', onError: 'stop', retryCount: 0, retryDelaySeconds: 1 })
}

const moveStep = (index, offset) => {
  const next = index + offset
  if (next < 0 || next >= editor.steps.length) return
  const [item] = editor.steps.splice(index, 1)
  editor.steps.splice(next, 0, item)
}

const saveWorkflow = async () => {
  if (!editor.name.trim()) return ElMessage.warning('请填写工作流名称')
  if (!editor.steps.length) return ElMessage.warning('至少添加一个步骤')
  let steps
  try {
    steps = editor.steps.map((step, index) => ({
      id: step.id || `step-${index + 1}`,
      name: step.name || step.method,
      method: step.method,
      args: parseObject(step.argsText, `步骤 ${index + 1} 参数`),
      onError: step.onError,
      retryCount: Number(step.retryCount || 0),
      retryDelaySeconds: Number(step.retryDelaySeconds || 0)
    }))
  } catch (error) {
    return ElMessage.error(error.message)
  }
  saving.value = true
  try {
    const response = await callApi('workflow_save', {
      id: editor.id,
      name: editor.name,
      description: editor.description,
      enabled: editor.enabled,
      steps,
      inputExample: parseObject(runInput.value, '运行输入')
    })
    if (!response.ok) return ElMessage.error(response.message || '保存失败')
    selectedId.value = response.data.workflow.id
    ElMessage.success('工作流已保存')
    await refresh(true)
  } catch (error) {
    ElMessage.error(error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const removeWorkflow = async () => {
  if (!editor.id) return
  await ElMessageBox.confirm('关联的定时任务和目录监听也会一并删除，是否继续？', '删除工作流', { type: 'warning' })
  const response = await callApi('workflow_delete', { id: editor.id })
  if (!response.ok) return ElMessage.error(response.message || '删除失败')
  ElMessage.success('已删除')
  await refresh(false)
}

const runWorkflow = async () => {
  if (!editor.id) {
    ElMessage.warning('请先保存工作流')
    return
  }
  let input
  try {
    input = parseObject(runInput.value, '运行输入')
  } catch (error) {
    return ElMessage.error(error.message)
  }
  running.value = true
  try {
    const response = await callApi('workflow_run', { id: editor.id, input })
    if (response.ok) ElMessage.success('工作流执行完成')
    else ElMessage.error(response.message || '工作流执行失败')
    await refresh(true)
    activeTab.value = 'history'
  } catch (error) {
    ElMessage.error(error?.message || '执行失败')
  } finally {
    running.value = false
  }
}

const saveSchedule = async () => {
  if (!scheduleForm.workflowId) return ElMessage.warning('请先选择工作流')
  let input
  try {
    input = parseObject(scheduleForm.input, '定时输入')
  } catch (error) {
    return ElMessage.error(error.message)
  }
  const response = await callApi('workflow_schedule_save', { ...scheduleForm, input })
  if (!response.ok) return ElMessage.error(response.message || '保存失败')
  ElMessage.success('定时任务已启用')
  await refresh(true)
}

const selectWatchFolder = async () => {
  try {
    const path = await callApiRaw('system_pySelectDirDialog', watchForm.path || '')
    if (path) watchForm.path = path
  } catch (error) {
    ElMessage.error(error?.message || '选择目录失败')
  }
}

const saveWatch = async () => {
  if (!watchForm.workflowId || !watchForm.path) return ElMessage.warning('请选择工作流和监听目录')
  let input
  try {
    input = parseObject(watchForm.input, '监听输入')
  } catch (error) {
    return ElMessage.error(error.message)
  }
  const response = await callApi('workflow_watch_save', { ...watchForm, input })
  if (!response.ok) return ElMessage.error(response.message || '保存失败')
  ElMessage.success('目录监听已启用；已有文件不会被重复处理')
  await refresh(true)
}

const removeTrigger = async (kind, id) => {
  const method = kind === 'schedule' ? 'workflow_schedule_delete' : 'workflow_watch_delete'
  const response = await callApi(method, { id })
  if (!response.ok) return ElMessage.error(response.message || '删除失败')
  ElMessage.success('触发器已删除')
  await refresh(true)
}

const toggleTrigger = async (trigger, enabled) => {
  triggerActionId.value = trigger.id
  try {
    const response = await callApi('workflow_trigger_set_enabled', { kind: trigger.kind, id: trigger.id, enabled })
    if (!response.ok) {
      await refresh(true)
      return ElMessage.error(response.message || '更新触发器失败')
    }
    ElMessage.success(response.message)
    await refresh(true)
  } catch (error) {
    ElMessage.error(error?.message || '更新触发器失败')
    await refresh(true)
  } finally {
    triggerActionId.value = ''
  }
}

const runTriggerNow = async (trigger) => {
  triggerActionId.value = trigger.id
  try {
    const response = await callApi('workflow_trigger_run_now', { kind: trigger.kind, id: trigger.id })
    if (!response.ok) return ElMessage.error(response.message || '提交运行失败')
    ElMessage.success(response.message || '已提交运行')
    await refresh(true)
  } catch (error) {
    ElMessage.error(error?.message || '提交运行失败')
  } finally {
    triggerActionId.value = ''
  }
}

watch(
  () => props.initialTab,
  (value) => {
    if (value) activeTab.value = value
  }
)

onMounted(() => refresh(false))
</script>

<template>
  <div v-loading="loading" class="workflow-tool">
    <el-tabs v-model="activeTab" class="workflow-tabs">
      <el-tab-pane label="工作流" name="workflows">
        <div class="workflow-grid">
          <aside class="workflow-list">
            <div class="section-head">
              <strong>我的工作流</strong>
              <el-button size="small" @click="resetEditor">新建</el-button>
            </div>
            <button v-for="item in workflows" :key="item.id" class="workflow-list-item" :class="{ active: item.id === selectedId }" type="button" @click="loadEditor(item)">
              <span>{{ item.name }}</span>
              <small>{{ item.steps?.length || 0 }} 步 · {{ item.enabled === false ? '停用' : '启用' }}</small>
            </button>
            <el-empty v-if="!workflows.length" :image-size="54" description="还没有工作流" />

            <div class="template-title">内置模板</div>
            <div v-for="template in templates" :key="template.id" class="template-card">
              <strong>{{ template.name }}</strong>
              <p>{{ template.description }}</p>
              <el-button size="small" plain @click="useTemplate(template)">使用模板</el-button>
            </div>
          </aside>

          <section class="workflow-editor">
            <div class="editor-top">
              <div>
                <h3>{{ editor.id ? '编辑工作流' : '新建工作流' }}</h3>
                <p>
                  步骤按顺序执行；使用 <code v-pre>{{ input.filePath }}</code> 或 <code v-pre>{{steps.step-1.output}}</code> 引用数据。
                </p>
              </div>
              <el-switch v-model="editor.enabled" active-text="启用" />
            </div>
            <el-form label-position="top">
              <div class="two-columns">
                <el-form-item label="名称">
                  <el-input v-model="editor.name" maxlength="120" />
                </el-form-item>
                <el-form-item label="说明">
                  <el-input v-model="editor.description" maxlength="500" />
                </el-form-item>
              </div>

              <div class="step-stack">
                <div v-for="(step, index) in editor.steps" :key="`${step.id}-${index}`" class="step-card">
                  <div class="step-number">{{ index + 1 }}</div>
                  <div class="step-body">
                    <div class="step-row">
                      <el-input v-model="step.id" placeholder="步骤 ID" />
                      <el-input v-model="step.name" placeholder="步骤名称" />
                      <el-select v-model="step.method" filterable placeholder="选择能力">
                        <el-option v-for="method in methods" :key="method" :label="method" :value="method" />
                      </el-select>
                      <el-select v-model="step.onError" class="error-select">
                        <el-option label="失败即停止" value="stop" />
                        <el-option label="失败后继续" value="continue" />
                      </el-select>
                    </div>
                    <el-input v-model="step.argsText" type="textarea" :rows="5" resize="vertical" placeholder="步骤参数 JSON" />
                    <div class="step-policy">
                      <span>失败自动重试</span>
                      <el-input-number v-model="step.retryCount" :min="0" :max="5" size="small" />
                      <span>次，每次等待</span>
                      <el-input-number v-model="step.retryDelaySeconds" :min="0" :max="300" size="small" />
                      <span>秒</span>
                    </div>
                  </div>
                  <div class="step-actions">
                    <el-button text :disabled="index === 0" @click="moveStep(index, -1)">上移</el-button>
                    <el-button text :disabled="index === editor.steps.length - 1" @click="moveStep(index, 1)">下移</el-button>
                    <el-button text type="danger" @click="editor.steps.splice(index, 1)">删除</el-button>
                  </div>
                </div>
              </div>
              <el-button plain class="add-step" @click="addStep">+ 添加步骤</el-button>

              <el-form-item label="运行输入 JSON" class="run-input">
                <el-input v-model="runInput" type="textarea" :rows="5" resize="vertical" />
              </el-form-item>
              <div class="editor-actions">
                <el-button v-if="editor.id" type="danger" plain @click="removeWorkflow">删除</el-button>
                <span class="action-spacer" />
                <el-button :loading="saving" @click="saveWorkflow">保存</el-button>
                <el-button type="primary" :loading="running" :disabled="!editor.id" @click="runWorkflow">立即运行</el-button>
              </div>
            </el-form>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="触发器" name="triggers">
        <div class="trigger-grid">
          <el-card shadow="never">
            <template #header><strong>周期运行</strong></template>
            <el-form label-position="top">
              <el-form-item label="工作流">
                <el-select v-model="scheduleForm.workflowId" filterable><el-option v-for="item in workflowOptions" :key="item.value" v-bind="item" /></el-select>
              </el-form-item>
              <div class="two-columns">
                <el-form-item label="名称"><el-input v-model="scheduleForm.name" placeholder="例如：每小时整理" /></el-form-item>
                <el-form-item label="间隔（分钟）"><el-input-number v-model="scheduleForm.intervalMinutes" :min="1" :max="525600" /></el-form-item>
              </div>
              <el-form-item label="输入 JSON"><el-input v-model="scheduleForm.input" type="textarea" :rows="4" /></el-form-item>
              <el-button type="primary" @click="saveSchedule">创建定时任务</el-button>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header><strong>目录监听</strong></template>
            <el-form label-position="top">
              <el-form-item label="工作流">
                <el-select v-model="watchForm.workflowId" filterable><el-option v-for="item in workflowOptions" :key="item.value" v-bind="item" /></el-select>
              </el-form-item>
              <el-form-item label="监听目录">
                <el-input v-model="watchForm.path"
                  ><template #append><el-button @click="selectWatchFolder">选择</el-button></template></el-input
                >
              </el-form-item>
              <div class="two-columns">
                <el-form-item label="扩展名（逗号分隔）"><el-input v-model="watchForm.extensions" placeholder="pdf,png,jpg" /></el-form-item>
                <el-form-item label="稳定等待（秒）"><el-input-number v-model="watchForm.debounceSeconds" :min="1" :max="3600" /></el-form-item>
              </div>
              <el-form-item><el-checkbox v-model="watchForm.recursive">包含子目录</el-checkbox></el-form-item>
              <el-form-item label="附加输入 JSON"><el-input v-model="watchForm.input" type="textarea" :rows="3" /></el-form-item>
              <el-button type="primary" @click="saveWatch">创建目录监听</el-button>
            </el-form>
          </el-card>
        </div>

        <div class="trigger-list">
          <h3>触发器</h3>
          <el-table :data="triggerRows" empty-text="暂无触发器">
            <el-table-column label="类型" width="100"
              ><template #default="scope">{{ scope.row.kind === 'schedule' ? '周期' : '目录' }}</template></el-table-column
            >
            <el-table-column prop="name" label="名称" min-width="150" />
            <el-table-column label="规则" min-width="240"
              ><template #default="scope">{{ scope.row.kind === 'schedule' ? `每 ${scope.row.intervalMinutes} 分钟` : scope.row.path }}</template></el-table-column
            >
            <el-table-column label="最近触发" width="180"
              ><template #default="scope">{{ formatTime(scope.row.lastRunAt || scope.row.lastEventAt) }}</template></el-table-column
            >
            <el-table-column label="状态" width="100"
              ><template #default="scope"><el-switch :model-value="scope.row.enabled !== false" :loading="triggerActionId === scope.row.id" @change="toggleTrigger(scope.row, $event)" /></template
            ></el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="scope">
                <el-button text type="primary" :loading="triggerActionId === scope.row.id" @click="runTriggerNow(scope.row)">立即运行</el-button>
                <el-button text type="danger" @click="removeTrigger(scope.row.kind, scope.row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="运行记录" name="history">
        <div class="history-head">
          <div>
            <h3>自动化运行记录</h3>
            <p>每一步的结果都会保存在本机，最多保留 80 次。</p>
          </div>
          <el-button @click="refresh(true)">刷新</el-button>
        </div>
        <div class="history-filters">
          <el-input v-model="runQuery" clearable placeholder="搜索工作流名称或触发来源" />
          <el-select v-model="runStatus">
            <el-option label="全部状态" value="all" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="运行中" value="running" />
          </el-select>
          <el-select v-model="runTrigger">
            <el-option label="全部来源" value="all" />
            <el-option label="手动运行" value="manual" />
            <el-option label="周期任务" value="schedule" />
            <el-option label="目录监听" value="watch" />
          </el-select>
        </div>
        <el-collapse class="run-list">
          <el-collapse-item v-for="run in filteredRuns" :key="run.id" :name="run.id">
            <template #title>
              <div class="run-title">
                <el-tag :type="run.status === 'success' ? 'success' : run.status === 'running' ? 'warning' : 'danger'" size="small">{{ run.status }}</el-tag>
                <strong>{{ run.workflowName || run.workflowId }}</strong>
                <span>{{ run.trigger }}</span>
                <time>{{ formatTime(run.startedAt) }}</time>
              </div>
            </template>
            <el-timeline>
              <el-timeline-item v-for="step in run.steps || []" :key="step.id" :type="step.status === 'success' ? 'success' : 'danger'" :timestamp="formatTime(step.endedAt)">
                <strong>{{ step.name }}</strong> · <code>{{ step.method }}</code>
                <p>{{ step.message || (step.status === 'success' ? '完成' : '失败') }}</p>
                <small v-if="step.attemptCount > 1">共执行 {{ step.attemptCount }} 次（自动重试 {{ step.attemptCount - 1 }} 次）</small>
                <ul v-if="step.attempts?.length > 1" class="attempt-list">
                  <li v-for="attempt in step.attempts" :key="attempt.attempt">
                    <el-tag :type="attempt.status === 'success' ? 'success' : 'danger'" size="small" effect="plain">第 {{ attempt.attempt }} 次</el-tag>
                    <span>{{ attempt.message || (attempt.status === 'success' ? '完成' : '失败') }}</span>
                  </li>
                </ul>
              </el-timeline-item>
            </el-timeline>
          </el-collapse-item>
        </el-collapse>
        <el-empty v-if="!filteredRuns.length" :description="runs.length ? '没有符合筛选条件的运行记录' : '还没有运行记录'" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.workflow-tool {
  height: 100%;
  overflow: auto;
  padding: 18px 22px 30px;
  box-sizing: border-box;
}
.workflow-tabs {
  min-height: 100%;
}
.workflow-grid {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  gap: 18px;
}
.workflow-list,
.workflow-editor,
.trigger-list {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 14px;
  background: var(--ppx-bg-elevated);
}
.workflow-list {
  padding: 14px;
  align-self: start;
}
.section-head,
.editor-top,
.editor-actions,
.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.workflow-list-item {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  color: var(--ppx-text-primary);
  padding: 10px;
  margin-top: 6px;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.workflow-list-item:hover,
.workflow-list-item.active {
  background: var(--ppx-bg-soft);
  border-color: var(--accent);
}
.workflow-list-item small,
.template-card p,
.editor-top p,
.history-head p {
  color: var(--ppx-text-muted);
  margin: 0;
}
.template-title {
  margin: 20px 0 8px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}
.template-card {
  border-top: 1px solid var(--ppx-glass-border);
  padding: 12px 4px;
}
.template-card p {
  font-size: 12px;
  line-height: 1.6;
  margin: 5px 0 9px;
}
.workflow-editor {
  padding: 18px;
  min-width: 0;
}
.editor-top {
  margin-bottom: 16px;
}
h3 {
  margin: 0 0 5px;
  font-size: 16px;
}
.editor-top p,
.history-head p {
  font-size: 12px;
}
.two-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.step-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.step-card {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 58px;
  gap: 10px;
  padding: 14px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  background: var(--ppx-bg-soft);
}
.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: white;
  background: var(--accent);
  font-weight: 700;
}
.step-body {
  min-width: 0;
}
.step-row {
  display: grid;
  grid-template-columns: 110px 1fr minmax(180px, 1.2fr) 116px;
  gap: 8px;
  margin-bottom: 9px;
}
.step-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.step-policy {
  margin-top: 9px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.step-policy .el-input-number {
  width: 96px;
}
.error-select {
  width: 116px;
}
.add-step {
  width: 100%;
  margin: 12px 0 16px;
}
.run-input {
  margin-top: 4px;
}
.action-spacer {
  flex: 1;
}
.trigger-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.trigger-list {
  margin-top: 18px;
  padding: 18px;
}
.history-head {
  margin-bottom: 14px;
}
.history-filters {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 150px 150px;
  gap: 10px;
  margin-bottom: 14px;
}
.run-list {
  border-top: 1px solid var(--ppx-glass-border);
}
.run-title {
  width: 100%;
  display: grid;
  grid-template-columns: 72px minmax(140px, 1fr) 160px 190px;
  gap: 10px;
  align-items: center;
  padding-right: 16px;
}
.run-title span,
.run-title time {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.attempt-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}
.attempt-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--accent);
}
@media (max-width: 1050px) {
  .workflow-grid,
  .trigger-grid {
    grid-template-columns: 1fr;
  }
  .step-row {
    grid-template-columns: 1fr 1fr;
  }
  .history-filters {
    grid-template-columns: 1fr;
  }
}
</style>
