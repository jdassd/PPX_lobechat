<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  codecType: 'base64',
  operation: 'encode',
  direction: 'utf8_to_gbk',
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

const runCodec = async () => {
  if (!ensurePyReady()) return
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('text_encode_decode', {
      codecType: state.codecType,
      operation: state.operation,
      direction: state.direction,
      content: state.input
    })
    if (ok) {
      state.output = res.result || ''
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
      <h4>常见文本编码</h4>
      <p>Base64、URL、HTML 与 UTF-8/GBK 互转</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="编码类型">
        <el-select v-model="state.codecType" style="width: 200px">
          <el-option label="Base64" value="base64" />
          <el-option label="URL" value="url" />
          <el-option label="HTML" value="html" />
          <el-option label="字符集转换" value="charset" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="state.codecType !== 'charset'" label="操作">
        <el-radio-group v-model="state.operation">
          <el-radio-button label="encode">编码</el-radio-button>
          <el-radio-button label="decode">解码</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-else label="方向">
        <el-radio-group v-model="state.direction">
          <el-radio-button label="utf8_to_gbk">UTF-8 → GBK</el-radio-button>
          <el-radio-button label="gbk_to_utf8">GBK → UTF-8</el-radio-button>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <div class="text-grid">
      <el-input
        v-model="state.input"
        type="textarea"
        :rows="8"
        placeholder="在此输入原文本"
      />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runCodec">执行</el-button>
      </div>
      <el-input
        v-model="state.output"
        type="textarea"
        :rows="8"
        placeholder="输出结果"
        readonly
      />
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
</style>
