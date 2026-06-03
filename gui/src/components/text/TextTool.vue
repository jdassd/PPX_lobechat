<script setup>
import { computed, ref } from 'vue'

import CodecPanel from './parts/CodecPanel.vue'
import RegexPanel from './parts/RegexPanel.vue'
import JsonPanel from './parts/JsonPanel.vue'
import CsvPanel from './parts/CsvPanel.vue'
import TransformPanel from './parts/TransformPanel.vue'
import DedupPanel from './parts/DedupPanel.vue'
import ReplacePanel from './parts/ReplacePanel.vue'
import TimestampPanel from './parts/TimestampPanel.vue'
import UnicodePanel from './parts/UnicodePanel.vue'
import HashPanel from './parts/HashPanel.vue'

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

const activeTab = ref('codec')
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="70%"
    append-to-body
    custom-class="text-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">TEXT SUITE</p>
          <h3>文本与数据处理</h3>
          <p class="sub">编码、正则、CSV/JSON、排序、哈希一站完成</p>
        </div>
      </div>
    </template>
    <div class="text-tool">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="编码 / 解码" name="codec">
          <CodecPanel />
        </el-tab-pane>

        <el-tab-pane label="正则工具" name="regex">
          <RegexPanel />
        </el-tab-pane>

        <el-tab-pane label="JSON 工具" name="json">
          <JsonPanel />
        </el-tab-pane>

        <el-tab-pane label="CSV / JSON 转换" name="csv">
          <CsvPanel />
        </el-tab-pane>

        <el-tab-pane label="文本转换" name="transform">
          <TransformPanel />
        </el-tab-pane>

        <el-tab-pane label="去重 / 排序" name="dedup">
          <DedupPanel />
        </el-tab-pane>

        <el-tab-pane label="批量替换" name="replace">
          <ReplacePanel />
        </el-tab-pane>

        <el-tab-pane label="时间戳转换" name="timestamp">
          <TimestampPanel />
        </el-tab-pane>

        <el-tab-pane label="Unicode 工具" name="unicode">
          <UnicodePanel />
        </el-tab-pane>

        <el-tab-pane label="哈希计算" name="hash">
          <HashPanel />
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 使用全局深空玻璃主题样式 */
</style>
