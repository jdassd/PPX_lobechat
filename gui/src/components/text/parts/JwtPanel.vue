<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import PreviewPanel from '../../shared/PreviewPanel.vue'
import { callApi, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)
const state = reactive({ token: '', result: null })

const headerText = computed(() => JSON.stringify(state.result?.header || {}, null, 2))
const payloadText = computed(() => JSON.stringify(state.result?.payload || {}, null, 2))
const validityType = computed(() => (state.result?.expired || state.result?.notYetValid ? 'danger' : 'success'))
const validityLabel = computed(() => {
  if (state.result?.expired) return '已过期'
  if (state.result?.notYetValid) return '尚未生效'
  return '时间声明正常'
})

const decodeToken = async () => {
  if (!state.token.trim()) return ElMessage.warning('请先粘贴 JWT')
  if (!hasPyApi()) return ElMessage.warning('该功能需在桌面客户端使用')
  loading.value = true
  try {
    const response = await callApi('text_decode_jwt', { token: state.token })
    if (!response.ok) return ElMessage.error(response.message || 'JWT 解码失败')
    state.result = response.data
    ElMessage.success(response.message)
  } catch (error) {
    ElMessage.error(error?.message || 'JWT 解码失败')
  } finally {
    loading.value = false
  }
}

const clear = () => {
  state.token = ''
  state.result = null
}

watch(
  () => state.token,
  () => {
    state.result = null
  }
)
</script>

<template>
  <section class="panel jwt-panel">
    <header>
      <h4>JWT 本地诊断</h4>
      <p>解码 Header、Payload 与时间声明；内容只在本机处理，不会进入任务历史。</p>
    </header>
    <el-alert title="此工具不验证签名，解码结果不能证明 Token 真实可信，也不能作为授权依据。" type="warning" :closable="false" show-icon />
    <el-input v-model="state.token" class="token-input" type="textarea" :rows="6" resize="vertical" autocomplete="off" spellcheck="false" placeholder="粘贴形如 xxxxx.yyyyy.zzzzz 的 JWT" />
    <div class="actions">
      <el-button @click="clear">清空</el-button>
      <el-button type="primary" :loading="loading" @click="decodeToken">解码并诊断</el-button>
    </div>

    <template v-if="state.result">
      <div class="summary">
        <el-tag effect="plain">算法：{{ state.result.algorithm || '未声明' }}</el-tag>
        <el-tag :type="state.result.signaturePresent ? 'warning' : 'danger'" effect="plain">{{ state.result.signaturePresent ? `携带签名（${state.result.signatureBytes} B，未验证）` : '没有签名' }}</el-tag>
        <el-tag :type="validityType" effect="plain">{{ validityLabel }}</el-tag>
      </div>
      <el-alert v-for="warning in state.result.warnings || []" :key="warning" class="warning-item" :title="warning" type="info" :closable="false" show-icon />
      <div v-if="Object.keys(state.result.claimTimes || {}).length" class="claim-times">
        <div v-for="(claim, name) in state.result.claimTimes" :key="name">
          <strong>{{ name }}</strong>
          <span>{{ claim.valid ? claim.iso : '无法解析' }}</span>
        </div>
      </div>
      <div class="result-grid">
        <PreviewPanel title="Header" :content="headerText" language="json" />
        <PreviewPanel title="Payload" :content="payloadText" language="json" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.token-input {
  margin-top: 16px;
  font-family: var(--ppx-font-mono);
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 20px 0 12px;
}
.warning-item + .warning-item {
  margin-top: 6px;
}
.claim-times {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 14px 0;
}
.claim-times div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: 10px;
  background: var(--ppx-bg-soft);
}
.claim-times strong {
  color: var(--accent);
  text-transform: uppercase;
}
.claim-times span {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}
@media (max-width: 850px) {
  .result-grid,
  .claim-times {
    grid-template-columns: 1fr;
  }
}
</style>
