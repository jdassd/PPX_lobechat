<script setup>
import { onMounted, reactive } from 'vue'
import { Files, InfoFilled, Picture, Refresh } from '@element-plus/icons-vue'

import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import { useInitialTab } from '@/composables/useInitialTab'
import { callApi, hasPyApi } from '@/utils/pyapi'
import EngineInfoPanel from './parts/EngineInfoPanel.vue'
import PdfBatchPanel from './parts/PdfBatchPanel.vue'
import UniversalConvertPanel from './parts/UniversalConvertPanel.vue'

const TABS = [
  { name: 'universal', label: '通用转换', icon: Refresh },
  { name: 'images-pdf', label: '图片合成 PDF', icon: Picture },
  { name: 'merge-pdf', label: 'PDF 合并', icon: Files },
  { name: 'engine', label: '引擎与许可', icon: InfoFilled }
]

const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = useInitialTab(TABS, () => props.initialTab, 'universal')

const engine = reactive({
  loading: true,
  available: false,
  detail: '正在检测本地转换引擎…',
  runtime: {},
  groups: {},
  optional: [],
  metadata: {
    name: 'FlyingMouse Format',
    author: '牢蜂（LaoFeng）',
    license: '个人非商用许可'
  }
})

const loadEngine = async () => {
  engine.loading = true
  engine.detail = '正在检测本地转换引擎…'
  if (!hasPyApi()) {
    engine.available = false
    engine.detail = '转换中心需要在 PPX 桌面客户端中使用'
    engine.loading = false
    return
  }
  try {
    const { ok, data, message } = await callApi('format_center_capabilities')
    engine.available = Boolean(ok && data?.available)
    engine.detail = data?.detail || message || (engine.available ? '转换引擎已就绪' : '转换引擎未就绪')
    engine.runtime = data?.runtime || {}
    engine.groups = data?.groups || {}
    engine.optional = data?.optional || []
    engine.metadata = { ...engine.metadata, ...(data?.engine || {}) }
  } catch (error) {
    engine.available = false
    engine.detail = error?.message || '转换引擎检测失败'
  } finally {
    engine.loading = false
  }
}

const showEngine = () => {
  activeTab.value = 'engine'
}

onMounted(loadEngine)
</script>

<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#0c9c8f" content-width="980px">
    <UniversalConvertPanel v-show="activeTab === 'universal'" :engine="engine" @open-engine="showEngine" />
    <PdfBatchPanel v-show="activeTab === 'images-pdf'" mode="images" :engine="engine" @open-engine="showEngine" />
    <PdfBatchPanel v-show="activeTab === 'merge-pdf'" mode="pdf" :engine="engine" @open-engine="showEngine" />
    <EngineInfoPanel v-show="activeTab === 'engine'" :engine="engine" @refresh="loadEngine" />
  </ToolWorkspace>
</template>
