<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  directory: '',
  stats: null
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', state.directory)
  if (dir) {
    state.directory = dir
  }
}

const runAnalyze = async () => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_directory_analyze', {
      directory: state.directory
    })
    if (ok) {
      state.stats = res.stats
      ElMessage.success(message || '分析完成')
    } else {
      ElMessage.error(message || '分析失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '分析失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>统计目录结构</h4>
      <p>展示文件数量、空间占用与扩展名 Top N</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="目录">
        <div class="field-row">
          <el-input v-model="state.directory" placeholder="选择目录" readonly />
          <el-button @click="selectDir">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runAnalyze">开始分析</el-button>
      </el-form-item>
    </el-form>
    <div v-if="state.stats" class="stats-panel">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="总大小">
          {{ state.stats.totalSize }}
        </el-descriptions-item>
        <el-descriptions-item label="文件数">
          {{ state.stats.fileCount }}
        </el-descriptions-item>
        <el-descriptions-item label="子目录数">
          {{ state.stats.dirCount }}
        </el-descriptions-item>
      </el-descriptions>
      <div class="stat-cols">
        <div>
          <h5>热门扩展名</h5>
          <ul>
            <li v-for="item in state.stats.topExtensions" :key="item.ext">
              {{ item.ext }} · {{ item.count }}
            </li>
          </ul>
        </div>
        <div>
          <h5>最大文件</h5>
          <ul>
            <li v-for="item in state.stats.largestFiles" :key="item.path">
              <span>{{ item.name }}</span>
              <span>{{ item.size }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stats-panel {
  margin-top: 18px;
}

.stat-cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 16px;
}

.stat-cols h5 {
  margin: 0 0 8px;
  color: var(--ppx-text-primary);
}

.stat-cols ul {
  margin: 0;
  padding-left: 16px;
  color: var(--ppx-text-secondary);
}
</style>
