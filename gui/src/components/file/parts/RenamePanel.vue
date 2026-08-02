<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  directory: '',
  extensions: '',
  recursive: false,
  rule: 'sequence',
  prefix: 'FILE_',
  start: 1,
  padding: 3,
  search: '',
  pattern: '',
  replace: '',
  template: '{date}_{name}',
  presetTemplate: '',
  conflictPolicy: 'skip',
  dryRun: true,
  result: [],
  skipped: [],
  transactionId: '',
  showHelp: false
})
const previewReady = ref(false)

// 预置模板选项
const presetTemplates = [
  { label: '日期 + 序号', value: '{date}_{index:3}' },
  { label: '日期 + 原名', value: '{date}_{name}' },
  { label: '原名 + 备份后缀', value: '{name}_backup' },
  { label: '纯序号', value: 'IMG_{index:4}' },
  { label: '年月日时分秒', value: '{datetime}_{index}' },
  { label: '年/月/原名', value: '{year}{month}_{name}' }
]

// 变量说明
const templateVariables = [
  { var: '{name}', desc: '原文件名（不含扩展名）' },
  { var: '{ext}', desc: '扩展名（如 .jpg）' },
  { var: '{index}', desc: '序号（自动补零）' },
  { var: '{index:4}', desc: '指定4位序号' },
  { var: '{date}', desc: '日期 (YYYYMMDD)' },
  { var: '{time}', desc: '时间 (HHMMSS)' },
  { var: '{datetime}', desc: '日期时间' },
  { var: '{year}', desc: '年份' },
  { var: '{month}', desc: '月份' },
  { var: '{day}', desc: '日' }
]

// 正则表达式示例
const regexExamples = [
  { target: '删除空格', pattern: '\\s+', replace: '_', desc: '空格 → 下划线' },
  { target: '删除括号内容', pattern: '\\([^)]*\\)', replace: '', desc: '移除 (xxx)' },
  { target: '删除开头数字', pattern: '^\\d+[._-]?', replace: '', desc: '移除开头 01-' },
  { target: '仅保留字母数字', pattern: '[^a-zA-Z0-9]', replace: '_', desc: '其他字符变下划线' }
]

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const parseExtensions = (value) =>
  value
    .split(',')
    .map((item) => item.trim().replace('.', ''))
    .filter(Boolean)

const chooseDir = async (current = '') => {
  if (!ensurePyReady()) return null
  return callApiRaw('system_pySelectDirDialog', current)
}

const selectRenameDir = async () => {
  const dir = await chooseDir(state.directory)
  if (dir) state.directory = dir
}

const applyPreset = (value) => {
  if (value) {
    state.template = value
  }
}

const applyRegexExample = (example) => {
  state.pattern = example.pattern
  state.replace = example.replace
}

const buildRenameParams = () => {
  if (state.rule === 'sequence') {
    return {
      prefix: state.prefix,
      start: state.start,
      padding: state.padding
    }
  }
  if (state.rule === 'timestamp') {
    return {
      start: state.start,
      padding: state.padding
    }
  }
  if (state.rule === 'replace') {
    return {
      search: state.search,
      replace: state.replace
    }
  }
  if (state.rule === 'template') {
    return {
      template: state.template,
      start: state.start,
      padding: state.padding
    }
  }
  return {
    pattern: state.pattern,
    replace: state.replace
  }
}

watch(
  () => [state.directory, state.extensions, state.recursive, state.rule, state.prefix, state.start, state.padding, state.search, state.pattern, state.replace, state.template],
  () => {
    previewReady.value = false
  }
)

