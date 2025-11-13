<script setup>
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'

import ResultTable from '../shared/ResultTable.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const state = reactive({
  loading: false,
  activeTab: 'search',
  search: {
    directory: '',
    keyword: '',
    extensions: '',
    recursive: true,
    minSize: 0,
    maxSize: 0,
    result: []
  },
  analyze: {
    directory: '',
    stats: null
  },
  archive: {
    items: [],
    format: 'zip',
    archiveName: '',
    password: '',
    outputDir: '',
    result: ''
  },
  extract: {
    archiveFile: null,
    targetDir: '',
    password: '',
    files: []
  }
})

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const current = state[target].directory || state[target].outputDir || state[target].targetDir || ''
  const dir = await window.pywebview.api.system_pySelectDirDialog(current)
  if (dir) {
    if (state[target].directory !== undefined) state[target].directory = dir
    if (state[target].outputDir !== undefined) state[target].outputDir = dir
    if (state[target].targetDir !== undefined) state[target].targetDir = dir
  }
}

const selectArchiveFile = async () => {
  if (!ensurePyReady()) return
  const res = await window.pywebview.api.system_pyCreateFileDialog(['压缩文件 (*.zip;*.7z)'])
  if (res?.length) {
    state.extract.archiveFile = res[0]
  }
}

const addArchiveFiles = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['全部文件 (*.*)'])
  if (files?.length) {
    state.archive.items.push(...files.map((file) => ({ ...file, type: 'file' })))
  }
}

const addArchiveFolder = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.archive.outputDir)
  if (dir) {
    state.archive.items.push({ path: dir, filename: dir.split(/[\\/]/).pop(), type: 'folder' })
  }
}

const removeArchiveItem = (index) => {
  state.archive.items.splice(index, 1)
}

