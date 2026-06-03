<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

const state = reactive({
  mode: 'upper',
  input: '',
  output: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runTransform = async () => {
  if (!ensurePyReady()) return
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('text_case_transform', {
      mode: state.mode,
      content: state.input
    })
    if (ok) {
      state.output = res.result || ''
      ElMessage.success(message || '转换成功')
    } else {
      ElMessage.error(message || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>大小写与命名规范</h4>
      <p>一键切换 Upper / Lower / Camel / Snake</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="转换类型">
        <el-select v-model="state.mode" style="width: 240px">
          <el-option label="全大写" value="upper" />
          <el-option label="全小写" value="lower" />
          <el-option label="标题格式" value="title" />
          <el-option label="句首大写" value="sentence" />
          <el-option label="camelCase" value="camel" />
          <el-option label="PascalCase" value="pascal" />
          <el-option label="snake_case" value="snake" />
          <el-option label="kebab-case" value="kebab" />
        </el-select>
      </el-form-item>
    </el-form>
    <div class="text-grid">
      <el-input
        v-model="state.input"
        type="textarea"
        :rows="6"
        placeholder="输入原始文本"
      />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runTransform">转换</el-button>
      </div>
      <PreviewPanel title="结果" :content="state.output" />
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
