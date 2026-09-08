<script setup>
import { computed, getCurrentInstance, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { toolById } from '@/config/tools'
import { isToolEnabled } from '@/composables/useToolRegistry'
import { useCapabilities } from '@/composables/useCapabilities'
import { callApiRaw } from '../../utils/pyapi'
import { handoffAssets } from '../../utils/workspace'
import { getResultRoutes } from '../../utils/resultRouting.mjs'

const props = defineProps({ assets: { type: Array, default: () => [] }, sourceTaskId: { type: String, default: '' } })
const emit = defineEmits(['sent'])
const { state: capabilities, loadCapabilities } = useCapabilities()
const opened = ref(false)
const page = ref(1)
const selection = ref([])
const routeId = ref('')
const pageSize = 20
const selectorId = `handoff-route-${getCurrentInstance().uid}`
const assetName = (asset) => asset.name || (typeof asset.path === 'string' ? asset.path.split(/[\\/]/).pop() : '') || '无效结果'
const selectable = (asset) => typeof asset?.path === 'string' && asset.path.trim() && asset.kind !== 'directory' && asset.exists !== false
const usableAssets = computed(() => props.assets.filter(selectable))
const selectedAssets = computed(() => {
  const paths = new Set(selection.value)
  return usableAssets.value.filter((asset) => paths.has(asset.path))
})
const visible = computed(() => props.assets.slice((page.value - 1) * pageSize, page.value * pageSize).map((asset) => asset || {}))
const routes = computed(() =>
  getResultRoutes(selectedAssets.value).map((plan) => {
    const tool = toolById(plan.route.tool)
    const dependency = capabilities.capabilities[plan.route.dependency]
    const unavailable = !tool || !isToolEnabled(tool) ? '请先在模块中心启用' : plan.route.dependency && capabilities.loading ? '正在检测依赖' : dependency?.available === false ? dependency.detail || '所需依赖不可用' : ''
    return { ...plan, toolName: tool?.name || '', unavailable, dependency }
  })
)
const plan = computed(() => routes.value.find((item) => item.route.id === routeId.value))
const skippedReasons = computed(() => [...new Set(plan.value?.skipped.map((item) => item.reason) || [])].join('；'))
const selectAll = () => {
  selection.value = [...new Set(usableAssets.value.map((asset) => asset.path))]
  page.value = 1
}
watch(opened, (value) => {
  if (!value) return
  selectAll()
  loadCapabilities()
})
watch(
  () => props.assets,
  () => {
    page.value = Math.min(page.value, Math.max(1, Math.ceil(props.assets.length / pageSize)))
    const paths = new Set(usableAssets.value.map((asset) => asset.path))
    selection.value = selection.value.filter((path) => paths.has(path))
  },
  { deep: true }
)
watch(routes, (items) => {
  if (!items.some((item) => item.route.id === routeId.value && !item.unavailable)) routeId.value = items.find((item) => !item.unavailable)?.route.id || ''
})
const openFile = async (asset) => {
  try {
    await callApiRaw('system_pyOpenFile', asset.path)
  } catch (error) {
    ElMessage.error(error.message || '无法打开文件，请检查文件是否仍在原位置')
  }
}
const send = () => {
  if (!plan.value?.acceptedCount || plan.value.unavailable) return
  if (handoffAssets(plan.value.assets, routeId.value, props.sourceTaskId)) {
    opened.value = false
    emit('sent')
  }
}
</script>

<template>
  <el-button v-if="assets.length" size="small" @click="opened = true">检查结果 / 继续处理（{{ assets.length }}）</el-button>
  <el-dialog v-model="opened" title="处理结果" width="min(900px, 94vw)" top="4vh" append-to-body class="ppx-result-dialog">
    <div class="selection-tools">
      <span>已选择 {{ selectedAssets.length }} / {{ assets.length }} 个结果</span>
      <el-button text size="small" @click="selectAll">全选可用文件</el-button>
      <el-button text size="small" :disabled="!selection.length" @click="selection = []">清空选择</el-button>
    </div>
    <p v-if="usableAssets.length < assets.length" class="muted">目录、缺失文件和无路径结果不可发送；原结果仍保留在这里。</p>
    <el-checkbox-group v-model="selection" class="asset-list" aria-label="选择处理结果">
      <div v-for="(asset, index) in visible" :key="index" class="asset">
        <el-checkbox :label="typeof asset.path === 'string' ? asset.path : 'invalid-' + index" :disabled="!selectable(asset)"
          ><span class="asset-name">{{ assetName(asset) }}</span></el-checkbox
        >
        <small :title="asset.path">{{ asset.path }}</small>
        <el-tag v-if="asset.kind === 'directory'" type="info">文件夹</el-tag>
        <el-tag v-else-if="asset.exists === false" type="warning">文件已移动或删除</el-tag>
        <el-button v-if="selectable(asset)" size="small" @click="openFile(asset)">打开</el-button>
      </div>
    </el-checkbox-group>
    <el-pagination v-if="assets.length > pageSize" v-model:current-page="page" :page-size="pageSize" :total="assets.length" layout="prev, pager, next, total" />
    <div class="handoff-options">
      <label :for="selectorId">下一步</label>
      <el-select :id="selectorId" v-model="routeId" aria-label="下一步操作" placeholder="选择兼容操作" :disabled="!routes.length" class="route-select">
        <el-option v-for="item in routes" :key="item.route.id" :label="item.route.label + ' · ' + item.acceptedCount + ' 个文件'" :value="item.route.id" :disabled="!!item.unavailable">
          <span>{{ item.route.label }} · {{ item.acceptedCount }} 个文件</span><small class="route-status">{{ item.unavailable || item.toolName }}</small>
        </el-option>
      </el-select>
      <el-button text size="small" :loading="capabilities.loading" @click="loadCapabilities(true)">重新检测依赖</el-button>
    </div>
    <div v-if="plan" class="plan-note" aria-live="polite">
      <strong>将发送 {{ plan.acceptedCount }} 个文件到：{{ plan.route.label }}</strong>
      <p>{{ plan.route.description }} 接收后不会自动执行。</p>
      <p v-if="plan.skippedCount" class="skip-note">本次跳过 {{ plan.skippedCount }} 个结果：{{ skippedReasons }}。可重新选择操作或文件。</p>
      <p v-if="plan.route.capability?.maximumAssets">此操作一次接收一个文件，将替换目标操作当前的源文件；其它参数保留。</p>
      <p v-if="plan.route.dependency && !plan.dependency" class="muted">依赖状态尚未确认，目标工具会在运行前检查。</p>
    </div>
    <el-empty v-else :image-size="48" :description="!selection.length ? '请选择要继续处理的文件' : routes.length ? '兼容操作暂不可用，请启用模块或检查依赖' : '没有兼容操作，可先只选择一个文件再试'" />
    <template #footer>
      <span class="muted footer-note">文件在本机处理；运行时会再次检查文件是否可用。</span>
      <el-button @click="opened = false">取消</el-button>
      <el-button type="primary" :disabled="!plan?.acceptedCount || !!plan?.unavailable" @click="send">交给下一工具</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
:global(.ppx-result-dialog) {
  display: flex;
  flex-direction: column;
  max-height: 92vh;
}
:global(.ppx-result-dialog .el-dialog__body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
:global(.ppx-result-dialog .el-dialog__header),
:global(.ppx-result-dialog .el-dialog__footer) {
  flex-shrink: 0;
}
.selection-tools,
.handoff-options,
.asset {
  display: flex;
  align-items: center;
  gap: 12px;
}
.selection-tools {
  flex-wrap: wrap;
  font-size: 13px;
}
.asset-list {
  display: block;
  line-height: 1.5;
  max-height: 30vh;
  overflow-y: auto;
  margin: 12px 0;
}
.asset {
  padding: 9px 0;
  border-bottom: 1px solid var(--ppx-glass-border);
}
.asset :deep(.el-checkbox) {
  max-width: 45%;
  min-width: 0;
}
.asset-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}
.asset small {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ppx-text-muted);
}
.handoff-options {
  flex-wrap: wrap;
  margin-top: 20px;
}
.route-select {
  flex: 1;
  min-width: 200px;
}
.route-status {
  margin-left: 14px;
  color: var(--ppx-text-muted);
}
.plan-note {
  margin-top: 16px;
  padding: 16px;
  background: var(--ppx-bg-base);
  border-radius: var(--ppx-radius-md);
  line-height: 1.6;
}
.plan-note p {
  margin: 5px 0 0;
}
.skip-note {
  color: var(--el-color-warning-dark-2);
}
.muted {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.footer-note {
  margin-right: auto;
}
@media (max-width: 640px) {
  .asset {
    flex-wrap: wrap;
  }
  .asset :deep(.el-checkbox) {
    max-width: 100%;
  }
  .asset small {
    flex-basis: 100%;
    order: 2;
  }
  .footer-note {
    display: block;
    margin-bottom: 8px;
  }
}
</style>
