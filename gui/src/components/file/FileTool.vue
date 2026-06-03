<script setup>
import { computed, ref } from 'vue'

import SearchPanel from './parts/SearchPanel.vue'
import ClassifyPanel from './parts/ClassifyPanel.vue'
import CopyPanel from './parts/CopyPanel.vue'
import DeletePanel from './parts/DeletePanel.vue'
import RenamePanel from './parts/RenamePanel.vue'
import DedupPanel from './parts/DedupPanel.vue'
import AnalyzePanel from './parts/AnalyzePanel.vue'
import ComparePanel from './parts/ComparePanel.vue'
import ArchivePanel from './parts/ArchivePanel.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const activeTab = ref('search')
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="78%"
    append-to-body
    custom-class="file-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">FILE TOOLKIT</p>
          <h3>文件管理工具</h3>
          <p class="sub">搜索、目录分析与压缩解压</p>
        </div>
      </div>
    </template>
    <div class="file-tool">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="文件搜索" name="search">
          <SearchPanel />
        </el-tab-pane>

        <el-tab-pane label="自动分类" name="classify">
          <ClassifyPanel />
        </el-tab-pane>

        <el-tab-pane label="批量复制" name="copy">
          <CopyPanel />
        </el-tab-pane>

        <el-tab-pane label="批量删除" name="delete">
          <DeletePanel />
        </el-tab-pane>

        <el-tab-pane label="批量改名" name="rename">
          <RenamePanel />
        </el-tab-pane>

        <el-tab-pane label="文件去重" name="dedup">
          <DedupPanel />
        </el-tab-pane>

        <el-tab-pane label="目录分析" name="analyze">
          <AnalyzePanel />
        </el-tab-pane>

        <el-tab-pane label="文件对比" name="compare">
          <ComparePanel />
        </el-tab-pane>

        <el-tab-pane label="压缩 / 解压" name="archive">
          <ArchivePanel />
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>
