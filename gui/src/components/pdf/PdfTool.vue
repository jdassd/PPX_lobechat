<template>
  <ToolWorkspace v-model="activeTab" :tabs="TABS" accent="#e0533d">
    <ImagePanel v-show="activeTab === 'image'" />
    <ScanPanel v-show="activeTab === 'scan'" />
    <CompressPanel v-show="activeTab === 'compress'" />
    <MergePanel v-show="activeTab === 'merge'" />
    <SplitPanel v-show="activeTab === 'split'" />
    <CutPanel v-show="activeTab === 'cut'" />
    <ReorderPanel v-show="activeTab === 'reorder'" />
    <ExtractTextPanel v-show="activeTab === 'text'" />
    <TocPanel v-show="activeTab === 'toc'" />
    <WordPanel v-show="activeTab === 'word'" />
    <ExtractImagesPanel v-show="activeTab === 'images'" />
    <ImagePdfPanel v-show="activeTab === 'imagePdf'" />

    <section class="log-panel">
      <header>
        <h4>最近操作</h4>
        <p>保留最近 8 条，便于定位输出目录</p>
      </header>
      <el-timeline v-if="shared.logs.length">
        <el-timeline-item
          v-for="item in shared.logs"
          :key="item.id"
          :timestamp="item.time"
          :type="item.type"
          size="large"
        >
          <div class="log-entry">
            <strong>{{ item.message }}</strong>
            <p class="log-sub">{{ item.action }}</p>
            <el-link v-if="item.detail?.output" type="primary" @click="openPath(item.detail.output)">
              打开输出
            </el-link>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无记录" />
    </section>
  </ToolWorkspace>
</template>

<script setup>
import { provide, reactive, ref } from 'vue'
import ToolWorkspace from '@/components/shared/ToolWorkspace.vue'
import { usePdfApi } from './parts/usePdfApi'
import ImagePanel from './parts/ImagePanel.vue'
import ScanPanel from './parts/ScanPanel.vue'
import CompressPanel from './parts/CompressPanel.vue'
import MergePanel from './parts/MergePanel.vue'
import SplitPanel from './parts/SplitPanel.vue'
import CutPanel from './parts/CutPanel.vue'
import ReorderPanel from './parts/ReorderPanel.vue'
import ExtractTextPanel from './parts/ExtractTextPanel.vue'
import TocPanel from './parts/TocPanel.vue'
import WordPanel from './parts/WordPanel.vue'
import ExtractImagesPanel from './parts/ExtractImagesPanel.vue'
import ImagePdfPanel from './parts/ImagePdfPanel.vue'

const TABS = [
  { name: 'image', label: 'PDF 转高清图片' },
  { name: 'scan', label: 'PDF → 扫描件' },
  { name: 'compress', label: 'PDF 压缩' },
  { name: 'merge', label: '合并 PDF' },
  { name: 'split', label: '拆分 PDF' },
  { name: 'cut', label: '页码切割' },
  { name: 'reorder', label: '页面重排' },
  { name: 'text', label: '提取文本' },
  { name: 'toc', label: '生成目录' },
  { name: 'word', label: 'PDF 转 Word' },
  { name: 'images', label: '提取图片' },
  { name: 'imagePdf', label: '图片转 PDF' },
]

const activeTab = ref('image')

// 全局共享：loading 为唯一开关，logs 显示在底部统一日志面板，需跨所有子面板共享。
const shared = reactive({
  loading: false,
  logs: [],
})

// 共享的 PDF 调用层（封装 callApi / 文件目录选择 / 打开文件等），下沉给各子面板复用。
const pdfApi = usePdfApi(shared)
const { openPath } = pdfApi

provide('pdfApi', pdfApi)
provide('pdfShared', shared)
</script>

<style scoped>
.log-panel {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--ppx-glass-border);
}
.log-panel header {
  margin-bottom: 12px;
}
.log-panel header h4 {
  margin: 0;
  color: var(--ppx-text-primary);
}
.log-panel header p {
  margin: 4px 0 0;
  color: var(--ppx-text-muted);
  font-size: 13px;
}
.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.log-entry .log-sub {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>