const runRename = async (dryRun = true) => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  if (!dryRun && !previewReady.value) {
    ElMessage.warning('请先预览重命名结果')
    return
  }
  if (!dryRun) {
    try {
      await ElMessageBox.confirm(`将重命名 ${state.result.length} 个文件；名称冲突的文件会自动跳过。`, '确认批量重命名', {
        confirmButtonText: '执行改名',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch {
      return
    }
  }
  state.dryRun = dryRun
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('file_batch_rename', {
      directory: state.directory,
      extensions: parseExtensions(state.extensions || ''),
      recursive: state.recursive,
      rule: state.rule,
      ruleParams: buildRenameParams(),
      conflictPolicy: state.conflictPolicy,
      dryRun: state.dryRun
    })
    if (ok) {
      state.result = res.renamed || []
      state.skipped = res.skipped || []
      state.transactionId = dryRun ? '' : res.transactionId || ''
      previewReady.value = dryRun && state.result.length > 0
      ElMessage.success(message || (dryRun ? '预览完成' : '重命名完成'))
    } else {
      ElMessage.error(message || '重命名失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '重命名失败')
  } finally {
    loading.value = false
  }
}

const undoRename = async () => {
  if (!state.transactionId || !state.directory) return
  try {
    await ElMessageBox.confirm('将按本次改名前的映射恢复文件名；若原名称已被占用，对应文件会跳过。', '撤销批量重命名', { confirmButtonText: '撤销改名', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_batch_rename_undo', { directory: state.directory, transactionId: state.transactionId })
    if (!ok) return ElMessage.error(message || '撤销失败')
    state.result = res.restored || []
    if (!(res.skipped || []).length) state.transactionId = ''
    previewReady.value = false
    ElMessage.success(message || '已撤销重命名')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>重命名规则</h4>
      <p>支持序号、时间戳、替换、正则或模板；必须先预览，且永不覆盖已有文件</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="目录">
        <div class="field-row">
          <el-input v-model="state.directory" placeholder="选择目录" readonly />
          <el-button @click="selectRenameDir">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="扩展名">
        <el-input v-model="state.extensions" placeholder="可选，如：jpg,png" />
      </el-form-item>
      <el-form-item label="选项">
        <el-checkbox v-model="state.recursive">包含子目录</el-checkbox>
      </el-form-item>
      <el-form-item label="冲突策略">
        <el-tag type="info" effect="plain">跳过已有文件（不覆盖）</el-tag>
      </el-form-item>
      <el-form-item label="规则">
        <el-radio-group v-model="state.rule">
          <el-radio-button label="sequence">序号</el-radio-button>
          <el-radio-button label="timestamp">时间戳</el-radio-button>
          <el-radio-button label="replace">替换</el-radio-button>
          <el-radio-button label="template">模板</el-radio-button>
          <el-radio-button label="regex">正则</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- 序号模式 -->
      <div v-if="state.rule === 'sequence'" class="field-row">
        <el-form-item label="前缀">
          <el-input v-model="state.prefix" placeholder="如 IMG_" />
        </el-form-item>
        <el-form-item label="起始值">
          <el-input-number v-model="state.start" :min="1" />
        </el-form-item>
        <el-form-item label="位数">
          <el-input-number v-model="state.padding" :min="1" :max="6" />
        </el-form-item>
      </div>

      <!-- 时间戳模式 -->
      <div v-else-if="state.rule === 'timestamp'" class="field-row">
        <el-form-item label="起始值">
          <el-input-number v-model="state.start" :min="1" />
        </el-form-item>
        <el-form-item label="位数">
          <el-input-number v-model="state.padding" :min="1" :max="6" />
        </el-form-item>
      </div>

      <!-- 模板模式 -->
      <div v-else-if="state.rule === 'template'" class="rename-template-section">
        <el-form-item label="预置模板">
          <el-select v-model="state.presetTemplate" placeholder="选择常用模板" style="width: 220px" clearable @change="applyPreset">
            <el-option v-for="item in presetTemplates" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="自定义模板">
          <div class="field-row">
            <el-input v-model="state.template" placeholder="如 {date}_{name}" style="flex: 1" />
            <el-popover placement="right" :width="320" trigger="hover">
              <template #reference>
                <el-button type="info" text>变量说明</el-button>
              </template>
              <div class="var-help">
                <p class="var-help-title">可用变量：</p>
                <el-table :data="templateVariables" size="small" border>
                  <el-table-column prop="var" label="变量" width="100" />
                  <el-table-column prop="desc" label="说明" />
                </el-table>
                <p class="var-help-example">示例：{date}_{name} → 20260104_photo.jpg</p>
              </div>
            </el-popover>
          </div>
        </el-form-item>
        <el-form-item label="起始序号">
          <el-input-number v-model="state.start" :min="1" />
        </el-form-item>
      </div>

      <!-- 正则模式 -->
      <div v-else-if="state.rule === 'regex'" class="rename-regex-section">
        <el-form-item label="正则表达式">
          <div class="field-row">
            <el-input v-model="state.pattern" placeholder="如 \s+ 匹配空格" style="flex: 1" />
            <el-popover placement="right" :width="400" trigger="hover">
              <template #reference>
                <el-button type="info" text>常用示例</el-button>
              </template>
              <div class="regex-help">
                <p class="regex-help-title">常用正则表达式示例（点击可应用）：</p>
                <el-table :data="regexExamples" size="small" border>
                  <el-table-column prop="target" label="目标" width="100" />
                  <el-table-column prop="pattern" label="匹配" width="120" />
                  <el-table-column prop="desc" label="效果" />
                  <el-table-column label="操作" width="70">
                    <template #default="scope">
                      <el-button size="small" text type="primary" @click="applyRegexExample(scope.row)"> 应用 </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-popover>
          </div>
        </el-form-item>
        <el-form-item label="替换为">
          <el-input v-model="state.replace" placeholder="替换内容，留空表示删除匹配部分" />
        </el-form-item>
      </div>

      <!-- 简单替换模式 -->
      <div v-else-if="state.rule === 'replace'" class="field-row">
        <el-form-item label="查找文本">
          <el-input v-model="state.search" placeholder="要替换的文本" />
        </el-form-item>
        <el-form-item label="替换为">
          <el-input v-model="state.replace" placeholder="替换内容" />
        </el-form-item>
      </div>

      <el-form-item>
        <el-button type="primary" plain :loading="loading" @click="runRename(true)">1. 预览结果</el-button>
        <el-button type="primary" :loading="loading" :disabled="!previewReady" @click="runRename(false)">2. 执行改名</el-button>
        <el-button v-if="state.transactionId" type="warning" plain :loading="loading" @click="undoRename">撤销本次改名</el-button>
      </el-form-item>
    </el-form>

    <!-- 使用说明 -->
    <el-collapse v-model="state.showHelp" class="rename-help-collapse">
      <el-collapse-item title="📖 使用说明" name="help">
        <div class="rename-help-content">
          <h5>规则说明</h5>
          <ul>
            <li><strong>序号</strong>：按序号重命名，如 FILE_001、FILE_002</li>
            <li><strong>时间戳</strong>：使用当前时间命名</li>
            <li><strong>替换</strong>：简单文本替换，无需正则知识</li>
            <li><strong>模板</strong>：使用变量组合自定义格式，推荐新手使用</li>
            <li><strong>正则</strong>：高级模式，支持正则表达式匹配</li>
          </ul>
          <h5>操作建议</h5>
          <ul>
            <li>首次操作请先开启「仅预览」模式，确认无误后再执行</li>
            <li>不熟悉正则？试试「模板」模式，选择预置模板或使用变量</li>
          </ul>
        </div>
      </el-collapse-item>
    </el-collapse>

    <el-table v-if="state.result.length" :data="state.result" border size="small" style="margin-top: 12px">
      <el-table-column label="原文件" prop="from" show-overflow-tooltip />
      <el-table-column label="新文件" prop="to" show-overflow-tooltip />
    </el-table>
  </section>
</template>

<style scoped>
/* 重命名模块样式 */
.rename-template-section,
.rename-regex-section {
  margin-bottom: 12px;
}

.var-help,
.regex-help {
  font-size: 13px;
}

.var-help-title,
.regex-help-title {
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--ppx-text-primary);
}

.var-help-example {
  margin: 8px 0 0;
  padding: 6px 10px;
  background: var(--ppx-glass-bg);
  border-radius: var(--ppx-radius-sm);
  color: var(--ppx-text-secondary);
  font-size: 12px;
}

.rename-help-collapse {
  margin-top: 16px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  overflow: hidden;
}

.rename-help-content {
  font-size: 13px;
  color: var(--ppx-text-secondary);
}

.rename-help-content h5 {
  font-size: 14px;
  margin: 0 0 8px;
  color: var(--ppx-text-primary);
}

.rename-help-content h5:not(:first-child) {
  margin-top: 16px;
}

.rename-help-content ul {
  margin: 0;
  padding-left: 18px;
}

.rename-help-content li {
  margin-bottom: 4px;
}

.rename-help-content strong {
  color: var(--ppx-neon-blue);
}
</style>
