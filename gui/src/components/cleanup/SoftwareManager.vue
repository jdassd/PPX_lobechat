<!-- gui/src/components/cleanup/SoftwareManager.vue
     软件管理 / 强力清理：扫描已安装软件 → 卸载 / 打开安装目录 / 强力粉碎安装目录。
     仅 Windows 桌面客户端可用。 -->
<template>
  <div class="software-manager">
    <el-alert v-if="!apiReady" type="warning" show-icon class="hint" :closable="false">
      请在桌面客户端内使用，浏览器预览无法访问本地系统信息。
    </el-alert>

    <div class="toolbar">
      <el-input
        v-model.trim="keyword"
        placeholder="按软件名 / 发行商筛选"
        clearable
        class="kw"
        @keyup.enter="scan"
      />
      <el-button type="primary" :loading="loading" @click="scan">{{ rows.length ? '刷新' : '扫描' }}</el-button>
      <el-checkbox v-model="includeSystem" @change="scan">包含系统组件</el-checkbox>
      <span class="flex1" />
      <span v-if="rows.length" class="summary">共 {{ filteredRows.length }} 个软件</span>
    </div>

    <el-alert
      type="error"
      show-icon
      :closable="false"
      class="warn"
      title="“强力粉碎”会自动结束相关进程并永久删除整个安装目录（不进回收站，不可恢复），请谨慎操作。"
    />

    <div class="table-wrap">
      <el-table
        :data="filteredRows"
        v-loading="loading"
        border
        size="small"
        height="100%"
        empty-text="点击“扫描”获取已安装软件列表"
      >
        <el-table-column prop="name" label="软件" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-name">{{ row.name }}</div>
            <div v-if="row.publisher" class="cell-sub">{{ row.publisher }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="120" show-overflow-tooltip />
        <el-table-column prop="installDate" label="安装日期" width="110" align="center" />
        <el-table-column prop="estimatedSizeText" label="占用大小" width="100" align="right">
          <template #default="{ row }">{{ row.estimatedSizeText || '—' }}</template>
        </el-table-column>
        <el-table-column prop="installLocation" label="安装目录" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.installLocation || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" :disabled="!row.canUninstall" @click="uninstall(row)">卸载</el-button>
            <el-button text size="small" :disabled="!row.canOpen" @click="openDir(row)">打开目录</el-button>
            <el-button type="danger" text size="small" :disabled="!row.canShred" @click="shred(row)">强力粉碎</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePyReady } from '@/composables/useApiCall'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'

const { apiReady } = usePyReady()

const keyword = ref('')
const includeSystem = ref(false)
const loading = ref(false)
const rows = ref([])

// 关键字本地筛选（后端也会按关键字过滤，这里保证刷新前即时响应）
const filteredRows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return rows.value
  return rows.value.filter(
    (r) => r.name.toLowerCase().includes(kw) || (r.publisher || '').toLowerCase().includes(kw)
  )
})

const scan = async () => {
  if (!hasPyApi()) {
    ElMessage.warning('该功能需在桌面客户端中使用')
    return
  }
  loading.value = true
  try {
    const { ok, data, message } = await pyCall('system_listInstalledSoftware', {
      keyword: keyword.value,
      includeSystemComponents: includeSystem.value
    })
    if (ok) {
      rows.value = data.list || []
    } else {
      ElMessage.error(message || '扫描失败')
    }
  } catch (e) {
    ElMessage.error(e?.message || '扫描失败')
  } finally {
    loading.value = false
  }
}

const uninstall = async (row) => {
  try {
    await ElMessageBox.confirm(`将调用 ${row.name} 自带的卸载程序，是否继续？`, '卸载软件', {
      type: 'warning',
      confirmButtonText: '卸载',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }
  const { ok, message } = await pyCall('system_uninstallSoftware', { id: row.id })
  if (ok) {
    ElMessage.success(message || '已启动卸载程序，完成后请点击刷新')
  } else {
    ElMessage.error(message || '卸载失败')
  }
}

const openDir = async (row) => {
  const { ok, message } = await pyCall('system_openSoftwareDir', { id: row.id })
  if (!ok) ElMessage.error(message || '无法打开安装目录')
}

const shred = async (row) => {
  try {
    await ElMessageBox.confirm(
      `即将强力粉碎以下安装目录：\n${row.installLocation}\n\n操作会先结束占用该目录的所有进程，再永久删除整个文件夹（不进回收站，无法恢复）。确定继续？`,
      '强力粉碎安装目录',
      {
        type: 'error',
        confirmButtonText: '彻底粉碎',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        dangerouslyUseHTMLString: false
      }
    )
  } catch {
    return
  }
  loading.value = true
  try {
    const { ok, data, message } = await pyCall('system_shredSoftwareDir', { id: row.id })
    if (ok) {
      const failed = (data && data.failedItems) || []
      if (failed.length) {
        ElMessage.warning(message || `部分文件未能删除（${failed.length} 项）`)
      } else {
        ElMessage.success(`${message || '已彻底粉碎'}，释放 ${data?.freedText || ''}`)
      }
      await scan()
    } else {
      ElMessage.error(message || '粉碎失败')
    }
  } catch (e) {
    ElMessage.error(e?.message || '粉碎失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.software-manager {
  height: 100%;
  box-sizing: border-box;
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.hint {
  flex-shrink: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.toolbar .kw {
  width: 260px;
}
.flex1 {
  flex: 1;
}
.summary {
  font-size: 12.5px;
  color: var(--ppx-text-muted);
}
.warn {
  flex-shrink: 0;
}
.table-wrap {
  flex: 1;
  min-height: 0;
}
.cell-name {
  font-weight: 600;
  color: var(--ppx-text-primary);
  line-height: 1.25;
}
.cell-sub {
  font-size: 11.5px;
  color: var(--ppx-text-muted);
  line-height: 1.2;
}
</style>
