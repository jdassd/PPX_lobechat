<template>
  <div>
    <el-alert v-if="!isWindows" type="info" show-icon :closable="false" class="helper-hint">
      C盘专清仅支持 Windows 系统
    </el-alert>
    <template v-else>
      <el-alert type="info" show-icon :closable="false" class="helper-hint">
        已支持文件级管理：按类型筛选、按大小/时间排序、批量清理、加入白名单、打开文件所在目录。
      </el-alert>

      <div class="toolbar">
        <el-button type="primary" :loading="cDriveCleanState.scanning" @click="scanCDriveClean">
          <template #icon><el-icon><Search /></el-icon></template>
          扫描 C盘可清理项
        </el-button>
        <el-button :disabled="!cDriveCleanState.selectedFiles.length" @click="addSelectedFilesToWhitelist">
          加入白名单 ({{ cDriveCleanState.selectedFiles.length }})
        </el-button>
        <el-select v-model="cDriveCleanState.cleanMode" style="width: 150px">
          <el-option label="永久删除" value="permanent" />
          <el-option label="移到回收站" value="recycle" />
        </el-select>
        <el-button
          type="danger"
          :loading="cDriveCleanState.cleaning"
          :disabled="!cDriveCleanState.selectedFiles.length"
          @click="cleanCDriveFiles"
        >
          <template #icon><el-icon><Delete /></el-icon></template>
          清理选中文件 ({{ cDriveCleanState.selectedFiles.length }})
        </el-button>
        <div class="toolbar-info" v-if="cDriveCleanState.totalSizeText">
          <span>总计可清理: <strong>{{ cDriveCleanState.totalSizeText }}</strong></span>
        </div>
      </div>

      <div class="toolbar">
        <el-input v-model.trim="cDriveCleanState.fileKeyword" placeholder="文件名关键字" clearable class="keyword-input" />
        <el-select v-model="cDriveCleanState.fileExtFilter" clearable placeholder="按类型筛选" style="width: 170px">
          <el-option v-for="ext in cDriveFileExtensions" :key="ext" :label="ext" :value="ext" />
        </el-select>
        <el-select v-model="cDriveCleanState.fileSort" style="width: 170px">
          <el-option label="按大小降序" value="size_desc" />
          <el-option label="按大小升序" value="size_asc" />
          <el-option label="按时间降序" value="time_desc" />
          <el-option label="按时间升序" value="time_asc" />
        </el-select>
        <el-button @click="selectAllVisibleCDriveFiles">全选当前可见</el-button>
      </div>

      <el-table
        ref="cDriveCategoryTableRef"
        :data="cDriveCleanState.items"
        v-loading="cDriveCleanState.scanning"
        border
        size="small"
        max-height="220"
        empty-text="点击“扫描 C盘可清理项”开始扫描"
        @selection-change="onCDriveCleanSelectionChange"
        @row-click="onCDriveCategoryRowClick"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="类别" min-width="140" />
        <el-table-column label="风险" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.risk === 'high'" size="small" type="danger">高</el-tag>
            <el-tag v-else-if="row.risk === 'medium'" size="small" type="warning">中</el-tag>
            <el-tag v-else size="small" type="success">低</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column prop="fileCount" label="文件数" width="90" />
        <el-table-column prop="sizeText" label="大小" width="120" />
        <el-table-column prop="path" label="路径" min-width="220" show-overflow-tooltip />
      </el-table>

      <el-table
        ref="cDriveFileTableRef"
        :data="filteredCDriveFiles"
        border
        size="small"
        max-height="300"
        empty-text="点击上方分类查看文件详情"
        @selection-change="onCDriveFileSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="ext" label="类型" width="90" />
        <el-table-column prop="sizeText" label="大小" width="120" />
        <el-table-column prop="modifiedAtText" label="修改时间" width="170" />
        <el-table-column prop="path" label="路径" min-width="280" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openPath(row.path)">打开</el-button>
            <el-button size="small" text @click="openFolderOfPath(row.path)">目录</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="toolbar" style="margin-top: 10px;">
        <el-input v-model.trim="cDriveCleanState.ruleForm.name" placeholder="自定义规则名称" style="width: 180px" />
        <el-input v-model.trim="cDriveCleanState.ruleForm.path" placeholder="规则路径（如 C:/Logs）" class="keyword-input" />
        <el-button @click="pickCDriveRulePath">选择路径</el-button>
        <el-input v-model.trim="cDriveCleanState.ruleForm.patterns" placeholder="匹配模式，如 *.log,*.tmp" style="width: 200px" />
        <el-input v-model.trim="cDriveCleanState.ruleForm.extFilters" placeholder="扩展名过滤，如 .log,.tmp" style="width: 200px" />
        <el-input v-model.number="cDriveCleanState.ruleForm.minSizeMB" placeholder="最小大小(MB)" style="width: 130px" />
        <el-input v-model.number="cDriveCleanState.ruleForm.olderThanDays" placeholder="至少多少天" style="width: 130px" />
        <el-button type="primary" @click="saveCDriveRule">保存规则</el-button>
      </div>

      <el-table :data="cDriveCleanState.customRules" border size="small" max-height="180" empty-text="暂无自定义规则">
        <el-table-column prop="name" label="规则名" min-width="140" />
        <el-table-column prop="path" label="路径" min-width="220" show-overflow-tooltip />
        <el-table-column label="条件" min-width="260">
          <template #default="{ row }">
            <span>patterns: {{ (row.patterns || []).join(',') || '*' }}</span>
            <span style="margin-left: 8px;">ext: {{ (row.extFilters || []).join(',') || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text type="danger" @click="removeCDriveRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="cDriveCleanState.cleanResult" class="clean-result">
        <el-alert
          :type="cDriveCleanState.cleanResult.errors?.length ? 'warning' : 'success'"
          show-icon
          :closable="false"
        >
          <template #title>
            已清理 {{ cDriveCleanState.cleanResult.clearedCount }} 个项目，释放
            {{ cDriveCleanState.cleanResult.clearedSizeText }}
          </template>
          <template #default v-if="cDriveCleanState.cleanResult.errors?.length">
            <div v-for="err in cDriveCleanState.cleanResult.errors" :key="err">{{ err }}</div>
          </template>
        </el-alert>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi as pyCall, callApiRaw } from '@/utils/pyapi'
import { Search, Delete } from '@element-plus/icons-vue'

const props = defineProps({
  apiReady: {
    type: Boolean,
    default: false
  },
  isWindows: {
    type: Boolean,
    default: false
  }
})

const cDriveCategoryTableRef = ref(null)
const cDriveFileTableRef = ref(null)

const cDriveCleanState = reactive({
  scanning: false,
  cleaning: false,
  items: [],
  selectedCategories: [],
  selectedCategory: '',
  selectedFiles: [],
  totalSizeText: '',
  cleanResult: null,
  cleanMode: 'permanent',
  fileKeyword: '',
  fileExtFilter: '',
  fileSort: 'size_desc',
  whitelist: [],
  customRules: [],
  ruleForm: {
    name: '',
    path: '',
    patterns: '*.log,*.tmp',
    extFilters: '.log,.tmp',
    minSizeMB: 0,
    olderThanDays: 0
  }
})

const selectedCategoryFiles = computed(() => {
  const row = cDriveCleanState.items.find(item => item.category === cDriveCleanState.selectedCategory)
  return row?.files || []
})

const cDriveFileExtensions = computed(() => {
  const set = new Set()
  selectedCategoryFiles.value.forEach(file => {
    const ext = (file.ext || '').trim()
    if (ext) set.add(ext)
  })
  return Array.from(set).sort((a, b) => a.localeCompare(b))
})

const filteredCDriveFiles = computed(() => {
  let list = [...selectedCategoryFiles.value]
  const keyword = (cDriveCleanState.fileKeyword || '').trim().toLowerCase()
  if (keyword) {
    list = list.filter(item => String(item.name || '').toLowerCase().includes(keyword))
  }
  if (cDriveCleanState.fileExtFilter) {
    list = list.filter(item => (item.ext || '') === cDriveCleanState.fileExtFilter)
  }
  const sorter = cDriveCleanState.fileSort
  list.sort((a, b) => {
    if (sorter === 'size_asc') return (a.size || 0) - (b.size || 0)
    if (sorter === 'size_desc') return (b.size || 0) - (a.size || 0)
    if (sorter === 'time_asc') return (a.modifiedAt || 0) - (b.modifiedAt || 0)
    if (sorter === 'time_desc') return (b.modifiedAt || 0) - (a.modifiedAt || 0)
    return 0
  })
  return list
})

const onCDriveCleanSelectionChange = (selection) => {
  cDriveCleanState.selectedCategories = selection.map(item => item.category)
}

const onCDriveCategoryRowClick = (row) => {
  cDriveCleanState.selectedCategory = row?.category || ''
  cDriveCleanState.selectedFiles = []
}

const onCDriveFileSelectionChange = (selection) => {
  cDriveCleanState.selectedFiles = selection || []
}

const openPath = (path) => {
  if (!path || !window.pywebview?.api?.system_pyOpenFile) return
  callApiRaw('system_pyOpenFile', path)
}

const openFolderOfPath = (path) => {
  if (!path || !window.pywebview?.api?.system_pyOpenFile) return
  const dir = path.replace(/\\[^\\]+$/, '')
  callApiRaw('system_pyOpenFile', dir)
}

const selectAllVisibleCDriveFiles = () => {
  if (!cDriveFileTableRef.value) return
  cDriveFileTableRef.value.clearSelection()
  filteredCDriveFiles.value.forEach(row => {
    cDriveFileTableRef.value.toggleRowSelection(row, true)
  })
}

const loadCDriveCustomRules = async () => {
  if (!window.pywebview?.api?.system_listCDriveCustomRules) return
  try {
    const { ok, data: res } = await pyCall('system_listCDriveCustomRules')
    if (ok) {
      cDriveCleanState.customRules = res.rules || []
    }
  } catch {
    // ignore
  }
}

const scanCDriveClean = async () => {
  if (!props.apiReady || !window.pywebview?.api?.system_scanCDriveClean) {
    ElMessage.warning('当前环境不支持 C盘专清功能')
    return
  }
  cDriveCleanState.scanning = true
  cDriveCleanState.cleanResult = null
  try {
    const { ok, data: res } = await pyCall('system_scanCDriveClean')
    if (ok) {
      cDriveCleanState.items = res.items || []
      cDriveCleanState.totalSizeText = res.totalSizeText || ''
      if (!cDriveCleanState.selectedCategory && cDriveCleanState.items.length) {
        cDriveCleanState.selectedCategory = cDriveCleanState.items[0].category
      }
      await loadCDriveCustomRules()
    } else {
      ElMessage.error(res?.message || '扫描失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '扫描失败')
  } finally {
    cDriveCleanState.scanning = false
  }
}

const cleanCDriveClean = async () => {
  if (!cDriveCleanState.selectedCategories.length) {
    ElMessage.warning('请先选择要清理的类别')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要清理选中的 ${cDriveCleanState.selectedCategories.length} 个类别吗？此操作不可撤销。`,
      '确认清理',
      {
        confirmButtonText: '清理',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }
  cDriveCleanState.cleaning = true
  try {
    const { ok, data: res } = await pyCall('system_cleanCDriveClean', {
      categories: cDriveCleanState.selectedCategories,
      mode: cDriveCleanState.cleanMode
    })
    if (ok) {
      cDriveCleanState.cleanResult = res
      ElMessage.success(`已清理 ${res.clearedCount} 个项目，释放 ${res.clearedSizeText}`)
      await scanCDriveClean()
    } else {
      ElMessage.error(res?.message || '清理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '清理失败')
  } finally {
    cDriveCleanState.cleaning = false
  }
}

const cleanCDriveFiles = async () => {
  if (!cDriveCleanState.selectedFiles.length) {
    ElMessage.warning('请先选择要清理的文件')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要清理选中的 ${cDriveCleanState.selectedFiles.length} 个文件吗？`,
      '确认清理文件',
      {
        confirmButtonText: '清理',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }
  cDriveCleanState.cleaning = true
  try {
    const { ok, data: res } = await pyCall('system_cleanCDriveFiles', {
      filePaths: cDriveCleanState.selectedFiles.map(item => item.path),
      mode: cDriveCleanState.cleanMode
    })
    if (ok) {
      cDriveCleanState.cleanResult = res
      ElMessage.success(`已清理 ${res.clearedCount} 个文件，释放 ${res.clearedSizeText}`)
      await scanCDriveClean()
    } else {
      ElMessage.error(res?.message || '清理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '清理失败')
  } finally {
    cDriveCleanState.cleaning = false
  }
}

const addSelectedFilesToWhitelist = async () => {
  if (!cDriveCleanState.selectedFiles.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  if (!window.pywebview?.api?.system_addCDriveWhitelist) {
    ElMessage.warning('当前环境不支持白名单')
    return
  }
  try {
    const { ok, data: res } = await pyCall('system_addCDriveWhitelist', {
      paths: cDriveCleanState.selectedFiles.map(item => item.path)
    })
    if (ok) {
      cDriveCleanState.whitelist = res.whitelist || []
      ElMessage.success('已加入白名单')
      await scanCDriveClean()
    } else {
      ElMessage.error(res?.message || '加入白名单失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '加入白名单失败')
  }
}

const pickCDriveRulePath = async () => {
  if (!window.pywebview?.api?.system_pySelectDirDialog) return
  const dir = await callApiRaw('system_pySelectDirDialog', cDriveCleanState.ruleForm.path || '')
  if (dir) cDriveCleanState.ruleForm.path = dir
}

const saveCDriveRule = async () => {
  if (!window.pywebview?.api?.system_saveCDriveCustomRule) {
    ElMessage.warning('当前环境不支持自定义规则')
    return
  }
  const patterns = String(cDriveCleanState.ruleForm.patterns || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
  const extFilters = String(cDriveCleanState.ruleForm.extFilters || '')
    .split(',')
    .map(item => item.trim().toLowerCase())
    .filter(Boolean)

  const payload = {
    name: cDriveCleanState.ruleForm.name,
    path: cDriveCleanState.ruleForm.path,
    patterns: patterns.length ? patterns : ['*'],
    extFilters,
    minSizeBytes: Math.max(0, Number(cDriveCleanState.ruleForm.minSizeMB || 0)) * 1024 * 1024,
    olderThanDays: Math.max(0, Number(cDriveCleanState.ruleForm.olderThanDays || 0))
  }

  const { ok, data: res } = await pyCall('system_saveCDriveCustomRule', payload)
  if (ok) {
    ElMessage.success('规则已保存')
    cDriveCleanState.customRules = res.rules || []
    await scanCDriveClean()
  } else {
    ElMessage.error(res?.message || '保存规则失败')
  }
}

const removeCDriveRule = async (row) => {
  if (!window.pywebview?.api?.system_removeCDriveCustomRule) return
  const { ok, data: res } = await pyCall('system_removeCDriveCustomRule', { id: row.id })
  if (ok) {
    cDriveCleanState.customRules = res.rules || []
    ElMessage.success('规则已删除')
    await scanCDriveClean()
  } else {
    ElMessage.error(res?.message || '删除规则失败')
  }
}
</script>

<style scoped>
.helper-hint {
  margin-bottom: 12px;
}

.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.keyword-input {
  flex: 1;
  min-width: 150px;
}

.toolbar-info {
  flex: 1;
  text-align: right;
  color: var(--ppx-text-secondary);
  font-size: 13px;
}

.toolbar-info strong {
  color: var(--el-color-primary);
}

.clean-result {
  margin-top: 12px;
}

@media (max-width: 600px) {
  .toolbar {
    flex-direction: column;
  }

  .keyword-input {
    width: 100%;
  }

  :deep(.el-button) {
    width: 100%;
  }
}
</style>
