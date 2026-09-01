<script setup>
import { computed, onMounted } from 'vue'
import { CircleCheck, Connection, Refresh, Tools, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { GROUPS, TOOLS } from '@/config/tools'
import { useCapabilities } from '@/composables/useCapabilities'
import { useToolRegistry } from '@/composables/useToolRegistry'

const emit = defineEmits(['open'])
const { isPlatformSupported, isToolEnabled, resetToolPreferences, setToolEnabled } = useToolRegistry()
const { state, loadCapabilities } = useCapabilities()

const groups = computed(() => GROUPS.map((group) => ({ ...group, tools: TOOLS.filter((tool) => tool.group === group.id) })).filter((group) => group.tools.length))
const capabilityItems = computed(() => Object.values(state.capabilities || {}))

const capabilityFor = (tool) => (tool.capability ? state.capabilities?.[tool.capability] : null)
const repairGuide = {
  ocr: 'OCR 随完整安装包提供。开发环境请重新运行 pnpm run init；安装版请下载完整安装包。',
  ffmpeg: '请安装 FFmpeg，并确保 ffmpeg 与 ffprobe 能被系统识别。安装完成后回到本页重新检测。',
  libreoffice: '请安装 LibreOffice。PPX 会自动检测 soffice，用于 Word 真实分页。',
  flyingmouse: '完整安装包已内置 FlyingMouse Format。若组件缺失，请重新安装；开发环境请运行 pnpm run prepare:flyingmouse。',
  system: '系统高级诊断仅在 Windows 上提供，其他平台不受影响。'
}

const repairCapability = async (item) => {
  if (item.id === 'playwright') {
    emit('open', { tool: 'webauto', feature: 'collect' })
    ElMessage.info('请在网页采集页面选择下载源并安装 Chromium 内核')
    return
  }
  await ElMessageBox.alert(repairGuide[item.id] || item.detail, `${item.name}修复指引`, { confirmButtonText: '知道了' })
}

const toggle = (tool, value) => {
  setToolEnabled(tool.id, value)
  ElMessage.success(value ? `已启用${tool.name}` : `已停用${tool.name}`)
}

const reset = () => {
  resetToolPreferences()
  ElMessage.success('已恢复推荐模块配置')
}

onMounted(() => loadCapabilities())
</script>

<template>
  <div class="module-page">
    <header class="page-head">
      <div>
        <span class="eyebrow">按需启用</span>
        <h1>工具与能力</h1>
        <p>核心文档工具始终可用；媒体、协作、系统等模块可按需开启，侧栏只显示你需要的功能。</p>
      </div>
      <div class="head-actions">
        <el-button :loading="state.loading" @click="loadCapabilities(true)"
          ><el-icon><Refresh /></el-icon>重新检测</el-button
        >
        <el-button @click="reset">恢复推荐配置</el-button>
      </div>
    </header>

    <el-alert class="safety-note" type="success" :closable="false" show-icon title="已移除强力粉碎和任意启动命令" description="为安全起见，不再提供安装目录的永久删除；启动项页面改为只读诊断。" />

    <section class="capability-section">
      <div class="section-title">
        <div>
          <h2>本机能力</h2>
          <p>外部组件缺失时会在对应模块给出提示，不影响其他工具。</p>
        </div>
        <el-tag v-if="state.platform" effect="plain">{{ state.platform }}</el-tag>
      </div>
      <el-alert v-if="state.error" type="warning" :closable="false" :title="state.error" />
      <div v-if="capabilityItems.length" class="capability-grid">
        <article v-for="item in capabilityItems" :key="item.id" class="capability-card">
          <span class="cap-icon" :class="{ ready: item.available }"
            ><el-icon><CircleCheck v-if="item.available" /><WarningFilled v-else /></el-icon
          ></span>
          <div>
            <b>{{ item.name }}</b>
            <p>{{ item.detail }}</p>
          </div>
          <div class="cap-actions">
            <el-tag :type="item.available ? 'success' : 'warning'" size="small" effect="plain">{{ item.available ? '可用' : '未就绪' }}</el-tag>
            <el-button v-if="!item.available" text type="primary" size="small" @click="repairCapability(item)">处理</el-button>
          </div>
        </article>
      </div>
      <div v-else-if="state.loading" class="loading-row">
        <el-icon class="spin"><Refresh /></el-icon>正在检测本机能力…
      </div>
    </section>

    <section v-for="group in groups" :key="group.id" class="module-section">
      <div class="section-title">
        <div>
          <h2>{{ group.label }}</h2>
        </div>
      </div>
      <div class="module-grid">
        <article v-for="tool in group.tools" :key="tool.id" class="module-card" :class="{ disabled: !isToolEnabled(tool) }">
          <span class="tool-icon" :style="{ background: tool.hue + '1a', color: tool.hue }"
            ><el-icon :size="22"><component :is="tool.icon" /></el-icon
          ></span>
          <div class="module-main">
            <div class="module-name-row">
              <h3>{{ tool.name }}</h3>
              <el-tag v-if="tool.badge" size="small" effect="plain">{{ tool.badge }}</el-tag>
            </div>
            <p>{{ tool.desc }}</p>
            <span v-if="!isPlatformSupported(tool)" class="module-warning"
              ><el-icon><Connection /></el-icon>当前平台不支持</span
            >
            <span v-else-if="capabilityFor(tool) && !capabilityFor(tool).available" class="module-warning"
              ><el-icon><WarningFilled /></el-icon>{{ capabilityFor(tool).detail }}</span
            >
          </div>
          <div class="module-actions">
            <el-tag v-if="tool.locked" type="success" effect="plain" size="small">核心</el-tag>
            <el-switch v-else :model-value="isToolEnabled(tool)" :disabled="!isPlatformSupported(tool)" :aria-label="`${isToolEnabled(tool) ? '停用' : '启用'}${tool.name}`" @change="toggle(tool, $event)" />
            <el-button v-if="isToolEnabled(tool)" text type="primary" :aria-label="`打开${tool.name}`" @click="emit('open', tool.id)"
              ><el-icon><Tools /></el-icon>打开</el-button
            >
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.module-page {
  height: 100%;
  overflow-y: auto;
  padding: 32px clamp(22px, 4vw, 46px) 54px;
  box-sizing: border-box;
}
.page-head,
.module-section,
.capability-section,
.safety-note {
  max-width: 1040px;
  margin-left: auto;
  margin-right: auto;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
}
.eyebrow {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
h1 {
  margin: 5px 0 7px;
  color: var(--ppx-text-primary);
  font-size: 30px;
}
.page-head p,
.section-title p {
  margin: 0;
  color: var(--ppx-text-muted);
}
.head-actions {
  display: flex;
  gap: 8px;
}
.safety-note {
  margin-bottom: 20px;
}
.capability-section,
.module-section {
  margin-bottom: 24px;
}
.section-title {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 11px;
}
.section-title h2 {
  margin: 0 0 3px;
  color: var(--ppx-text-primary);
  font-size: 17px;
}
.section-title p {
  font-size: 12px;
}
.capability-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.capability-card,
.module-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  background: var(--ppx-bg-surface);
}
.capability-card {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  padding: 13px 14px;
}
.cap-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: color-mix(in srgb, var(--el-color-warning) 13%, transparent);
  color: var(--el-color-warning);
}
.cap-icon.ready {
  background: color-mix(in srgb, var(--el-color-success) 13%, transparent);
  color: var(--el-color-success);
}
.capability-card b {
  color: var(--ppx-text-primary);
  font-size: 13px;
}
.capability-card p {
  margin: 3px 0 0;
  color: var(--ppx-text-muted);
  font-size: 11.5px;
}
.cap-actions {
  display: flex;
  align-items: flex-end;
  flex-direction: column;
  gap: 3px;
}
.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.module-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 15px;
  transition: opacity var(--ppx-transition-fast);
}
.module-card.disabled {
  opacity: 0.65;
}
.tool-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 11px;
}
.module-main {
  min-width: 0;
}
.module-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
}
.module-name-row h3 {
  margin: 0;
  color: var(--ppx-text-primary);
  font-size: 14px;
}
.module-main > p {
  margin: 4px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.module-warning {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  color: var(--el-color-warning);
  font-size: 11px;
}
.module-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 5px;
}
.loading-row {
  padding: 22px;
  border: 1px dashed var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  color: var(--ppx-text-muted);
  text-align: center;
}
.spin {
  margin-right: 8px;
  animation: spin 1.2s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (max-width: 900px) {
  .page-head {
    flex-direction: column;
  }
  .capability-grid,
  .module-grid {
    grid-template-columns: 1fr;
  }
}
</style>
