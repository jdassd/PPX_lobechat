<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { callApi, callApiRaw } from '@/utils/pyapi'

const props = defineProps({ initialTab: { type: String, default: '' } })
const activeTab = ref(props.initialTab || 'health')
const loading = ref(false)
const health = reactive({ checks: [], healthy: false, appVersion: '', platform: '' })
const backup = reactive({ outputDir: '', output: '', manifest: null })
const restore = reactive({ filePath: '', manifest: null, frontendState: {} })
const diagnostics = reactive({ outputDir: '', output: '', report: null })
const requiredChecks = computed(() => health.checks.filter((item) => ['app-data', 'disk', 'python'].includes(item.id)))
const optionalChecks = computed(() => health.checks.filter((item) => !['app-data', 'disk', 'python'].includes(item.id)))

const collectFrontendState = () => {
  const state = {}
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index)
    if (key?.startsWith('ppx-')) state[key] = localStorage.getItem(key)
  }
  return state
}

const refreshHealth = async () => {
  loading.value = true
  try {
    const response = await callApi('maintenance_health')
    if (!response.ok) return ElMessage.error(response.message || '健康检查失败')
    Object.assign(health, response.data)
  } catch (error) {
    ElMessage.error(error?.message || '健康检查失败')
  } finally {
    loading.value = false
  }
}

const chooseDir = async (target) => {
  const path = await callApiRaw('system_pySelectDirDialog', target.outputDir || '')
  if (path) target.outputDir = path
}

const createBackup = async () => {
  loading.value = true
  try {
    const response = await callApi('maintenance_backup_create', {
      outputDir: backup.outputDir,
      frontendState: collectFrontendState()
    })
    if (!response.ok) return ElMessage.error(response.message || '备份失败')
    backup.output = response.data.output
    backup.manifest = response.data.manifest
    ElMessage.success('完整备份已创建')
  } catch (error) {
    ElMessage.error(error?.message || '备份失败')
  } finally {
    loading.value = false
  }
}

const chooseBackup = async () => {
  const files = await callApiRaw('system_pyCreateFileDialog', ['PPX 备份 (*.zip)'])
  if (!files?.length) return
  const response = await callApi('maintenance_backup_inspect', { filePath: files[0].path })
  if (!response.ok) return ElMessage.error(response.message || '备份校验失败')
  restore.filePath = files[0].path
  restore.manifest = response.data.manifest
  restore.frontendState = response.data.frontendState || {}
  ElMessage.success(response.data.manifest?.integrity?.verified ? 'SHA-256 完整性校验通过' : '旧版备份兼容校验通过')
}

const scheduleRestore = async () => {
  if (!restore.filePath) return ElMessage.warning('请先选择备份文件')
  await ElMessageBox.confirm('恢复会在下次启动时应用，并自动保留一份“恢复前”安全备份。当前窗口将关闭，是否继续？', '恢复 PPX 数据', {
    type: 'warning',
    confirmButtonText: '安排恢复并关闭',
    cancelButtonText: '取消'
  })
  const response = await callApi('maintenance_backup_restore', { filePath: restore.filePath })
  if (!response.ok) return ElMessage.error(response.message || '安排恢复失败')
  Object.entries(response.data.frontendState || {}).forEach(([key, value]) => {
    if (key.startsWith('ppx-') && typeof value === 'string') localStorage.setItem(key, value)
  })
  ElMessage.success('恢复已安排，正在安全关闭')
  setTimeout(() => callApiRaw('close_window'), 600)
}

const createDiagnostics = async () => {
  loading.value = true
  try {
    const response = await callApi('maintenance_diagnostics', { outputDir: diagnostics.outputDir })
    if (!response.ok) return ElMessage.error(response.message || '生成失败')
    diagnostics.output = response.data.output
    diagnostics.report = response.data.report
    ElMessage.success('诊断报告已生成')
  } catch (error) {
    ElMessage.error(error?.message || '生成失败')
  } finally {
    loading.value = false
  }
}

const openPath = async (path) => {
  if (path) await callApiRaw('system_pyOpenFile', path)
}

watch(
  () => props.initialTab,
  (value) => {
    if (value) activeTab.value = value
  }
)
onMounted(refreshHealth)
</script>

