<script setup>
import { useDraft } from '../../../utils/workspace'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)
const transactionId = ref('')
const undo = async () => {
  const response = await pyCall('file_classify_undo', { directory: state.directory, transactionId: transactionId.value })
  if (response.ok) {
    ElMessage.success(response.message)
    if (!response.data.skipped?.length) transactionId.value = ''
  } else ElMessage.error(response.message)
}

const state = useDraft('file/parts/ClassifyPanel/state', {
  directory: '',
  targetDir: '',
  mode: 'type',
  operation: 'copy',
  recursive: true,
  conflictPolicy: 'rename',
  result: [],
  summary: null,
  categories: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectClassifySource = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', state.directory)
  if (dir) {
    state.directory = dir
  }
}

const selectClassifyTarget = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', state.targetDir || state.directory)
  if (dir) {
    state.targetDir = dir
  }
}

const runClassify = async () => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择源目录')
    return
  }
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('file_auto_classify', {
      directory: state.directory,
      targetDir: state.targetDir,
      mode: state.mode,
      operation: state.operation,
      recursive: state.recursive,
      conflictPolicy: state.conflictPolicy
    })
    if (ok) {
      state.summary = res.summary
      state.result = res.operations || []
      if (!res.dryRun) transactionId.value = res.transactionId || ''
      state.categories = res.categories || []
      if (res.outputDir) {
        state.targetDir = res.outputDir
      }
      ElMessage.success(message || '分类完成')
    } else {
      ElMessage.error(message || '分类失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '分类失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>按类型 / 大小 / 日期整理</h4>
      <p>将目录中的文件批量复制/移动到分类子目录</p>
    </header>
    <el-form :model="state" label-width="130px" class="form-gap">
      <el-form-item label="源目录">
        <div class="field-row">
          <el-input v-model="state.directory" placeholder="选择待整理目录" readonly />
          <el-button @click="selectClassifySource">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="目标目录">
        <div class="field-row">
          <el-input v-model="state.targetDir" placeholder="留空则在源目录创建 _classified" readonly />
          <el-button @click="selectClassifyTarget">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="分类模式">
        <el-radio-group v-model="state.mode">
          <el-radio-button label="type">按文件类型</el-radio-button>
          <el-radio-button label="size">按大小区间</el-radio-button>
          <el-radio-button label="date">按日期（年月）</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="操作方式">
        <el-radio-group v-model="state.operation">
          <el-radio-button label="copy">复制</el-radio-button>
          <el-radio-button label="move">移动</el-radio-button>
        </el-radio-group>
        <el-checkbox v-model="state.recursive" style="margin-left: 12px"> 包含子目录 </el-checkbox>
      </el-form-item>
      <el-form-item label="冲突策略">
        <el-select v-model="state.conflictPolicy" style="width: 200px">
          <el-option label="重命名" value="rename" />
          <el-option label="覆盖" value="overwrite" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runClassify">执行分类</el-button>
      </el-form-item>
    </el-form>
    <el-button v-if="transactionId" @click="undo">撤销本次分类</el-button>
    <div v-if="state.summary" class="stats-panel">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="匹配文件">
          {{ state.summary.matched }}
        </el-descriptions-item>
        <el-descriptions-item label="已处理">
          {{ state.summary.processed }}
        </el-descriptions-item>
        <el-descriptions-item label="总大小">
          {{ state.summary.totalSize }}
        </el-descriptions-item>
      </el-descriptions>
    </div>
    <el-table v-if="state.categories.length" :data="state.categories" border size="small" style="margin-top: 16px">
      <el-table-column prop="label" label="分类" />
      <el-table-column prop="count" label="数量" width="140" />
    </el-table>
    <el-table v-if="state.result.length" :data="state.result.slice(0, 60)" border size="small" style="margin-top: 16px">
      <el-table-column prop="category" label="分类" width="140" />
      <el-table-column prop="from" label="源文件" show-overflow-tooltip />
      <el-table-column prop="to" label="目标地址" show-overflow-tooltip />
    </el-table>
  </section>
</template>

<style scoped>
.stats-panel {
  margin-top: 18px;
}

.form-gap {
  margin-top: 12px;
}
</style>
