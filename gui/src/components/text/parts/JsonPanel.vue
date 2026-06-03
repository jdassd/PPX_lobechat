<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

const state = reactive({
  operation: 'format',
  input: '',
  path: '',
  output: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runJson = async () => {
  if (!ensurePyReady()) return
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('text_format_json', {
      operation: state.operation,
      content: state.input,
      path: state.path
    })
    if (ok) {
      state.output = typeof res.result === 'string' ? res.result : JSON.stringify(res.result, null, 2)
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
      <h4>JSON 格式化、压缩与查询</h4>
      <p>支持 JSONPath 风格的 $ 节点查询</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="操作">
        <el-select v-model="state.operation" style="width: 220px">
          <el-option label="美化" value="format" />
          <el-option label="压缩" value="compress" />
          <el-option label="校验" value="validate" />
          <el-option label="查询" value="query" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="state.operation === 'query'" label="路径">
        <el-input
          v-model="state.path"
          placeholder="示例：$.items[0].name"
          clearable
        />
      </el-form-item>
    </el-form>
    <div class="text-grid">
      <el-input
        v-model="state.input"
        type="textarea"
        :rows="10"
        placeholder="粘贴 JSON 字符串"
      />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runJson">执行</el-button>
      </div>
      <PreviewPanel title="输出" :content="state.output" />
    </div>
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
