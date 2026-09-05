<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi } from '../../utils/pyapi'
const props = defineProps({ file: { type: [Object, String], default: null } })
const preview = ref(null)
const busy = ref(false)
const page = ref(1)
const renderPages = ref(false)
const resetPreview = () => {
  page.value = 1
  preview.value = null
}
watch(
  () => props.file,
  () => {
    preview.value = null
    page.value = 1
  }
)
const load = async () => {
  if (!props.file) return
  busy.value = true
  try {
    const res = await callApi('word_preview', { filePath: props.file.path || props.file, offset: (page.value - 1) * 20, limit: 20, pageOffset: (page.value - 1) * 6, renderPages: renderPages.value })
    if (!res.ok) throw new Error(res.message)
    preview.value = res.data
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <section v-if="file" style="margin: 16px 0">
    <el-checkbox v-model="renderPages" @change="resetPreview">显示排版预览（需要 LibreOffice）</el-checkbox>
    <el-button :loading="busy" @click="load">预览文档</el-button>
    <template v-if="preview">
      <p>{{ preview.blockCount }} 个段落或表格行 · {{ preview.sectionCount }} 节。按页裁切遇到跨页内容块时会提示调整范围。</p>
      <div v-if="renderPages" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px">
        <figure v-for="item in preview.pages" :key="item.page" style="margin: 0">
          <el-image :src="item.preview" :preview-src-list="preview.pages.map((p) => p.preview)" style="width: 100%" />
          <figcaption>第 {{ item.page }} 页</figcaption>
        </figure>
      </div>
      <el-table v-else :data="preview.blocks">
        <el-table-column label="位置" width="90"
          ><template #default="{ row }">{{ row.index + 1 }}</template></el-table-column
        >
        <el-table-column label="类型" width="120"
          ><template #default="{ row }">{{ row.kind === 'tableRow' ? '表格行' : row.style || '段落' }}</template></el-table-column
        >
        <el-table-column prop="text" label="内容" show-overflow-tooltip />
        <el-table-column label="分节" width="70"
          ><template #default="{ row }">{{ row.sectionBreak ? '是' : '' }}</template></el-table-column
        >
      </el-table>
      <el-pagination v-model:current-page="page" :page-size="renderPages ? 6 : 20" :total="renderPages ? preview.pageCount : preview.blockCount" layout="prev, pager, next, total" @current-change="load" />
    </template>
  </section>
</template>