const runSearch = async () => {
  if (!ensurePyReady()) return
  if (!state.search.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  state.loading = true
  try {
    const extensions = state.search.extensions
      .split(',')
      .map((item) => item.trim().replace('.', ''))
      .filter(Boolean)
    const res = await window.pywebview.api.file_search({
      directory: state.search.directory,
      keyword: state.search.keyword,
      extensions,
      recursive: state.search.recursive,
      minSize: state.search.minSize,
      maxSize: state.search.maxSize
    })
    if (res?.code === 0) {
      state.search.result = res.items || []
      ElMessage.success(res.msg || '搜索完成')
    } else {
      ElMessage.error(res?.msg || '搜索失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '搜索失败')
  } finally {
    state.loading = false
  }
}

const runAnalyze = async () => {
  if (!ensurePyReady()) return
  if (!state.analyze.directory) {
    ElMessage.warning('请选择目录')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_directory_analyze({
      directory: state.analyze.directory
    })
    if (res?.code === 0) {
      state.analyze.stats = res.stats
      ElMessage.success(res.msg || '分析完成')
    } else {
      ElMessage.error(res?.msg || '分析失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '分析失败')
  } finally {
    state.loading = false
  }
}

const runCompress = async () => {
  if (!ensurePyReady()) return
  if (!state.archive.items.length) {
    ElMessage.warning('请先添加文件或文件夹')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_compress({
      items: state.archive.items.map((item) => item.path || item),
      format: state.archive.format,
      archiveName: state.archive.archiveName,
      outputDir: state.archive.outputDir,
      password: state.archive.password
    })
    if (res?.code === 0) {
      state.archive.result = res.file || ''
      ElMessage.success(res.msg || '压缩完成')
    } else {
      ElMessage.error(res?.msg || '压缩失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '压缩失败')
  } finally {
    state.loading = false
  }
}

const runExtract = async () => {
  if (!ensurePyReady()) return
  if (!state.extract.archiveFile) {
    ElMessage.warning('请选择压缩包')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_decompress({
      archiveFile: state.extract.archiveFile.path || state.extract.archiveFile,
      targetDir: state.extract.targetDir,
      password: state.extract.password
    })
    if (res?.code === 0) {
      state.extract.files = res.files || []
      state.extract.targetDir = res.outputDir || state.extract.targetDir
      ElMessage.success(res.msg || '解压完成')
    } else {
      ElMessage.error(res?.msg || '解压失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '解压失败')
  } finally {
    state.loading = false
  }
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  window.pywebview.api.system_pyOpenFile(path)
}
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="78%"
    append-to-body
    custom-class="file-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">FILE TOOLKIT</p>
          <h3>文件管理工具</h3>
          <p class="sub">搜索、目录分析与压缩解压</p>
        </div>
        <el-tag type="success">Phase 1</el-tag>
      </div>
    </template>
    <div class="file-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="文件搜索" name="search">
          <section class="panel">
            <header>
              <h4>快速查找目录内文件</h4>
              <p>支持扩展名筛选、大小范围与递归搜索</p>
            </header>
            <el-form :model="state.search" label-width="120px">
              <el-form-item label="目录">
                <div class="field-row">
                  <el-input v-model="state.search.directory" placeholder="选择要搜索的目录" readonly />
                  <el-button @click="selectDir('search')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="关键字">
                <el-input v-model="state.search.keyword" placeholder="支持模糊匹配" clearable />
              </el-form-item>
              <el-form-item label="扩展名">
                <el-input
                  v-model="state.search.extensions"
                  placeholder="以逗号分隔，如：pdf,jpg,docx"
                />
              </el-form-item>
              <el-form-item label="大小 (B)">
                <div class="field-row">
                  <el-input-number v-model="state.search.minSize" :min="0" />
                  <span>~</span>
                  <el-input-number v-model="state.search.maxSize" :min="0" />
                </div>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.search.recursive">包含子目录</el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runSearch">开始搜索</el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.search.result.length"
              title="搜索结果"
              :description="`共 ${state.search.result.length} 条`"
              :items="state.search.result"
              :columns="[
                { label: '文件名', prop: 'name', width: 200 },
                { label: '路径', prop: 'path' },
                { label: '大小', prop: 'sizeText', width: 120 }
              ]"
            >
              <template #actions>
                <el-button text type="primary" @click="openPath(state.search.directory)">
                  打开目录
                </el-button>
              </template>
            </ResultTable>
          </section>
        </el-tab-pane>

        <el-tab-pane label="目录分析" name="analyze">
          <section class="panel">
            <header>
              <h4>统计目录结构</h4>
              <p>展示文件数量、空间占用与扩展名 Top N</p>
            </header>
            <el-form :model="state.analyze" label-width="120px">
              <el-form-item label="目录">
                <div class="field-row">
                  <el-input v-model="state.analyze.directory" placeholder="选择目录" readonly />
                  <el-button @click="selectDir('analyze')">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runAnalyze">开始分析</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.analyze.stats" class="stats-panel">
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item label="总大小">
                  {{ state.analyze.stats.totalSize }}
                </el-descriptions-item>
                <el-descriptions-item label="文件数">
                  {{ state.analyze.stats.fileCount }}
                </el-descriptions-item>
                <el-descriptions-item label="子目录数">
                  {{ state.analyze.stats.dirCount }}
                </el-descriptions-item>
              </el-descriptions>
              <div class="stat-cols">
                <div>
                  <h5>热门扩展名</h5>
                  <ul>
                    <li v-for="item in state.analyze.stats.topExtensions" :key="item.ext">
                      {{ item.ext }} · {{ item.count }}
                    </li>
                  </ul>
                </div>
                <div>
                  <h5>最大文件</h5>
                  <ul>
                    <li v-for="item in state.analyze.stats.largestFiles" :key="item.path">
                      <span>{{ item.name }}</span>
                      <span>{{ item.size }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="压缩 / 解压" name="archive">
          <section class="panel">
            <header>
              <h4>批量压缩 ZIP/7Z，或解压文件</h4>
            </header>
            <div class="archive-grid">
              <div class="archive-card">
                <h5>压缩打包</h5>
                <div class="field-row">
                  <el-button size="small" @click="addArchiveFiles">添加文件</el-button>
                  <el-button size="small" @click="addArchiveFolder">添加文件夹</el-button>
                </div>
                <el-table
                  v-if="state.archive.items.length"
                  :data="state.archive.items"
                  size="small"
                  border
                  style="margin-top: 10px"
                >
                  <el-table-column type="index" width="50" label="#" />
                  <el-table-column prop="filename" label="名称" />
                  <el-table-column label="类型" width="100">
                    <template #default="scope">
                      <el-tag size="small" effect="plain">{{ scope.row.type === 'folder' ? '文件夹' : '文件' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="80">
                    <template #default="scope">
                      <el-button link type="danger" @click="removeArchiveItem(scope.$index)">移除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-else description="尚未添加" />
                <el-form :model="state.archive" label-width="100px" style="margin-top: 12px">
                  <el-form-item label="格式">
                    <el-radio-group v-model="state.archive.format">
                      <el-radio-button label="zip">ZIP</el-radio-button>
                      <el-radio-button label="7z">7Z</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item label="文件名">
                    <el-input v-model="state.archive.archiveName" placeholder="可选，如 work_backup" />
                  </el-form-item>
                  <el-form-item label="输出目录">
                    <div class="field-row">
                      <el-input v-model="state.archive.outputDir" placeholder="留空使用源目录" readonly />
                      <el-button @click="selectDir('archive')">目录</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item label="密码" v-if="state.archive.format === '7z'">
                    <el-input v-model="state.archive.password" placeholder="可选" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="state.loading" @click="runCompress">开始压缩</el-button>
                  </el-form-item>
                </el-form>
                <el-alert
                  v-if="state.archive.result"
                  type="success"
                  :closable="false"
                  show-icon
                >
                  <template #title>
                    已生成：
                    <a class="link" @click.prevent="openPath(state.archive.result)">{{ state.archive.result }}</a>
                  </template>
                </el-alert>
              </div>

              <div class="archive-card">
                <h5>解压缩</h5>
                <el-form :model="state.extract" label-width="100px">
                  <el-form-item label="压缩包">
                    <div class="field-row">
                      <el-input :model-value="state.extract.archiveFile?.path || ''" placeholder="选择 ZIP/7Z" readonly />
                      <el-button @click="selectArchiveFile">选择</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item label="输出目录">
                    <div class="field-row">
                      <el-input v-model="state.extract.targetDir" placeholder="自动创建" readonly />
                      <el-button @click="selectDir('extract')">目录</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item label="密码">
                    <el-input v-model="state.extract.password" placeholder="如文件带密码" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="state.loading" @click="runExtract">开始解压</el-button>
                  </el-form-item>
                </el-form>
                <ResultTable
                  v-if="state.extract.files.length"
                  title="部分解压文件"
                  :items="state.extract.files.map((path) => ({ path }))"
                  :columns="[{ label: '文件路径', prop: 'path' }]"
                  :max-height="200"
                />
              </div>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  color: #8d93a8;
  letter-spacing: 2px;
}

.panel {
  background: #fff;
  border: 1px solid #e9edf5;
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 24px;
}

.panel header h4 {
  margin: 0;
}

.panel header p {
  margin: 6px 0 0;
  color: #7a829d;
  font-size: 13px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

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
}

.stat-cols ul {
  margin: 0;
  padding-left: 16px;
  color: #5f657c;
}

.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.archive-card {
  border: 1px solid #e4e7f3;
  border-radius: 14px;
  padding: 16px;
  background: #fbfcff;
}

.archive-card h5 {
  margin: 0 0 12px;
}

.link {
  color: #2f73ff;
}
</style>
