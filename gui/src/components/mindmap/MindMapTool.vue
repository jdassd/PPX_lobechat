<!-- ============================================================
     MindMapTool.vue —— 思维导图（团队协作）
     内嵌本地 FastAPI 服务（api/mindmap），iframe 加载其 Web 界面。
     支持局域网协作（队友浏览器直连本机地址）与连接远程服务器两种模式。
     ============================================================ -->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Link, Refresh, Monitor, Connection } from '@element-plus/icons-vue'
import { callApi as pyCall, hasPyApi, whenPyReady } from '@/utils/pyapi'

const MODE_KEY = 'ppx-mindmap-mode'
const REMOTE_KEY = 'ppx-mindmap-remote-url'
const LAN_KEY = 'ppx-mindmap-lan'

const mode = ref(localStorage.getItem(MODE_KEY) || 'local') // local | remote
const remoteUrl = ref(localStorage.getItem(REMOTE_KEY) || '')
const remoteInput = ref(remoteUrl.value)

const starting = ref(false)
const running = ref(false)
const lan = ref(localStorage.getItem(LAN_KEY) === '1')
const localUrl = ref('')
const lanUrls = ref([])
const errMsg = ref('')
const frameKey = ref(0) // 自增强制刷新 iframe

const frameSrc = computed(() => {
  if (mode.value === 'remote') return remoteUrl.value
  return running.value ? localUrl.value : ''
})

const applyState = (data) => {
  running.value = !!data.running
  localUrl.value = data.localUrl || ''
  lanUrls.value = data.lanUrls || []
  if (data.running) lan.value = !!data.lan
}

const startServer = async (useLan) => {
  starting.value = true
  errMsg.value = ''
  try {
    await whenPyReady()
    const res = await pyCall('mindmap_start', !!useLan)
    // callApi 归一化后业务字段在 res.data（running/port/localUrl/lanUrls）
    if (res.ok) {
      applyState(res.data || {})
      frameKey.value++
    } else {
      errMsg.value = res.message || '服务启动失败'
    }
  } catch (e) {
    errMsg.value = String(e?.message || e)
  } finally {
    starting.value = false
  }
}

const onLanChange = async (val) => {
  localStorage.setItem(LAN_KEY, val ? '1' : '0')
  await startServer(val) // 切换绑定地址需重启服务
  if (!errMsg.value) {
    ElMessage.success(val ? '已开启局域网协作，队友可通过下方地址访问' : '已关闭局域网协作')
  }
}

const setMode = (m) => {
  mode.value = m
  localStorage.setItem(MODE_KEY, m)
  if (m === 'local' && !running.value && hasPyApi()) startServer(lan.value)
}

const connectRemote = () => {
  let url = (remoteInput.value || '').trim()
  if (!url) {
    ElMessage.warning('请输入服务器地址，如 http://192.168.1.8:8323')
    return
  }
  if (!/^https?:\/\//i.test(url)) url = 'http://' + url
  remoteUrl.value = url
  remoteInput.value = url
  localStorage.setItem(REMOTE_KEY, url)
  frameKey.value++
}

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制: ' + text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    ElMessage.success('已复制: ' + text)
  }
}

const openInBrowser = () => {
  const url = mode.value === 'remote' ? remoteUrl.value : localUrl.value
  if (!url) return
  pyCall('mindmap_open_browser', url)
}

const reload = () => {
  frameKey.value++
}

onMounted(async () => {
  if (!hasPyApi() && mode.value === 'local') {
    // 纯浏览器开发环境：无 Python 后端，仅支持远程模式
    errMsg.value = '当前环境未连接客户端后端，可切换到「远程服务器」模式'
    return
  }
  if (mode.value === 'local') {
    // 查询现状，未运行则启动（服务常驻，切走再回来不中断协作）
    const res = await pyCall('mindmap_status')
    if (res.ok && res.data && res.data.running) {
      applyState(res.data)
    } else {
      await startServer(lan.value)
    }
  }
})
</script>

