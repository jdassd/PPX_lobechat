<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

import PreviewPanel from '../../shared/PreviewPanel.vue'

const loading = ref(false)

const state = reactive({
  mode: 'escape',
  content: '',
  codePoints: '',
  result: '',
  preview: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runUnicode = async () => {
  if (!ensurePyReady()) return
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('text_unicode_convert', {
      mode: state.mode,
      content: state.content,
      codePoints: state.codePoints,
      uppercase: true
    })
    if (ok) {
      state.result = res.result || ''
      state.preview = res.codepoints || res.preview || []
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
      <h4>Unicode 编码 / 解码</h4>
      <p>在文本与 \\uXXXX、编码点间快速转换，支持批量列表</p>
    </header>
    <el-form :model="state" label-width="120px" class="form-gap">
      <el-form-item label="模式">
        <el-radio-group v-model="state.mode">
          <el-radio-button label="escape">文本 → \\u</el-radio-button>
          <el-radio-button label="unescape">\\u → 文本</el-radio-button>
          <el-radio-button label="codepoint">输出编码点</el-radio-button>
          <el-radio-button label="from_codepoint">编码点 → 文本</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="state.mode === 'from_codepoint'" label="编码点列表">
        <el-input
          v-model="state.codePoints"
          type="textarea"
          :rows="4"
          placeholder="示例：0041 0042 或 U+1F600,U+1F64C"
        />
      </el-form-item>
    </el-form>
    <div class="text-grid">
      <el-input
        v-model="state.content"
        type="textarea"
        :rows="8"
        placeholder="输入文本或编码点"
      />
      <div class="text-grid-actions">
        <el-button type="primary" :loading="loading" @click="runUnicode">执行</el-button>
      </div>
      <PreviewPanel title="输出" :content="state.result" />
    </div>
    <el-table
      v-if="state.preview?.length"
      :data="state.preview"
      border
      size="small"
      style="margin-top: 16px"
    >
      <el-table-column prop="char" label="字符" width="120" />
      <el-table-column prop="code" label="Unicode" />
      <el-table-column prop="decimal" label="十进制" width="120" />
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
