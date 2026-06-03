<template>
  <div>
    <div class="startup-form">
      <el-input v-model.trim="ruleForm.name" placeholder="名称" />
      <el-input v-model.trim="ruleForm.command" placeholder="启动命令" />
      <el-input v-model.trim="ruleForm.description" placeholder="备注" />
      <el-switch v-model="ruleForm.autoStart" active-text="开机启动" inactive-text="手动启动" />
      <el-button type="primary" :loading="startupLoading" @click="saveRule">保存</el-button>
      <el-button @click="resetRule">清空</el-button>
    </div>

    <el-table :data="startupRules" size="small" border class="startup-table">
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="command" label="命令" min-width="220" show-overflow-tooltip />
      <el-table-column prop="description" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.isSystem" size="small" type="info">系统</el-tag>
          <el-tag v-else size="small" type="success">自定义</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开机启动" width="120">
        <template #default="{ row }">
          <el-switch v-model="row.autoStart" :disabled="row.isSystem" @change="() => toggleRule(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <template v-if="!row.isSystem">
            <el-button size="small" text type="primary" @click="editRule(row)">编辑</el-button>
            <el-button size="small" text @click="runRule(row)">运行</el-button>
            <el-button size="small" text type="danger" @click="removeRule(row)">删除</el-button>
          </template>
          <template v-else>
            <el-button size="small" text @click="runRule(row)">运行</el-button>
            <el-button size="small" text type="info" @click="openStartupLocation(row)">打开位置</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi as pyCall } from '@/utils/pyapi'

const props = defineProps({
  apiReady: {
    type: Boolean,
    default: false
  },
  visible: {
    type: Boolean,
    default: false
  }
})

const startupRules = ref([])
const startupLoading = ref(false)
const ruleForm = reactive({
  id: '',
  name: '',
  command: '',
  description: '',
  autoStart: true
})

const loadStartupRules = async () => {
  if (!props.apiReady || !window.pywebview?.api?.system_listStartupRules) return
  startupLoading.value = true
  try {
    const { ok, data: res } = await pyCall('system_listStartupRules')
    if (ok) {
      startupRules.value = res.rules || []
    } else {
      ElMessage.error(res?.message || '获取启动项失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '获取启动项失败')
  } finally {
    startupLoading.value = false
  }
}

const resetRule = () => {
  ruleForm.id = ''
  ruleForm.name = ''
  ruleForm.command = ''
  ruleForm.description = ''
  ruleForm.autoStart = true
}

const saveRule = async () => {
  if (!props.apiReady || !window.pywebview?.api?.system_saveStartupRule) {
    ElMessage.warning('当前环境不支持启动项管理')
    return
  }
  startupLoading.value = true
  try {
    const payload = {
      id: ruleForm.id || undefined,
      name: ruleForm.name,
      command: ruleForm.command,
      description: ruleForm.description,
      autoStart: ruleForm.autoStart
    }
    const { ok, data: res } = await pyCall('system_saveStartupRule', payload)
    if (ok) {
      startupRules.value = res.rules || []
      resetRule()
      ElMessage.success('启动项已保存')
    } else {
      ElMessage.error(res?.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '保存失败')
  } finally {
    startupLoading.value = false
  }
}

const editRule = (row) => {
  ruleForm.id = row.id
  ruleForm.name = row.name
  ruleForm.command = row.command
  ruleForm.description = row.description
  ruleForm.autoStart = !!row.autoStart
}

const toggleRule = async (row) => {
  if (!window.pywebview?.api?.system_saveStartupRule) return
  const { ok, data: res } = await pyCall('system_saveStartupRule', {
    id: row.id,
    name: row.name,
    command: row.command,
    description: row.description,
    autoStart: row.autoStart
  })
  if (ok) {
    startupRules.value = res.rules || []
  } else {
    ElMessage.error(res?.message || '更新启动项失败')
  }
}

const removeRule = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除 ${row.name || '该启动项'} 吗？`, '删除启动项', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  const { ok, data: res } = await pyCall('system_removeStartupRule', { id: row.id })
  if (ok) {
    startupRules.value = res.rules || []
    ElMessage.success('已删除')
  } else {
    ElMessage.error(res?.message || '删除失败')
  }
}

const runRule = async (row) => {
  if (!window.pywebview?.api?.system_runStartupRule) return
  // 系统启动项直接运行命令
  if (row.isSystem) {
    const { ok, data: res } = await pyCall('system_runSystemStartup', { command: row.command, filePath: row.filePath })
    if (ok) {
      ElMessage.success(`已启动`)
    } else {
      ElMessage.error(res?.message || '启动失败')
    }
    return
  }
  const { ok, data: res } = await pyCall('system_runStartupRule', { id: row.id })
  if (ok) {
    ElMessage.success(`已启动 PID ${res.pid}`)
  } else {
    ElMessage.error(res?.message || '启动失败')
  }
}

const openStartupLocation = async (row) => {
  if (!window.pywebview?.api?.system_openStartupLocation) return
  const { ok, data: res } = await pyCall('system_openStartupLocation', {
    source: row.source,
    regKey: row.regKey,
    filePath: row.filePath
  })
  if (!ok) {
    ElMessage.error(res?.message || '打开位置失败')
  }
}

// 等价复刻原父组件中两个 watch 的触发语义：
// 原父组件常驻挂载，靠 watch(visible) / watch(apiReady) 触发加载。
// 此处子面板位于 el-dialog 默认插槽内（destroy-on-close），每次打开会重新挂载，
// 因此「可见且就绪」的场景改由 onMounted 兜住（挂载时必然 visible=true）；
// 「先打开、apiReady 稍后就绪」的场景仍由 watch(apiReady) 覆盖；
// watch(visible) 保留以兼容面板未被销毁却切换可见态的边界情况。
onMounted(() => {
  if (props.visible && props.apiReady) {
    loadStartupRules()
  }
})

watch(
  () => props.visible,
  (show) => {
    if (show && props.apiReady) {
      loadStartupRules()
    }
  }
)

watch(
  () => props.apiReady,
  (ready) => {
    if (ready && props.visible) {
      loadStartupRules()
    }
  }
)
</script>

<style scoped>
.startup-form {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
  align-items: center;
}

.startup-table {
  margin-top: 6px;
}

@media (max-width: 900px) {
  .startup-form {
    grid-template-columns: 1fr;
  }
}
</style>
