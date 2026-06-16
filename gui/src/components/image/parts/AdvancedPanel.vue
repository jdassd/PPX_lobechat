<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const props = defineProps({
  supportedFormats: {
    type: Object,
    required: true
  }
})

const loading = ref(false)

const concat = reactive({
  files: [],
  direction: 'horizontal',
  columns: 2,
  spacing: 24,
  align: 'center',
  background: '#ffffff',
  outputFormat: 'png',
  quality: 90,
  outputDir: '',
  result: ''
})

const rename = reactive({
  files: [],
  mode: 'sequence',
  prefix: 'img_',
  suffix: '',
  pattern: '{name}_{index}',
  digits: 4,
  startIndex: 1,
  keepExtension: true,
  copyMode: false,
  outputDir: '',
  dryRun: true,
  operations: [],
  skipped: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectImages = async (target) => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', props.supportedFormats.imageFilter)
  if (files?.length) {
    sections[target].files = files
  }
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', sections[target].outputDir)
  if (dir) {
    sections[target].outputDir = dir
  }
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const pickPaths = (files = []) => files.map((item) => item?.path || item)

const sections = { concat, rename }

const runConcat = async () => {
  if (!ensurePyReady()) return
  if (!concat.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('image_concat', {
      files: pickPaths(concat.files),
      direction: concat.direction,
      columns: concat.columns,
      spacing: concat.spacing,
      align: concat.align,
      background: concat.background,
      outputFormat: concat.outputFormat,
      quality: concat.quality,
      outputDir: concat.outputDir
    })
    if (ok) {
      concat.result = res.file || ''
      concat.outputDir = res.outputDir || concat.outputDir
      ElMessage.success(message || '拼接完成')
    } else {
      ElMessage.error(message || '拼接失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '拼接失败')
  } finally {
    loading.value = false
  }
}

const runRename = async () => {
  if (!ensurePyReady()) return
  if (!rename.files.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('image_batch_rename', {
      files: pickPaths(rename.files),
      mode: rename.mode,
      prefix: rename.prefix,
      suffix: rename.suffix,
      pattern: rename.pattern,
      digits: rename.digits,
      startIndex: rename.startIndex,
      keepExtension: rename.keepExtension,
      copyMode: rename.copyMode,
      outputDir: rename.outputDir,
      dryRun: rename.dryRun
    })
    if (ok) {
      rename.operations = res.operations || []
      rename.skipped = res.skipped || []
      if (res.outputDir) {
        rename.outputDir = res.outputDir
      }
      rename.dryRun = !!res.dryRun
      ElMessage.success(message || (rename.dryRun ? '预览生成' : '重命名完成'))
    } else {
      ElMessage.error(message || '重命名失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '重命名失败')
  } finally {
    loading.value = false
  }
}

// 当支持格式列表更新后，确保拼接输出格式仍然合法
watch(
  () => props.supportedFormats.raster,
  (options) => {
    if (!options?.length) return
    const allowed = new Set(options.map((item) => item.value))
    if (!allowed.has(concat.outputFormat)) {
      concat.outputFormat = options[0].value
    }
  },
  { immediate: true }
)
</script>

<template>
  <div>
    <section class="panel advanced-grid">
      <div class="advanced-card">
        <header>
          <h4>图片拼接</h4>
          <p>批量横向 / 纵向 / 网格拼接，支持自定义背景与间距</p>
        </header>
        <el-form :model="concat" label-width="110px">
          <el-form-item label="待处理">
            <div class="field-row">
              <el-button @click="selectImages('concat')">添加图片</el-button>
              <el-tag v-if="concat.files.length" type="info" effect="plain">
                已选 {{ concat.files.length }} 个文件
              </el-tag>
              <el-tag v-else type="warning" effect="plain">尚未选择</el-tag>
            </div>
          </el-form-item>
          <el-form-item label="排列方式">
            <el-radio-group v-model="concat.direction">
              <el-radio-button label="horizontal">横向</el-radio-button>
              <el-radio-button label="vertical">纵向</el-radio-button>
              <el-radio-button label="grid">网格</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="concat.direction === 'grid'" label="列数">
            <el-input-number v-model="concat.columns" :min="1" :max="6" />
          </el-form-item>
          <el-form-item label="对齐 / 间距">
            <div class="field-row field-row--wrap">
              <el-select v-model="concat.align" style="width: 140px">
                <el-option label="顶部" value="top" />
                <el-option label="居中" value="center" />
                <el-option label="底部" value="bottom" />
              </el-select>
              <el-input-number v-model="concat.spacing" :min="0" :max="200" />
            </div>
          </el-form-item>
          <el-form-item label="背景颜色">
            <el-color-picker v-model="concat.background" />
          </el-form-item>
          <el-form-item label="输出格式">
            <div class="field-row">
              <el-select v-model="concat.outputFormat" style="width: 120px">
                <el-option
                  v-for="item in supportedFormats.raster"
                  :key="`concat-format-${item.value}`"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
              <el-input-number v-model="concat.quality" :min="30" :max="100" />
            </div>
          </el-form-item>
          <el-form-item label="输出目录">
            <div class="field-row">
              <el-input v-model="concat.outputDir" placeholder="留空自动创建" readonly />
              <el-button @click="selectDir('concat')">选择目录</el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="runConcat">
              执行拼接
            </el-button>
          </el-form-item>
        </el-form>
        <div v-if="concat.result" class="result-block">
          <p class="result-title">输出文件</p>
          <el-tag type="info" effect="plain" @click="openPath(concat.result)">
            {{ concat.result }}
          </el-tag>
        </div>
      </div>
      <div class="advanced-card">
        <header>
          <h4>批量重命名</h4>
          <p>支持序号 / 时间戳 / 自定义模板，可预览再执行</p>
        </header>
        <el-form :model="rename" label-width="110px">
          <el-form-item label="待处理">
            <div class="field-row">
              <el-button @click="selectImages('rename')">添加图片</el-button>
              <el-tag v-if="rename.files.length" effect="plain" type="info">
                已选 {{ rename.files.length }} 个
              </el-tag>
              <el-tag v-else effect="plain" type="warning">尚未选择</el-tag>
            </div>
          </el-form-item>
          <el-form-item label="模式">
            <el-radio-group v-model="rename.mode" size="small">
              <el-radio-button label="sequence">序号</el-radio-button>
              <el-radio-button label="timestamp">时间戳</el-radio-button>
              <el-radio-button label="custom">自定义</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="rename.mode === 'custom'" label="模板">
            <el-input
              v-model="rename.pattern"
              placeholder="可使用 {name} {index} {timestamp}"
            />
          </el-form-item>
          <el-form-item v-else label="前后缀">
            <div class="field-row field-row--wrap">
              <el-input v-model="rename.prefix" placeholder="前缀" />
              <el-input v-model="rename.suffix" placeholder="后缀" />
            </div>
          </el-form-item>
          <el-form-item label="序号配置">
            <div class="field-row field-row--wrap">
              <el-input-number v-model="rename.startIndex" :min="1" />
              <el-input-number v-model="rename.digits" :min="2" :max="6" />
            </div>
          </el-form-item>
          <el-form-item label="选项">
            <div class="toggle-row">
              <el-checkbox v-model="rename.keepExtension">保留原扩展名</el-checkbox>
              <el-checkbox v-model="rename.copyMode">复制到新目录</el-checkbox>
              <el-checkbox v-model="rename.dryRun">仅预览</el-checkbox>
            </div>
          </el-form-item>
          <el-form-item label="输出目录">
            <div class="field-row">
              <el-input v-model="rename.outputDir" placeholder="可选" readonly />
              <el-button @click="selectDir('rename')">选择目录</el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="runRename">
              {{ rename.dryRun ? '生成预览' : '开始重命名' }}
            </el-button>
          </el-form-item>
        </el-form>
        <div v-if="rename.operations.length" class="result-block">
          <p class="result-title">
            {{ rename.dryRun ? '预览结果' : '重命名记录' }}（仅展示前 8 条）
          </p>
          <el-table :data="rename.operations.slice(0, 8)" size="small" border>
            <el-table-column prop="from" label="原文件" show-overflow-tooltip />
            <el-table-column prop="to" label="新文件" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

/* 高级批量处理 */
.advanced-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.advanced-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-lg);
  padding: 16px;
  background: var(--ppx-glass-bg);
}

.advanced-card:hover {
  border-color: var(--ppx-glass-border-hover);
  background: var(--ppx-glass-bg-hover);
}
</style>