<template>
  <div class="mindmap-tool">
    <div class="mm-toolbar">
      <el-radio-group :model-value="mode" size="small" @update:model-value="setMode">
        <el-radio-button value="local">
          <el-icon><Monitor /></el-icon>&nbsp;本机服务
        </el-radio-button>
        <el-radio-button value="remote">
          <el-icon><Connection /></el-icon>&nbsp;远程服务器
        </el-radio-button>
      </el-radio-group>

      <template v-if="mode === 'local'">
        <el-tag v-if="running" type="success" effect="plain" size="small">运行中 · {{ localUrl }}</el-tag>
        <el-tag v-else-if="starting" type="warning" effect="plain" size="small">启动中…</el-tag>
        <el-tag v-else type="info" effect="plain" size="small">未运行</el-tag>

        <el-tooltip content="开启后，同一局域网的队友可在浏览器中打开下方地址，注册账号并实时协同编辑" placement="bottom">
          <span class="mm-lan-switch">
            <el-switch v-model="lan" :disabled="starting" size="small" @change="onLanChange" />
            <span class="mm-lan-label">局域网协作</span>
          </span>
        </el-tooltip>

        <template v-if="lan && lanUrls.length">
          <el-tag v-for="u in lanUrls" :key="u" class="mm-lan-url" size="small" effect="dark" type="primary" @click="copyText(u)">
            {{ u }}
            <el-icon class="mm-copy"><CopyDocument /></el-icon>
          </el-tag>
        </template>
      </template>

      <template v-else>
        <el-input v-model="remoteInput" class="mm-remote-input" size="small" placeholder="http://192.168.1.8:8323" clearable @keyup.enter="connectRemote">
          <template #prefix
            ><el-icon><Link /></el-icon
          ></template>
        </el-input>
        <el-button size="small" type="primary" @click="connectRemote">连接</el-button>
      </template>

      <span class="flex1" />
      <el-button size="small" text :disabled="!frameSrc" @click="reload">
        <el-icon><Refresh /></el-icon>&nbsp;刷新
      </el-button>
      <el-button size="small" text :disabled="!frameSrc" @click="openInBrowser">
        <el-icon><Link /></el-icon>&nbsp;浏览器打开
      </el-button>
    </div>

    <div class="mm-stage">
      <iframe v-if="frameSrc" :key="frameKey" class="mm-frame" :src="frameSrc" allow="fullscreen; clipboard-read; clipboard-write" allowfullscreen />
      <div v-else class="mm-empty">
        <el-icon :size="42" class="mm-empty-ico"><Connection /></el-icon>
        <div v-if="errMsg" class="mm-empty-text">{{ errMsg }}</div>
        <div v-else-if="starting" class="mm-empty-text">正在启动思维导图服务…</div>
        <div v-else-if="mode === 'remote'" class="mm-empty-text">输入远程服务器地址并点击「连接」</div>
        <div v-else class="mm-empty-text">服务未运行</div>
        <el-button v-if="mode === 'local' && !starting" size="small" type="primary" @click="startServer(lan)">启动服务</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mindmap-tool {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.mm-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex: none;
}
.mm-lan-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: default;
}
.mm-lan-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.mm-lan-url {
  cursor: pointer;
  user-select: none;
}
.mm-copy {
  margin-left: 4px;
  vertical-align: -2px;
}
.mm-remote-input {
  width: 260px;
}
.flex1 {
  flex: 1;
}
.mm-stage {
  flex: 1;
  min-height: 0;
  position: relative;
  background: var(--el-bg-color);
}
.mm-frame {
  width: 100%;
  height: 100%;
  border: 0;
  display: block;
}
.mm-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--el-text-color-secondary);
}
.mm-empty-ico {
  opacity: 0.35;
}
.mm-empty-text {
  font-size: 13px;
}
</style>
