<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

import ResultTable from '../../shared/ResultTable.vue'

const loading = ref(false)

const state = reactive({
  directory: '',
  keyword: '',
  extensions: '',
  recursive: true,
  minSize: 0,
  maxSize: 0,
  result: []
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

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const runSearch = async () => {
  if (!ensurePyReady()) return
  if (!state.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  loading.value = true
  try {
    const extensions = state.extensions
      .split(',')
      .map((item) => item.trim().replace('.', ''))
      .filter(Boolean)
    const { ok, data: res, message } = await pyCall('file_search', {
      directory: state.directory,
      keyword: state.keyword,
      extensions,
      recursive: state.recursive,
      minSize: state.minSize,
      maxSize: state.maxSize
    })
    if (ok) {
      state.result = res.items || []
      ElMessage.success(message || '搜索完成')
    } else {
      ElMessage.error(message || '搜索失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '搜索失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>快速查找目录内文件</h4>
      <p>支持扩展名筛选、大小范围与递归搜索</p>
    </header>
    <el-form :model="state" label-width="120px">
      <el-form-item label="目录">
        <div class="field-row">
          <el-input v-model="state.directory" placeholder="选择要搜索的目录" readonly />
          <el-button @click="selectDir">选择</el-button>
        </div>
      </el-form-item>
      <el-form-item label="关键字">
        <el-input v-model="state.keyword" placeholder="支持模糊匹配" clearable />
      </el-form-item>
      <el-form-item label="扩展名">
        <el-input
          v-model="state.extensions"
          placeholder="以逗号分隔，如：pdf,jpg,docx"
        />
      </el-form-item>
      <el-form-item label="大小 (B)">
        <div class="field-row">
          <el-input-number v-model="state.minSize" :min="0" />
          <span>~</span>
          <el-input-number v-model="state.maxSize" :min="0" />
        </div>
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="state.recursive">包含子目录</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="runSearch">开始搜索</el-button>
      </el-form-item>
    </el-form>
    <ResultTable
      v-if="state.result.length"
      title="搜索结果"
      :description="`共 ${state.result.length} 条`"
      :items="state.result"
      :columns="[
        { label: '文件名', prop: 'name', width: 200 },
        { label: '路径', prop: 'path' },
        { label: '大小', prop: 'sizeText', width: 120 }
      ]"
    >
      <template #actions>
        <el-button text type="primary" @click="openPath(state.directory)">
          打开目录
        </el-button>
      </template>
    </ResultTable>
  </section>
</template>
