<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

import FileSelector from '../../shared/FileSelector.vue'
import ResultTable from '../../shared/ResultTable.vue'

const props = defineProps({
  supportedFormats: {
    type: Object,
    required: true
  }
})

const loading = ref(false)

const form = reactive({
  files: [],
  watermarkType: 'text',
  text: '',
  fontSize: 32,
  color: '#ffffff',
  opacity: 60,
  position: 'bottom-right',
  tile: false,
  tileSpacing: 80,
  rotation: 0,
  watermarkImage: null,
  scalePercent: 30,
  outputDir: '',
  generatedDir: '',
  result: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectImages = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (files?.length) {
    form.files = files
  }
}

const selectWatermarkImage = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (files?.length) {
    form.watermarkImage = files[0]
  }
}

const clearWatermarkImage = () => {
  form.watermarkImage = null
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) {
    form.outputDir = dir
  }
}

const removeFile = (file) => {
  form.files = form.files.filter((item) => item !== file)
}

const pickPaths = (files = []) => files.map((item) => item?.path || item)

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const openDir = () => {
  const dir = form.outputDir || form.generatedDir
  if (dir) {
    openPath(dir)
    return
  }
  const fallback = form.result?.[0]
  if (fallback) {
    openPath(fallback)
  }
}

const runWatermark = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  if (form.watermarkType === 'text' && !form.text.trim()) {
    ElMessage.warning('请输入水印文字')
    return
  }
  if (form.watermarkType === 'image' && !form.watermarkImage) {
    ElMessage.warning('请选择水印图片')
    return
  }
  loading.value = true
  try {
    const payload = {
      files: pickPaths(form.files),
      watermarkType: form.watermarkType,
      text: form.text,
      fontSize: form.fontSize,
      color: form.color,
      opacity: form.opacity,
      position: form.position,
      tile: form.tile,
      tileSpacing: form.tileSpacing,
      rotation: form.rotation,
      watermarkImage: form.watermarkImage?.path,
      scalePercent: form.scalePercent,
      outputDir: form.outputDir
    }
    const { ok, data: res, message } = await pyCall('image_add_watermark', payload)
    if (ok) {
      form.result = res.files || []
      form.generatedDir = res.outputDir || form.outputDir
      ElMessage.success(message || '水印已添加')
    } else {
      ElMessage.error(message || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>批量添加水印</h4>
      <p>支持文字与图片水印，九宫格定位与透明度控制</p>
    </header>
    <FileSelector
      label="待处理图片"
      :files="form.files"
      :removable="true"
      @select="selectImages"
      @remove="removeFile"
    />
    <el-form :model="form" label-width="110px" class="form-block">
      <el-form-item label="水印类型">
        <el-radio-group v-model="form.watermarkType">
          <el-radio-button label="text">文字</el-radio-button>
          <el-radio-button label="image">图片</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <template v-if="form.watermarkType === 'text'">
        <el-form-item label="文字内容">
          <el-input
            v-model="form.text"
            placeholder="输入水印文字，可换行"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
        <div class="watermark-config">
          <el-form-item label="字号">
            <el-input-number v-model="form.fontSize" :min="8" :max="200" />
          </el-form-item>
          <el-form-item label="颜色">
            <el-color-picker v-model="form.color" />
          </el-form-item>
          <el-form-item label="透明度 (%)">
            <el-slider v-model="form.opacity" :min="5" :max="100" show-input />
          </el-form-item>
        </div>
      </template>
      <template v-else>
        <el-form-item label="水印图片">
          <div class="field-row">
            <el-input :model-value="form.watermarkImage?.path || ''" placeholder="点击选择图片" readonly />
            <el-button @click="selectWatermarkImage">选择</el-button>
            <el-button text type="danger" @click="clearWatermarkImage">清除</el-button>
          </div>
        </el-form-item>
        <el-form-item label="尺寸比例 (%)">
          <el-slider v-model="form.scalePercent" :min="5" :max="80" show-input />
        </el-form-item>
        <el-form-item label="透明度 (%)">
          <el-slider v-model="form.opacity" :min="5" :max="100" show-input />
        </el-form-item>
      </template>
      <el-form-item label="平铺 / 间距">
        <div class="field-row field-row--wrap">
          <el-switch
            v-model="form.tile"
            active-text="按间距平铺"
            inactive-text="单个水印"
          />
          <el-input-number
            v-model="form.tileSpacing"
            :min="20"
            :max="600"
            :step="10"
            :disabled="!form.tile"
          />
          <span>px</span>
        </div>
      </el-form-item>
      <el-form-item label="旋转角度">
        <el-slider
          v-model="form.rotation"
          :min="-90"
          :max="90"
          :step="1"
          show-input
        />
      </el-form-item>              <el-form-item label="位置">
        <el-select v-model="form.position" style="width: 220px">
          <el-option label="左上角" value="top-left" />
          <el-option label="右上角" value="top-right" />
          <el-option label="居中" value="center" />
          <el-option label="左下角" value="bottom-left" />
          <el-option label="右下角" value="bottom-right" />
        </el-select>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="自动创建" readonly />
          <el-button @click="selectDir">选目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runWatermark">开始处理</el-button>
      </el-form-item>
    </el-form>
    <ResultTable
      v-if="form.result.length"
      title="输出文件"
      :items="form.result.map((path) => ({ path }))"
      :columns="[{ label: '文件路径', prop: 'path' }]"
    >
      <template #actions>
        <el-button text type="primary" @click="openDir">打开目录</el-button>
      </template>
    </ResultTable>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}

.watermark-config {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}
</style>
