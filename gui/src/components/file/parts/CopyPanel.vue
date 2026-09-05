<script setup>
import { useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = useDraft('file/parts/CopyPanel/state', {
  sourceDir: '',
  targetDir: '',
  keyword: '',
  extensions: '',
  recursive: true,
  conflictPolicy: 'skip',
  result: null
})

const parseExtensions = (value) =>
  value
    .split(',')
    .map((item) => item.trim().replace('.', ''))
    .filter(Boolean)

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const chooseDir = async (current = '') => {
  if (!ensurePyReady()) return null
  return callApiRaw('system_pySelectDirDialog', current)
}

const selectCopySource = async () => {
  const dir = await chooseDir(state.sourceDir)
  if (dir) state.sourceDir = dir
}

const selectCopyTarget = async () => {
  const dir = await chooseDir(state.targetDir)
  if (dir) state.targetDir = dir
}

const runCopy = async () => {
  if (!ensurePyReady()) return
  if (!state.sourceDir || !state.targetDir) {
    ElMessage.warning('请选择源目录和目标目录')
    return
  }
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('file_batch_copy', {
      sourceDir: state.sourceDir,
      targetDir: state.targetDir,
      keyword: state.keyword,
      extensions: parseExtensions(state.extensions || ''),
      recursive: state.recursive,
      conflictPolicy: state.conflictPolicy
    })
    if (ok) {
      state.result = res
      ElMessage.success(message || '复制完成')
    } else {
      ElMessage.error(message || '复制失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '复制失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>按规则复制文件</h4>
      <p>按关键字 / 扩展名筛选，自动复制到目标目录</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="源目录">
        <div class="field-row">
          <el-input v-model="state.sourceDir" placeholder="选择源目录" readonly />
          <el-button @click="selectCopySource">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="目标目录">
        <div class="field-row">
          <el-input v-model="state.targetDir" placeholder="选择目标目录" readonly />
          <el-button @click="selectCopyTarget">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="关键字">
        <el-input v-model="state.keyword" placeholder="可选" />
      </el-form-item>
      <el-form-item label="扩展名">
        <el-input v-model="state.extensions" placeholder="例如：pdf,jpg" />
      </el-form-item>
      <el-form-item label="选项">
        <el-checkbox v-model="state.recursive">包含子目录</el-checkbox>
        <el-select v-model="state.conflictPolicy" style="width: 200px">
          <el-option label="冲突跳过" value="skip" />
          <el-option label="覆盖同名文件" value="overwrite" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runCopy">开始复制</el-button>
      </el-form-item>
    </el-form>
    <el-descriptions v-if="state.result" :column="3" border size="small">
      <el-descriptions-item label="已复制">{{ state.result.copied }}</el-descriptions-item>
      <el-descriptions-item label="跳过">{{ state.result.skipped }}</el-descriptions-item>
      <el-descriptions-item label="总大小">{{ state.result.sizeText }}</el-descriptions-item>
    </el-descriptions>
  </section>
</template>
