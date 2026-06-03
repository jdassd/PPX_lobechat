<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  sourceType: 'text',
  hashType: 'md5',
  content: '',
  file: null,
  result: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runHash = async () => {
  if (!ensurePyReady()) return
  if (state.sourceType === 'file' && !state.file) {
    ElMessage.warning('请选择文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('text_hash_calculate', {
      sourceType: state.sourceType,
      hashType: state.hashType,
      content: state.content,
      file: state.file
    })
    if (ok) {
      state.result = res.result || ''
      ElMessage.success(message || '计算完成')
    } else {
      ElMessage.error(message || '计算失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '计算失败')
  } finally {
    loading.value = false
  }
}

const selectHashFile = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', ['全部文件 (*.*)'])
  if (files?.length) {
    state.file = files[0]
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>MD5 / SHA 系列</h4>
      <p>支持字符串与文件两种来源</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="输入类型">
        <el-radio-group v-model="state.sourceType">
          <el-radio-button label="text">文本</el-radio-button>
          <el-radio-button label="file">文件</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="算法">
        <el-select v-model="state.hashType" style="width: 200px">
          <el-option label="MD5" value="md5" />
          <el-option label="SHA-1" value="sha1" />
          <el-option label="SHA-256" value="sha256" />
          <el-option label="SHA-512" value="sha512" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="state.sourceType === 'text'" label="文本">
        <el-input
          v-model="state.content"
          type="textarea"
          :rows="4"
          placeholder="输入要计算的文本"
        />
      </el-form-item>
      <el-form-item v-else label="文件">
        <div class="field-row">
          <el-input :model-value="state.file?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectHashFile">选择文件</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runHash">开始计算</el-button>
      </el-form-item>
    </el-form>
    <el-input v-model="state.result" readonly placeholder="哈希结果" />
  </section>
</template>

<style scoped>
.form-gap {
  margin-top: 12px;
}
</style>
