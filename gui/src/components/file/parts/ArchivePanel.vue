<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

import ResultTable from '../../shared/ResultTable.vue'

const loading = ref(false)

const archive = reactive({
  items: [],
  format: 'zip',
  archiveName: '',
  password: '',
  outputDir: '',
  result: ''
})

const extract = reactive({
  archiveFile: null,
  targetDir: '',
  password: '',
  files: []
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  callApiRaw('system_pyOpenFile', path)
}

const selectArchiveOutput = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', archive.outputDir || '')
  if (dir) {
    archive.outputDir = dir
  }
}

const selectExtractTarget = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', extract.targetDir || '')
  if (dir) {
    extract.targetDir = dir
  }
}

const selectArchiveFile = async () => {
  if (!ensurePyReady()) return
  const res = await callApiRaw('system_pyCreateFileDialog', ['压缩文件 (*.zip;*.7z)'])
  if (res?.length) {
    extract.archiveFile = res[0]
  }
}

const addArchiveFiles = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', ['全部文件 (*.*)'])
  if (files?.length) {
    archive.items.push(...files.map((file) => ({ ...file, type: 'file' })))
  }
}

const addArchiveFolder = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', archive.outputDir)
  if (dir) {
    archive.items.push({ path: dir, filename: dir.split(/[\\/]/).pop(), type: 'folder' })
  }
}

const removeArchiveItem = (index) => {
  archive.items.splice(index, 1)
}

const runCompress = async () => {
  if (!ensurePyReady()) return
  if (!archive.items.length) {
    ElMessage.warning('请先添加文件或文件夹')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_compress', {
      items: archive.items.map((item) => item.path || item),
      format: archive.format,
      archiveName: archive.archiveName,
      outputDir: archive.outputDir,
      password: archive.password
    })
    if (ok) {
      archive.result = res.file || ''
      ElMessage.success(message || '压缩完成')
    } else {
      ElMessage.error(message || '压缩失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '压缩失败')
  } finally {
    loading.value = false
  }
}

const runExtract = async () => {
  if (!ensurePyReady()) return
  if (!extract.archiveFile) {
    ElMessage.warning('请选择压缩包')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('file_decompress', {
      archiveFile: extract.archiveFile.path || extract.archiveFile,
      targetDir: extract.targetDir,
      password: extract.password
    })
    if (ok) {
      extract.files = res.files || []
      extract.targetDir = res.outputDir || extract.targetDir
      ElMessage.success(message || '解压完成')
    } else {
      ElMessage.error(message || '解压失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '解压失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
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
          v-if="archive.items.length"
          :data="archive.items"
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
        <el-form :model="archive" label-width="100px" style="margin-top: 12px">
          <el-form-item label="格式">
            <el-radio-group v-model="archive.format">
              <el-radio-button label="zip">ZIP</el-radio-button>
              <el-radio-button label="7z">7Z</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="文件名">
            <el-input v-model="archive.archiveName" placeholder="可选，如 work_backup" />
          </el-form-item>
          <el-form-item label="输出目录">
            <div class="field-row">
              <el-input v-model="archive.outputDir" placeholder="留空使用源目录" readonly />
              <el-button @click="selectArchiveOutput">目录</el-button>
            </div>
          </el-form-item>
          <el-form-item label="密码" v-if="archive.format === '7z'">
            <el-input v-model="archive.password" placeholder="可选" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="runCompress">开始压缩</el-button>
          </el-form-item>
        </el-form>
        <el-alert
          v-if="archive.result"
          type="success"
          :closable="false"
          show-icon
        >
          <template #title>
            已生成：
            <a class="link" @click.prevent="openPath(archive.result)">{{ archive.result }}</a>
          </template>
        </el-alert>
      </div>

      <div class="archive-card">
        <h5>解压缩</h5>
        <el-form :model="extract" label-width="100px">
          <el-form-item label="压缩包">
            <div class="field-row">
              <el-input :model-value="extract.archiveFile?.path || ''" placeholder="选择 ZIP/7Z" readonly />
              <el-button @click="selectArchiveFile">选择</el-button>
            </div>
          </el-form-item>
          <el-form-item label="输出目录">
            <div class="field-row">
              <el-input v-model="extract.targetDir" placeholder="自动创建" readonly />
              <el-button @click="selectExtractTarget">目录</el-button>
            </div>
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="extract.password" placeholder="如文件带密码" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="runExtract">开始解压</el-button>
          </el-form-item>
        </el-form>
        <ResultTable
          v-if="extract.files.length"
          title="部分解压文件"
          :items="extract.files.map((path) => ({ path }))"
          :columns="[{ label: '文件路径', prop: 'path' }]"
          :max-height="200"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
/* 压缩/解压网格 */
.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.archive-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  padding: 16px;
  background: var(--ppx-glass-bg);
  transition: all var(--ppx-transition-fast);
}

.archive-card:hover {
  border-color: var(--ppx-glass-border-hover);
}

.archive-card h5 {
  margin: 0 0 12px;
  color: var(--ppx-text-primary);
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
