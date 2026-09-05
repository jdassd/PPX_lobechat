<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi } from '../../utils/pyapi'
const props = defineProps({ method: { type: String, required: true }, options: { type: Object, required: true } })
const loading = ref(false)
const result = ref(null)
const stale = ref(false)
watch(
  () => props.options,
  () => {
    if (result.value) stale.value = true
  },
  { deep: true }
)
const preview = async () => {
  loading.value = true
  try {
    const response = await callApi('image_operation_preview', { method: props.method, options: props.options })
    if (!response.ok) return ElMessage.error(response.message)
    result.value = response.data
    stale.value = false
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}
</script>
<template>
  <section class="effect-preview">
    <el-button :loading="loading" @click="preview">预览第一张图片的处理效果</el-button>
    <el-tag v-if="stale" type="warning">参数已变化，请重新预览</el-tag>
    <div v-if="result" class="comparison">
      <figure>
        <img :src="result.before.preview" alt="处理前" />
        <figcaption>处理前 {{ result.before.width }} × {{ result.before.height }} · {{ (result.sourceBytes / 1024).toFixed(1) }} KB</figcaption>
      </figure>
      <figure>
        <img :src="result.after.preview" alt="处理后" />
        <figcaption>处理后 {{ result.after.width }} × {{ result.after.height }} · {{ (result.outputBytes / 1024).toFixed(1) }} KB</figcaption>
      </figure>
    </div>
    <el-alert v-if="result?.item?.targetMet === false" title="当前质量范围无法达到目标体积，可以降低目标要求或调整图像尺寸。" type="warning" :closable="false" />
  </section>
</template>
<style scoped>
.effect-preview {
  margin: 16px 0;
}
.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.comparison figure {
  margin: 12px 0;
  padding: 8px;
  background: repeating-conic-gradient(#eee 0% 25%, white 0% 50%) 0 / 16px 16px;
}
.comparison img {
  width: 100%;
  height: 240px;
  object-fit: contain;
}
.comparison figcaption {
  background: var(--ppx-bg-base);
  padding: 8px;
  font-size: 12px;
}
</style>
