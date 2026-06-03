<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

const state = reactive({
  direction: 'ts_to_date',
  timestamp: '',
  datetime: '',
  unit: 's',
  timezone: 'Asia/Shanghai',
  result: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runTimestamp = async () => {
  if (!ensurePyReady()) return
  loading.value = true
  try {
    const payload = {
      direction: state.direction,
      timezone: state.timezone,
      unit: state.unit
    }
    if (state.direction === 'ts_to_date') {
      payload.timestamp = state.timestamp
    } else {
      payload.datetime = state.datetime
    }
    const { ok, data: res, message } = await pyCall('text_timestamp_convert', payload)
    if (ok) {
      state.result = JSON.stringify(res, null, 2)
      ElMessage.success(message || '转换完成')
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
      <h4>时间戳 ↔ 日期</h4>
      <p>支持秒/毫秒与多时区转换</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="方向">
        <el-radio-group v-model="state.direction">
          <el-radio-button label="ts_to_date">时间戳 → 日期</el-radio-button>
          <el-radio-button label="date_to_ts">日期 → 时间戳</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="单位" v-if="state.direction === 'ts_to_date'">
        <el-radio-group v-model="state.unit">
          <el-radio-button label="s">秒</el-radio-button>
          <el-radio-button label="ms">毫秒</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="state.direction === 'ts_to_date'" label="时间戳">
        <el-input v-model="state.timestamp" placeholder="例如 1700000000 或 1700000000000" />
      </el-form-item>
      <el-form-item v-else label="日期时间">
        <el-input v-model="state.datetime" placeholder="2024-11-01 08:00:00" />
      </el-form-item>
      <el-form-item label="时区">
        <el-input v-model="state.timezone" placeholder="如 Asia/Shanghai 或 UTC+8" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runTimestamp">转换</el-button>
      </el-form-item>
    </el-form>
    <PreviewPanel v-if="state.result" title="结果 JSON" :content="state.result" />
  </section>
</template>

<style scoped>
.form-gap {
  margin-top: 12px;
}
</style>
