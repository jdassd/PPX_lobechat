<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  fileA: null,
  fileB: null,
  mode: 'auto',
  encoding: 'utf-8',
  ignoreCase: false,
  result: '',
  diffText: '',
  size: null,
  hash: null,
  encodingInfo: null
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectCompareFile = async (target) => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', ['全部文件 (*.*)'])
  if (files?.length) {
    state[target] = files[0]
  }
}

const runCompare = async () => {
  if (!ensurePyReady()) return
  if (!state.fileA || !state.fileB) {
    ElMessage.warning('请先选择两个文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_compare', {
      fileA: state.fileA.path,
      fileB: state.fileB.path,
      mode: state.mode,
      encoding: state.encoding,
      ignoreCase: state.ignoreCase
    })
    if (ok) {
      state.result = res.equal ? '两个文件内容一致' : '检测到差异'
      state.diffText = (res.diff || []).join('\n')
      state.hash = res.hash || null
      state.size = res.size || null
      state.encodingInfo = res.encoding || null
      ElMessage.success(message || '对比完成')
    } else {
      ElMessage.error(message || '对比失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '对比失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>文本 / 二进制对比</h4>
      <p>快速确认两个文件是否一致，并给出差异 diff</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="文件 A">
        <div class="field-row">
          <el-input :model-value="state.fileA?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectCompareFile('fileA')">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="文件 B">
        <div class="field-row">
          <el-input :model-value="state.fileB?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectCompareFile('fileB')">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="state.mode">
          <el-radio-button label="auto">自动</el-radio-button>
          <el-radio-button label="text">文本</el-radio-button>
          <el-radio-button label="binary">二进制</el-radio-button>
        </el-radio-group>
        <el-checkbox v-model="state.ignoreCase" style="margin-left: 12px">忽略大小写</el-checkbox>
      </el-form-item>
      <el-form-item v-if="state.mode !== 'binary'" label="首选编码">
        <el-input v-model="state.encoding" placeholder="默认 UTF-8" style="width: 220px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runCompare">执行对比</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="state.result"
      :type="state.diffText ? 'warning' : 'success'"
      :closable="false"
      show-icon
    >
      <template #title>{{ state.result }}</template>
    </el-alert>
    <el-descriptions
      v-if="state.hash || state.size"
      :column="2"
      border
      size="small"
      style="margin-top: 12px"
    >
      <el-descriptions-item label="文件 A 大小">
        {{ state.size?.leftText || state.size?.left || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="文件 B 大小">
        {{ state.size?.rightText || state.size?.right || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="文件 A 哈希">
        {{ state.hash?.left || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="文件 B 哈希">
        {{ state.hash?.right || '-' }}
      </el-descriptions-item>
    </el-descriptions>
    <el-input
      v-if="state.diffText"
      v-model="state.diffText"
      type="textarea"
      :rows="12"
      readonly
      style="margin-top: 16px"
    />
  </section>
</template>

<style scoped>
.form-gap {
  margin-top: 12px;
}
</style>