<template>
  <div v-loading="loading" class="maintenance-tool">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="健康检查" name="health">
        <div class="health-hero" :class="{ healthy: health.healthy }">
          <div class="health-orb">{{ health.healthy ? '✓' : '!' }}</div>
          <div>
            <h3>{{ health.healthy ? '核心环境运行正常' : '发现需要关注的项目' }}</h3>
            <p>{{ health.appVersion }} · {{ health.platform }} · 所有检查均在本机完成</p>
          </div>
          <el-button @click="refreshHealth">重新检查</el-button>
        </div>
        <h4>核心检查</h4>
        <div class="check-grid">
          <article v-for="item in requiredChecks" :key="item.id" class="check-card">
            <el-tag :type="item.ok ? 'success' : 'danger'">{{ item.ok ? '正常' : '异常' }}</el-tag
            ><strong>{{ item.name }}</strong>
            <p>{{ item.detail }}</p>
          </article>
        </div>
        <h4>可选能力</h4>
        <div class="check-grid">
          <article v-for="item in optionalChecks" :key="item.id" class="check-card">
            <el-tag :type="item.ok ? 'success' : 'info'">{{ item.ok ? '可用' : '未启用' }}</el-tag
            ><strong>{{ item.name }}</strong>
            <p>{{ item.detail }}</p>
          </article>
        </div>
      </el-tab-pane>

      <el-tab-pane label="备份与恢复" name="backup">
        <div class="two-panels">
          <section class="panel-card">
            <h3>创建完整备份</h3>
            <p>包含本地任务、工作流、文档索引、数据库和界面偏好；逐文件记录 SHA-256，不读取浏览器密码或环境变量。</p>
            <el-form label-position="top">
              <el-form-item label="保存目录（留空则保存到应用数据目录）"
                ><el-input v-model="backup.outputDir"
                  ><template #append><el-button @click="chooseDir(backup)">选择</el-button></template></el-input
                ></el-form-item
              >
              <el-button type="primary" @click="createBackup">创建备份</el-button>
              <el-result v-if="backup.output" icon="success" title="备份完成" :sub-title="backup.output"
                ><template #extra><el-button @click="openPath(backup.output)">打开备份</el-button></template></el-result
              >
            </el-form>
          </section>
          <section class="panel-card">
            <h3>恢复备份</h3>
            <p>先校验路径、清单、大小、重复条目与内容摘要，再在下次启动前恢复；当前数据会自动生成恢复前备份。</p>
            <el-button @click="chooseBackup">选择并校验备份</el-button>
            <dl v-if="restore.manifest" class="manifest">
              <div>
                <dt>来源版本</dt>
                <dd>{{ restore.manifest.appVersion }}</dd>
              </div>
              <div>
                <dt>创建时间</dt>
                <dd>{{ new Date(restore.manifest.createdAt * 1000).toLocaleString() }}</dd>
              </div>
              <div>
                <dt>文件数量</dt>
                <dd>{{ restore.manifest.fileCount }}</dd>
              </div>
              <div>
                <dt>内容完整性</dt>
                <dd>
                  <el-tag :type="restore.manifest.integrity?.verified ? 'success' : 'warning'" effect="plain">{{ restore.manifest.integrity?.verified ? 'SHA-256 已验证' : '旧版 ZIP 兼容校验' }}</el-tag>
                </dd>
              </div>
            </dl>
            <el-button v-if="restore.manifest" type="danger" plain @click="scheduleRestore">安排恢复并关闭</el-button>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="诊断报告" name="diagnostics">
        <section class="panel-card diagnostics-card">
          <div>
            <h3>生成隐私安全的诊断报告</h3>
            <p>报告包含版本、系统、可选模块状态以及最近任务的状态摘要；不会收集文件正文、任务参数、密码、令牌或环境变量。</p>
          </div>
          <el-form label-position="top">
            <el-form-item label="输出目录"
              ><el-input v-model="diagnostics.outputDir"
                ><template #append><el-button @click="chooseDir(diagnostics)">选择</el-button></template></el-input
              ></el-form-item
            >
            <el-button type="primary" @click="createDiagnostics">生成报告</el-button>
            <el-button v-if="diagnostics.output" @click="openPath(diagnostics.output)">打开报告</el-button>
          </el-form>
          <el-alert v-if="diagnostics.output" :title="diagnostics.output" type="success" :closable="false" show-icon />
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.maintenance-tool {
  height: 100%;
  overflow: auto;
  box-sizing: border-box;
  padding: 18px 22px 30px;
}
.health-hero,
.panel-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 15px;
  background: var(--ppx-bg-elevated);
  padding: 20px;
}
.health-hero {
  display: grid;
  grid-template-columns: 54px 1fr auto;
  gap: 16px;
  align-items: center;
  border-left: 4px solid #e6a23c;
}
.health-hero.healthy {
  border-left-color: #32a46f;
}
.health-orb {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: white;
  background: #e6a23c;
  font-size: 26px;
  font-weight: 800;
}
.healthy .health-orb {
  background: #32a46f;
}
h3 {
  margin: 0 0 5px;
}
h4 {
  margin: 20px 0 10px;
}
p {
  color: var(--ppx-text-muted);
  margin: 0;
  line-height: 1.6;
}
.check-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.check-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 11px;
  padding: 14px;
  background: var(--ppx-bg-elevated);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: center;
}
.check-card p {
  grid-column: 1 / -1;
  font-size: 12px;
  overflow-wrap: anywhere;
}
.two-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.panel-card > p {
  margin-bottom: 18px;
}
.manifest {
  border: 1px solid var(--ppx-glass-border);
  border-radius: 10px;
  margin: 14px 0;
  padding: 10px;
}
.manifest div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 7px;
}
.manifest dt {
  color: var(--ppx-text-muted);
}
.manifest dd {
  margin: 0;
}
.diagnostics-card {
  max-width: 820px;
}
.diagnostics-card .el-form {
  margin-top: 18px;
}
@media (max-width: 850px) {
  .two-panels {
    grid-template-columns: 1fr;
  }
  .health-hero {
    grid-template-columns: 50px 1fr;
  }
  .health-hero > .el-button {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
