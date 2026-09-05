<script setup>
import { useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

let replaceRuleSeed = 1

const state = useDraft('text/parts/ReplacePanel/state', {
  content: '',
  rules: [
    {
      id: replaceRuleSeed,
      search: '',
      replace: '',
      regex: false,
      caseSensitive: true,
      enabled: true,
      limit: 0
    }
  ],
  result: '',
  report: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const addReplaceRule = () => {
  replaceRuleSeed += 1
  state.rules.push({
    id: replaceRuleSeed,
    search: '',
    replace: '',
    regex: false,
    caseSensitive: true,
    enabled: true,
    limit: 0
  })
}

const removeReplaceRule = (index) => {
  state.rules.splice(index, 1)
  if (!state.rules.length) {
    addReplaceRule()
  }
}

const runReplace = async () => {
  if (!ensurePyReady()) return
  const rules = state.rules.filter((rule) => rule.enabled && rule.search?.trim())
  if (!rules.length) {
    ElMessage.warning('请至少启用一条规则')
    return
  }
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('text_batch_replace', {
      content: state.content,
      rules
    })
    if (ok) {
      state.result = res.result || ''
      state.report = res.report || []
      ElMessage.success(message || '处理完成')
    } else {
      ElMessage.error(message || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>批量替换规则</h4>
      <p>支持文本/正则模式、区分大小写、替换次数限制，附执行报告</p>
    </header>
    <div class="rule-toolbar">
      <span>替换规则</span>
      <el-button size="small" type="primary" text @click="addReplaceRule">新增规则</el-button>
    </div>
    <div class="rule-list">
      <div v-for="(rule, index) in state.rules" :key="rule.id" class="rule-row">
        <div class="rule-row-line">
          <el-checkbox v-model="rule.enabled">启用</el-checkbox>
          <el-checkbox v-model="rule.regex">正则</el-checkbox>
          <el-checkbox v-model="rule.caseSensitive" :disabled="rule.regex">区分大小写</el-checkbox>
          <el-input-number v-model="rule.limit" :min="0" :max="999" :step="1" size="small" style="width: 120px" />
          <el-button size="small" text type="danger" @click="removeReplaceRule(index)">移除</el-button>
        </div>
        <el-input v-model="rule.search" placeholder="查找内容（支持正则）" />
        <el-input v-model="rule.replace" placeholder="替换为（可留空）" />
      </div>
    </div>
    <div class="text-grid">
      <el-input v-model="state.content" type="textarea" :rows="8" placeholder="输入原始文本" />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runReplace">执行</el-button>
      </div>
      <PreviewPanel title="输出" :content="state.result" />
    </div>
    <el-table v-if="state.report.length" :data="state.report" border size="small" style="margin-top: 16px">
      <el-table-column type="index" width="60" label="#" />
      <el-table-column prop="search" label="查找" show-overflow-tooltip />
      <el-table-column prop="replacement" label="替换为" show-overflow-tooltip />
      <el-table-column prop="count" label="影响条数" width="120" />
    </el-table>
  </section>
</template>

<style scoped>
.text-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px minmax(0, 1fr);
  gap: 16px;
}

.text-grid-actions {
  display: flex;
  align-items: center;
  justify-content: center;
}

.rule-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.rule-row {
  border: 1px dashed var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--ppx-glass-bg);
  transition: all var(--ppx-transition-fast);
}

.rule-row:hover {
  border-color: var(--ppx-glass-border-hover);
}

.rule-row-line {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
</style>
