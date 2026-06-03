<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, callApiRaw, hasPyApi } from '@/utils/pyapi'

const videoFilter = ['视频文件 (*.mp4;*.mov;*.avi;*.mkv;*.webm)']

const loading = ref(false)

const form = reactive({
  files: [],
  reencode: false,
  targetFormat: 'mp4',
  preset: 'medium',
  outputDir: '',
  result: ''
})

const ensurePyReady = () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return false
  }
  return true
}

const selectConcatFiles = async () => {
  if (!ensurePyReady()) return
  const files = await callApiRaw('system_pyCreateFileDialog', videoFilter)
  if (files?.length) {
    form.files.push(...files)
  }
}

const clearConcatFiles = () => {
  form.files = []
}

const removeConcatFile = (index) => {
  form.files.splice(index, 1)
}

const moveConcatFile = (index, direction) => {
  const target = index + direction
  if (target < 0 || target >= form.files.length) return
  const temp = form.files[index]
  form.files[index] = form.files[target]
  form.files[target] = temp
}

const selectDir = async () => {
  if (!ensurePyReady()) return
  const dir = await callApiRaw('system_pySelectDirDialog', form.outputDir)
  if (dir) {
    form.outputDir = dir
  }
}

const openFile = (file) => {
  if (!ensurePyReady() || !file) return
  callApiRaw('system_pyOpenFile', file)
}

const runConcat = async () => {
  if (!ensurePyReady()) return
  if (!form.files.length) {
    ElMessage.warning('请至少选择两个视频')
    return
  }
  loading.value = true
  try {
    const { ok, data: res, message } = await pyCall('video_concat', {
      files: form.files.map((file) => file.path || file),
      reencode: form.reencode,
      targetFormat: form.targetFormat,
      preset: form.preset,
      outputDir: form.outputDir
    })
    if (ok) {
      form.result = res.file || ''
      ElMessage.success(message || '合成完成')
    } else {
      ElMessage.error(message || '合成失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '合成失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <header>
      <h4>多视频拼接</h4>
      <p>支持直接无损合并或重新编码输出，保持自定义排序</p>
    </header>
    <div class="field-row">
      <el-button @click="selectConcatFiles">添加视频文件</el-button>
      <el-button text type="danger" :disabled="!form.files.length" @click="clearConcatFiles">
        清空
      </el-button>
    </div>
    <el-table
      v-if="form.files.length"
      :data="form.files"
      border
      size="small"
      style="margin: 16px 0"
    >
      <el-table-column type="index" width="50" label="#" />
      <el-table-column label="文件名" prop="filename" show-overflow-tooltip />
      <el-table-column label="路径" show-overflow-tooltip>
        <template #default="scope">
          {{ scope.row.path }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="scope">
          <el-button text size="small" @click="moveConcatFile(scope.$index, -1)">上移</el-button>
          <el-button text size="small" @click="moveConcatFile(scope.$index, 1)">下移</el-button>
          <el-button text size="small" type="danger" @click="removeConcatFile(scope.$index)">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-alert v-else type="info" :closable="false" show-icon>
      <template #title>请选择至少两个视频文件</template>
    </el-alert>
    <el-form :model="form" label-width="140px" class="form-block">
      <el-form-item label="输出格式">
        <div class="field-row">
          <el-select v-model="form.targetFormat" style="width: 160px">
            <el-option label="MP4" value="mp4" />
            <el-option label="MOV" value="mov" />
            <el-option label="MKV" value="mkv" />
          </el-select>
          <el-switch
            v-model="form.reencode"
            active-text="重新编码（兼容不同参数）"
          />
        </div>
      </el-form-item>
      <el-form-item v-if="form.reencode" label="编码预设">
        <el-select v-model="form.preset" style="width: 200px">
          <el-option label="更好画质" value="slow" />
          <el-option label="平衡" value="medium" />
          <el-option label="更快" value="fast" />
        </el-select>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="form.outputDir" placeholder="留空自动创建" readonly />
          <el-button @click="selectDir">目录</el-button>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :loading="loading"
          :disabled="form.files.length < 2"
          @click="runConcat"
        >
          开始合成
        </el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="form.result"
      type="success"
      :closable="false"
      show-icon
    >
      <template #title>
        已输出：<a class="link" @click.prevent="openFile(form.result)">{{ form.result }}</a>
      </template>
    </el-alert>
  </section>
</template>

<style scoped>
.form-block {
  margin-top: 18px;
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}
</style>
