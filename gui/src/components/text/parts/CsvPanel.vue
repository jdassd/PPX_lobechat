<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  direction: 'csv_to_json',
  file: null,
  delimiter: ',',
  outputDir: '',
  outputName: '',
  result: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runCsvJson = async () => {
  if (!ensurePyReady()) return
  if (!state.file) {
    ElMessage.warning('请选择文件')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('text_convert_csv_json', {
      direction: state.direction,
      file: state.file,
      delimiter: state.delimiter,
      outputDir: state.outputDir,
      outputName: state.outputName
    })
    if (ok) {
      state.result = res.file || ''
      ElMessage.success(message || '转换完成')
    } else {
      ElMessage.error(message || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    loading.value = false
  }
}

const selectCsvFile = async () => {
  if (!ensurePyReady()) return
  const filter = state.direction === 'csv_to_json' ? ['CSV 文件 (*.csv)'] : ['JSON 文件 (*.json)']
  const files = await callApiRaw('system_pyCreateFileDialog', filter)
  if (files?.length) {
    state.file = files[0]
  }
}

const selectCsvOutputDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', state.outputDir)
  if (dir) {
    state.outputDir = dir
  }
}

const openFile = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>结构化数据互转</h4>
      <p>CSV ↔ JSON，支持自定义分隔符与输出目录</p>
    </header>
    <el-form :model="state" label-width="130px" class="form-gap">
      <el-form-item label="方向">
        <el-radio-group v-model="state.direction">
          <el-radio-button label="csv_to_json">CSV → JSON</el-radio-button>
          <el-radio-button label="json_to_csv">JSON → CSV</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="源文件">
        <div class="field-row">
          <el-input :model-value="state.file?.path || ''" placeholder="尚未选择" readonly />
          <el-button @click="selectCsvFile">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="分隔符">
        <el-input v-model="state.delimiter" style="width: 120px" />
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="state.outputDir" placeholder="自动使用源目录" readonly />
          <el-button @click="selectCsvOutputDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出名称">
        <el-input v-model="state.outputName" placeholder="可选" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runCsvJson">开始转换</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="state.result"
      type="success"
      :closable="false"
      show-icon
    >
      <template #title>
        已输出：<a class="link" @click.prevent="openFile(state.result)">{{ state.result }}</a>
      </template>
    </el-alert>
  </section>
</template>

<style scoped>
.form-gap {
  margin-top: 12px;
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
