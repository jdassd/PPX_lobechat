<template>
  <el-drawer
    v-model="visibleProxy"
    size="80%"
    append-to-body
    custom-class="pdf-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">PDF TOOLKIT</p>
          <h3>PDF 工具集</h3>
          <p class="sub">在一个面板内完成转换、扫描件、合并、拆分与页码切割</p>
        </div>
      </div>
    </template>
    <div class="pdf-tool">
      <el-tabs v-model="activeTab" class="pdf-tabs">
        <el-tab-pane label="PDF 转高清图片" name="image">
          <ImagePanel />
        </el-tab-pane>

        <el-tab-pane label="PDF → 扫描件" name="scan">
          <ScanPanel />
        </el-tab-pane>

        <el-tab-pane label="PDF 压缩" name="compress">
          <CompressPanel />
        </el-tab-pane>

        <el-tab-pane label="合并 PDF" name="merge">
          <MergePanel />
        </el-tab-pane>

        <el-tab-pane label="拆分 PDF" name="split">
          <SplitPanel />
        </el-tab-pane>

        <el-tab-pane label="页码切割" name="cut">
          <CutPanel />
        </el-tab-pane>

        <el-tab-pane label="页面重排" name="reorder">
          <ReorderPanel />
        </el-tab-pane>

        <el-tab-pane label="提取文本" name="text">
          <ExtractTextPanel />
        </el-tab-pane>

        <el-tab-pane label="生成目录" name="toc">
          <TocPanel />
        </el-tab-pane>

        <el-tab-pane label="PDF 转 Word" name="word">
          <WordPanel />
        </el-tab-pane>

        <el-tab-pane label="提取图片" name="images">
          <ExtractImagesPanel />
        </el-tab-pane>

        <el-tab-pane label="图片转 PDF" name="imagePdf">
          <ImagePdfPanel />
        </el-tab-pane>
      </el-tabs>

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
              <el-link
                v-if="item.detail?.output"
                type="primary"
                @click="openPath(item.detail.output)"
              >
                打开输出
              </el-link>
            </div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无记录" />
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, provide, reactive, ref } from 'vue'
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

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const activeTab = ref('image')

// 全局共享：loading 为唯一开关，logs 显示在底部统一日志面板，需跨所有子面板共享。
const shared = reactive({
  loading: false,
  logs: []
})

// 共享的 PDF 调用层（封装 callApi / 文件目录选择 / 打开文件等），下沉给各子面板复用。
const pdfApi = usePdfApi(shared)
const { openPath } = pdfApi

provide('pdfApi', pdfApi)
provide('pdfShared', shared)
</script>

<style scoped>
/* 使用全局深空玻璃主题样式 */

/* 日志面板 - 使用全局样式变量 */
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
