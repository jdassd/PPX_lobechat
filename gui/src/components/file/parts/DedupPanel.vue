<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  directory: '',
  extensions: '',
  recursive: true,
  mode: 'content',
  result: [],
  summary: null
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

const selectDedupDir = async () => {
  const dir = await chooseDir(state.directory)
  if (dir) state.directory = dir
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const runDedup = async () => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_deduplicate', {
      directory: state.directory,
      mode: state.mode,
      extensions: parseExtensions(state.extensions || ''),
      recursive: state.recursive
    })
    if (ok) {
      state.result = res.groups || []
      state.summary = res
      ElMessage.success(message || '扫描完成')
    } else {
      ElMessage.error(message || '扫描失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '扫描失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>重复文件检测</h4>
      <p>按内容或文件名扫描重复项，展示可释放空间</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="目录">
        <div class="field-row">
          <el-input v-model="state.directory" placeholder="选择目录" readonly />
          <el-button @click="selectDedupDir">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="扩展名">
        <el-input v-model="state.extensions" placeholder="可选，如：zip,iso" />
      </el-form-item>
      <el-form-item label="模式">
        <el-radio-group v-model="state.mode">
          <el-radio-button label="content">按内容 (哈希)</el-radio-button>
          <el-radio-button label="name">按文件名</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="state.recursive">包含子目录</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runDedup">开始扫描</el-button>
      </el-form-item>
    </el-form>
    <el-descriptions
      v-if="state.summary"
      :column="2"
      border
      size="small"
    >
      <el-descriptions-item label="重复分组">{{ state.summary.totalGroups }}</el-descriptions-item>
      <el-descriptions-item label="可释放空间">{{ state.summary.spaceSaved }}</el-descriptions-item>
    </el-descriptions>
    <el-table
      v-if="state.result.length"
      :data="state.result"
      border
      size="small"
      style="margin-top: 12px"
    >
      <el-table-column label="重复文件">
        <template #default="scope">
          <ul class="dedup-list">
            <li v-for="file in scope.row.files" :key="file">
              <a class="link" @click.prevent="openPath(file)">{{ file }}</a>
            </li>
          </ul>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<style scoped>
.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}

.dedup-list {
  list-style: none;
  padding-left: 0;
  margin: 0;
}

.dedup-list li {
  margin-bottom: 4px;
}
</style>
