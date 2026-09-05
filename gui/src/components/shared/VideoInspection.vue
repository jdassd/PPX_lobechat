<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi } from '../../utils/pyapi'
const props = defineProps({ file: { type: [Object, String], default: null } })
const report = ref(null)
const busy = ref(false)
watch(
  () => props.file,
  () => {
    report.value = null
  }
)
const inspect = async () => {
  busy.value = true
  try {
    const response = await callApi('video_inspect', { filePath: props.file.path || props.file })
    if (!response.ok) return ElMessage.error(response.message)
    report.value = response.data
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <section v-if="file" style="margin: 12px 0">
    <el-button :loading="busy" @click="inspect">检查编码与时长</el-button>
    <template v-if="report">
      <p>时长 {{ Number(report.format?.duration || 0).toFixed(2) }} 秒 · {{ report.format?.format_long_name }}</p>
      <el-table :data="report.streams" size="small">
        <el-table-column prop="codec_type" label="媒体流" /><el-table-column prop="codec_name" label="编码" />
        <el-table-column label="尺寸 / 采样率"
          ><template #default="{ row }">{{ row.width ? `${row.width} × ${row.height}` : `${row.sample_rate || ''} Hz` }}</template></el-table-column
        >
        <el-table-column prop="avg_frame_rate" label="帧率" />
      </el-table>
    </template>
  </section>
</template>
