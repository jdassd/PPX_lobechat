<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

const state = reactive({
  content: '',
  pattern: '',
  flags: [],
  operation: 'search',
  replacement: '',
  matches: [],
  output: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runRegex = async () => {
  if (!ensurePyReady()) return
  if (!state.pattern.trim()) {
    ElMessage.warning('请输入正则表达式')
    return
  }
  loading.value = true
  try {
    const payload = {
      content: state.content,
      pattern: state.pattern,
      flags: state.flags,
      operation: state.operation,
      replacement: state.replacement
    }
    const { ok, data: res, message } = await pyCall('text_regex_match', payload)
    if (ok) {
      state.matches = res.matches || []
      state.output = res.result || res.extracted?.join('\n') || ''
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
      <h4>正则匹配 / 替换 / 提取</h4>
      <p>支持多种 Flag，实时回显命中区间</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="操作">
        <el-radio-group v-model="state.operation">
          <el-radio-button label="search">匹配</el-radio-button>
          <el-radio-button label="replace">替换</el-radio-button>
          <el-radio-button label="extract">提取</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="正则表达式">
        <el-input v-model="state.pattern" placeholder="例如：\\d{3}-\\d{4}" />
      </el-form-item>
      <el-form-item label="标志">
        <el-checkbox-group v-model="state.flags">
          <el-checkbox label="ignorecase">忽略大小写</el-checkbox>
          <el-checkbox label="multiline">多行</el-checkbox>
          <el-checkbox label="dotall">DotAll</el-checkbox>
        </el-checkbox-group>
      </el-form-item>
      <el-form-item v-if="state.operation === 'replace'" label="替换为">
        <el-input v-model="state.replacement" placeholder="输入替换文本" />
      </el-form-item>
    </el-form>
    <div class="text-grid">
      <el-input
        v-model="state.content"
        type="textarea"
        :rows="8"
        placeholder="输入原始文本"
      />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runRegex">执行</el-button>
      </div>
      <PreviewPanel title="输出 / 命中" :content="state.output" />
    </div>
    <el-table
      v-if="state.matches.length && state.operation !== 'replace'"
      :data="state.matches"
      border
      size="small"
      style="margin-top: 16px"
    >
      <el-table-column label="匹配文本" prop="match" />
      <el-table-column label="开始" prop="start" width="80" />
      <el-table-column label="结束" prop="end" width="80" />
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

.form-gap {
  margin-top: 12px;
}
</style>
