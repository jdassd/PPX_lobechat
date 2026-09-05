<script setup>
import { computed, ref } from 'vue'
import { callApiRaw } from '../../utils/pyapi'
import { handoffAssets } from '../../utils/workspace'
const props = defineProps({ assets: { type: Array, default: () => [] } })
const opened = ref(false)
const page = ref(1)
const selection = ref([])
const target = ref('conversion')
const visible = computed(() => props.assets.slice((page.value - 1) * 20, page.value * 20))
const tools = { conversion: '格式转换', pdf: 'PDF 工具', word: 'Word 工具', excel: 'Excel 工具', image: '图片工具', video: '视频工具', file: '文件工具', document: '文档中心' }
const send = () => {
  handoffAssets(
    props.assets.filter((asset) => !selection.value.length || selection.value.includes(asset.path)),
    target.value
  )
  opened.value = false
}
</script>
<template>
  <el-button v-if="assets.length" size="small" @click="opened = true">检查结果 / 继续处理（{{ assets.length }}）</el-button>
  <el-dialog v-model="opened" title="处理结果" width="min(850px, 94vw)" append-to-body>
    <el-checkbox-group v-model="selection">
      <div v-for="asset in visible" :key="asset.path" class="asset">
        <el-checkbox :label="asset.path" :disabled="asset.exists === false">{{ asset.name }}</el-checkbox>
        <small>{{ asset.path }}</small>
        <el-tag v-if="asset.exists === false" type="warning">文件已移动或删除</el-tag>
        <el-button v-else size="small" @click="callApiRaw('system_pyOpenFile', asset.path)">打开</el-button>
      </div>
    </el-checkbox-group>
    <el-pagination v-model:current-page="page" :page-size="20" :total="assets.length" layout="prev, pager, next, total" />
    <template #footer>
      <el-select v-model="target" style="width: 150px"><el-option v-for="(label, id) in tools" :key="id" :label="label" :value="id" /></el-select>
      <el-button type="primary" @click="send">将{{ selection.length ? '所选' : '全部' }}结果交给下一工具</el-button>
    </template>
  </el-dialog>
</template>
<style scoped>
.asset {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--ppx-glass-border);
}
.asset small {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
