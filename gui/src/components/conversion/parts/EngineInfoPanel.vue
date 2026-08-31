<script setup>
import { computed } from 'vue'
import { CircleCheck, Refresh, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({ engine: { type: Object, required: true } })
const emit = defineEmits(['refresh'])

const groupLabels = {
  image: '图片',
  text: '文本与电子书',
  document: 'Word / WPS / OFD',
  spreadsheet: 'Excel / WPS 表格',
  presentation: 'PPT / WPS 演示',
  pdf: 'PDF',
  audio: '音频',
  video: '视频',
  any: '任意文件'
}

const groups = computed(() =>
  Object.entries(props.engine.groups || {}).map(([id, group]) => ({
    id,
    label: groupLabels[id] || id,
    inputs: Array.isArray(group?.inputs) ? group.inputs : [],
    targets: Array.isArray(group?.targets) ? group.targets : []
  }))
)
</script>

<template>
  <section class="engine-page">
    <header class="engine-head">
      <div>
        <span class="eyebrow">本地转换引擎</span>
        <h2>{{ engine.metadata.name }}</h2>
        <p>PPX 通过其公开 CLI 调用转换能力，文件仍在本机处理。</p>
      </div>
      <el-button :loading="engine.loading" @click="emit('refresh')"
        ><el-icon><Refresh /></el-icon>重新检测</el-button
      >
    </header>

    <div class="status-line" :class="{ ready: engine.available }">
      <el-icon :size="20"><CircleCheck v-if="engine.available" /><WarningFilled v-else /></el-icon>
      <div>
        <b>{{ engine.available ? '引擎已连接' : '引擎未就绪' }}</b>
        <p>{{ engine.detail }}</p>
      </div>
      <el-tag :type="engine.available ? 'success' : 'warning'" effect="plain">{{ engine.runtime?.mode === 'bundled' ? 'PPX 内置' : engine.runtime?.mode === 'source' ? '开发源码' : engine.runtime?.mode === 'installed' ? '外部安装版' : '待修复' }}</el-tag>
    </div>

    <section v-if="groups.length" class="format-section">
      <div class="section-title">
        <h3>当前环境可用格式</h3>
        <p>目标格式会根据 FFmpeg、LibreOffice、Poppler、Tesseract 等组件动态收敛。</p>
      </div>
      <div class="format-list">
        <article v-for="group in groups" :key="group.id">
          <b>{{ group.label }}</b>
          <p><span>输入</span>{{ group.inputs.join(' · ') || '—' }}</p>
          <p><span>输出</span>{{ group.targets.join(' · ') || '—' }}</p>
        </article>
      </div>
    </section>

    <section class="setup-section">
      <div class="section-title">
        <h3>内置运行时</h3>
        <p>完整安装包已经包含 FlyingMouse CLI、生产依赖和当前平台的 Node 运行时。</p>
      </div>
      <ol>
        <li>发布版优先使用包内 <code>vendor/flyingmouse-format</code> 与内置 Node</li>
        <li>开发环境运行 <code>git submodule update --init --recursive</code></li>
        <li>随后运行 <code>pnpm run prepare:flyingmouse</code> 安装生产依赖</li>
        <li><code>PPX_FLYINGMOUSE_CLI_PATH</code> 等变量仅用于调试覆盖</li>
        <li>内置组件损坏时请重新安装完整 PPX 安装包</li>
      </ol>
    </section>

    <footer class="license-note">
      <b>作者与许可</b>
      <p>转换引擎版权归 {{ engine.metadata.author }} 所有，采用“{{ engine.metadata.license }}”。PPX 经授权内置其 CLI 运行时并保留署名，不把 FlyingMouse 代码声明为 PPX 自有实现。</p>
    </footer>
  </section>
</template>

<style scoped>
.engine-page {
  color: var(--ppx-text-secondary);
}
.engine-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}
.eyebrow {
  color: var(--accent);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.engine-head h2 {
  margin: 5px 0 6px;
  color: var(--ppx-text-primary);
  font-size: 24px;
}
.engine-head p,
.status-line p,
.section-title p,
.license-note p {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12.5px;
  line-height: 1.6;
}
.status-line {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 15px 16px;
  border: 1px solid color-mix(in srgb, var(--el-color-warning) 30%, var(--ppx-glass-border));
  border-radius: var(--ppx-radius-md);
  background: color-mix(in srgb, var(--el-color-warning) 7%, var(--ppx-bg-surface));
  color: var(--el-color-warning);
}
.status-line.ready {
  border-color: color-mix(in srgb, var(--el-color-success) 30%, var(--ppx-glass-border));
  background: color-mix(in srgb, var(--el-color-success) 6%, var(--ppx-bg-surface));
  color: var(--el-color-success);
}
.status-line b {
  color: var(--ppx-text-primary);
  font-size: 13px;
}
.format-section,
.setup-section {
  margin-top: 28px;
}
.section-title {
  margin-bottom: 11px;
}
.section-title h3 {
  margin: 0 0 4px;
  color: var(--ppx-text-primary);
  font-size: 15px;
}
.format-list {
  border-top: 1px solid var(--ppx-glass-border);
}
.format-list article {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 6px 16px;
  padding: 13px 4px;
  border-bottom: 1px solid var(--ppx-glass-border);
}
.format-list article > b {
  grid-row: span 2;
  color: var(--ppx-text-primary);
  font-size: 12.5px;
}
.format-list p {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 11.5px;
  line-height: 1.55;
  word-break: break-word;
}
.format-list p span {
  display: inline-block;
  width: 34px;
  color: var(--ppx-text-secondary);
  font-weight: 650;
}
.setup-section ol {
  margin: 0;
  padding: 13px 13px 13px 34px;
  border-radius: var(--ppx-radius-sm);
  background: var(--ppx-bg-inset);
  color: var(--ppx-text-secondary);
  font-size: 12px;
  line-height: 1.9;
}
code {
  font-family: var(--ppx-font-mono);
  color: var(--accent);
}
.license-note {
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid var(--ppx-glass-border);
}
.license-note b {
  display: block;
  margin-bottom: 5px;
  color: var(--ppx-text-primary);
  font-size: 13px;
}
@media (max-width: 680px) {
  .engine-head {
    flex-direction: column;
  }
  .format-list article {
    grid-template-columns: 1fr;
  }
  .format-list article > b {
    grid-row: auto;
  }
}
</style>
