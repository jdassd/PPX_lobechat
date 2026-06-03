<script setup>
import { computed, ref } from 'vue'

import ConvertPanel from './parts/ConvertPanel.vue'
import CompressPanel from './parts/CompressPanel.vue'
import CutPanel from './parts/CutPanel.vue'
import AudioPanel from './parts/AudioPanel.vue'
import FramesPanel from './parts/FramesPanel.vue'
import ConcatPanel from './parts/ConcatPanel.vue'
import InfoPanel from './parts/InfoPanel.vue'

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

const activeTab = ref('convert')
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="70%"
    append-to-body
    custom-class="video-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">VIDEO STUDIO</p>
          <h3>视频处理工具</h3>
          <p class="sub">格式转换、压缩、截取、音频与帧图导出</p>
        </div>
      </div>
    </template>
    <div class="video-tool">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="格式转换" name="convert">
          <ConvertPanel />
        </el-tab-pane>

        <el-tab-pane label="视频压缩" name="compress">
          <CompressPanel />
        </el-tab-pane>

        <el-tab-pane label="视频截取" name="cut">
          <CutPanel />
        </el-tab-pane>

        <el-tab-pane label="音频提取" name="audio">
          <AudioPanel />
        </el-tab-pane>

        <el-tab-pane label="帧图导出" name="frames">
          <FramesPanel />
        </el-tab-pane>

        <el-tab-pane label="视频合成" name="concat">
          <ConcatPanel />
        </el-tab-pane>

        <el-tab-pane label="视频信息" name="info">
          <InfoPanel />
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 使用全局深空玻璃主题样式 */
</style>
