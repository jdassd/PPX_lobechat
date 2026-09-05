<script setup>
import { useDraft } from '../../../utils/workspace'
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const loading = ref(false)

const state = useDraft('file/parts/DeletePanel/state', {
  directory: '',
  keyword: '',
  extensions: '',
  recursive: true,
  preview: [],
  summary: null
})
const previewReady = ref(false)
const executed = ref(false)

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

watch(
  () => [state.directory, state.keyword, state.extensions, state.recursive],
  () => {
    previewReady.value = false
    executed.value = false
  }
)

const runDelete = async (dryRun = true) => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  if (!dryRun && !previewReady.value) {
    ElMessage.warning('请先预览并确认待删除列表')
    return
  }
  if (!dryRun) {
    try {
      await ElMessageBox.confirm(`将 ${state.preview.length} 个文件移入 .ppx_recycle，可手动恢复。是否继续？`, '确认安全删除', {
        confirmButtonText: '移入回收目录',
        cancelButtonText: '取消',
        type: 'warning'
      })
    } catch {
      return
    }
  }
  loading.value = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('file_batch_delete', {
      directory: state.directory,
      keyword: state.keyword,
      extensions: parseExtensions(state.extensions || ''),
      recursive: state.recursive,
      deletePolicy: 'recycle',
      dryRun
    })
    if (ok) {
      state.preview = res.preview || []
      state.summary = res
      previewReady.value = dryRun && state.preview.length > 0
      executed.value = !dryRun
      ElMessage.success(message || (dryRun ? '预览完成' : '已移入回收目录'))
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
      <h4>按条件安全删除文件</h4>
      <p>必须先预览；执行后文件会移入当前目录的 .ppx_recycle，可手动恢复</p>
    </header>
    <el-alert title="v2.0 已移除永久删除。源目录和 .ppx_recycle 目录不会被纳入匹配。" type="info" :closable="false" show-icon />
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
      </el-form-item>
      <el-form-item>
        <el-button type="primary" plain :loading="loading" @click="runDelete(true)">1. 预览删除列表</el-button>
        <el-button type="danger" :loading="loading" :disabled="!previewReady" @click="runDelete(false)">2. 移入回收目录</el-button>
      </el-form-item>
    </el-form>
    <el-table v-if="state.preview.length" :data="state.preview" border size="small" style="margin-top: 16px">
      <el-table-column label="待删除文件">
        <template #default="scope">
          <a class="link" @click.prevent="openPath(scope.row)">{{ scope.row }}</a>
        </template>
      </el-table-column>
    </el-table>
    <el-descriptions v-if="state.summary && executed" :column="2" border size="small" style="margin-top: 16px">
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
