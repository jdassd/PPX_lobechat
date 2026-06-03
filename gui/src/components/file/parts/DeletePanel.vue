<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = reactive({
  directory: '',
  keyword: '',
  extensions: '',
  recursive: true,
  deletePolicy: 'recycle',
  dryRun: true,
  preview: [],
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

const selectRemoveDir = async () => {
  const dir = await chooseDir(state.directory)
  if (dir) state.directory = dir
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const runDelete = async () => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_batch_delete', {
      directory: state.directory,
      keyword: state.keyword,
      extensions: parseExtensions(state.extensions || ''),
      recursive: state.recursive,
      deletePolicy: state.deletePolicy,
      dryRun: state.dryRun
    })
    if (ok) {
      state.preview = res.preview || []
      state.summary = res
      ElMessage.success(message || (state.dryRun ? '预览完成' : '删除完成'))
    } else {
      ElMessage.error(message || '删除失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '删除失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>按条件删除文件</h4>
      <p>支持先预览，再执行永久删除或移动到回收站</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="目录">
        <div class="field-row">
          <el-input v-model="state.directory" placeholder="选择目录" readonly />
          <el-button @click="selectRemoveDir">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="关键字">
        <el-input v-model="state.keyword" placeholder="可选" />
      </el-form-item>
      <el-form-item label="扩展名">
        <el-input v-model="state.extensions" placeholder="如：log,tmp" />
      </el-form-item>
      <el-form-item label="选项">
        <el-checkbox v-model="state.recursive">包含子目录</el-checkbox>
        <el-radio-group v-model="state.deletePolicy">
          <el-radio-button label="recycle">移动到回收站</el-radio-button>
          <el-radio-button label="permanent">永久删除</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="预览模式">
        <el-switch v-model="state.dryRun" active-text="仅预览" inactive-text="直接删除" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runDelete">
          {{ state.dryRun ? '预览删除列表' : '立即删除' }}
        </el-button>
      </el-form-item>
    </el-form>
    <el-table
      v-if="state.preview.length"
      :data="state.preview"
      border
      size="small"
      style="margin-top: 16px"
    >
      <el-table-column label="待删除文件">
        <template #default="scope">
          <a class="link" @click.prevent="openPath(scope.row)">{{ scope.row }}</a>
        </template>
      </el-table-column>
    </el-table>
    <el-descriptions
      v-if="state.summary && !state.dryRun"
      :column="2"
      border
      size="small"
      style="margin-top: 16px"
    >
      <el-descriptions-item label="删除数量">{{ state.summary.deleted }}</el-descriptions-item>
      <el-descriptions-item label="释放空间">{{ state.summary.sizeText }}</el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<style scoped>
.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
