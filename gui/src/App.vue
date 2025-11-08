<script setup>
import { markRaw } from 'vue'
import { Document, Files, Stamp, Setting } from '@element-plus/icons-vue'
import BtnUpdate from './components/BtnUpdate.vue'

const heroStats = [
  { label: '固定窗口', value: '1200 × 720 px', desc: '桌面端统一画布，防止布局跳动' },
  { label: '工具覆盖', value: 'Excel / PDF / 公章', desc: '核心场景优先实现，持续扩充' },
  { label: '运行模式', value: '本地 Python', desc: '调用 pywebview API，数据不出本机' }
]

const featureCards = [
  {
    id: 'excel',
    title: 'Excel 工具',
    desc: '针对固定结构的电子表格批处理',
    icon: markRaw(Document),
    tags: ['数据标准化', '图表导出'],
    action: '稍后开启',
    points: [
      '第一行支持自定义字段定义，允许通过分隔符快速匹配',
      '从第二行开始逐行清洗，可插入自定义逻辑',
      '按任意列分组输出分表，可选升序或降序排序',
      '分组结果可导出 JSON，配合前端动态绘制图表',
      '多分表可先合并回主表，再统一处理'
    ]
  },
  {
    id: 'pdf',
    title: 'PDF 工具',
    desc: '转换、合并与切割一体化',
    icon: markRaw(Files),
    tags: ['高清转换', '批量任务'],
    action: '稍后开启',
    points: [
      'PDF 转高清图片，保留矢量细节',
      '一键生成仿真扫描件效果',
      '多份 PDF 合并为单文件便于归档',
      '按区间或指定页码拆分/切割，支持批量策略'
    ]
  },
  {
    id: 'seal',
    title: '公章生成',
    desc: '内置模板快速生成电子印章',
    icon: markRaw(Stamp),
    tags: ['模板管理', '透明导出'],
    action: '稍后开启',
    points: [
      '提供常见圆章、椭圆章等基础模板',
      '可自定义文字、字号、弧度与描边',
      '导出透明 PNG，方便在 PDF/图片中叠加'
    ]
  },
  {
    id: 'roadmap',
    title: '功能预告',
    desc: '第 6 类工具正在设计中',
    icon: markRaw(Setting),
    tags: ['需求收集中'],
    action: '提交想法',
    points: [
      '更多 Office/PDF 自动化脚本接入',
      '结合 TinyDB/SQLite 打造轻量数据管道',
      '计划加入任务编排与批处理命令面板'
    ]
  }
]

const checklist = [
  {
    title: '检查更新',
    detail: '基于 BtnUpdate 组件，统一触发 system_checkNewVersion，后续将开放静默更新模式。'
  },
  {
    title: '安全配置',
    detail: '配置存放于 pyapp/config 与 TinyDB keystore，通过 system_* API 读写以保持跨平台权限。'
  },
  {
    title: '测试建议',
    detail: '运行 pnpm run start 联调前后端，发版前执行 pnpm -C gui run build 及 pnpm run pre:<platform>。'
  }
]
</script>

<template>
  <div class="app-shell">
    <div class="toolbox-window">
      <header class="hero">
        <div class="hero-copy">
          <p class="hero-eyebrow">PPX 桌面工具箱</p>
          <h1>一个窗口搞定 Excel、PDF 与印章工作</h1>
          <p class="hero-desc">
            基于 Vue 3 + Element Plus 打造的统一入口，底层通过 PyWebView 调用本地 Python 服务，确保数据不离开本机。
            当前阶段优先交付首页视觉与模块导航，功能入口将在后续迭代陆续放开。
          </p>
          <div class="hero-actions">
            <el-button size="large" type="primary" disabled>立即使用（即将开放）</el-button>
            <div class="update-entry">
              <BtnUpdate />
              <span>检测更新</span>
            </div>
          </div>
          <p class="hero-note">固定窗口尺寸 1200×720 px，所有页面都会在该画布内完整展示。</p>
        </div>
        <div class="hero-panel">
          <div v-for="stat in heroStats" :key="stat.label" class="stat-card">
            <p class="stat-label">{{ stat.label }}</p>
            <p class="stat-value">{{ stat.value }}</p>
            <p class="stat-desc">{{ stat.desc }}</p>
          </div>
        </div>
      </header>

      <main class="content">
        <section class="feature-section">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">核心能力</p>
              <h2>常用工具先行落位</h2>
            </div>
            <el-tag type="success" effect="plain">首页预览</el-tag>
          </div>
          <div class="feature-grid">
            <el-card v-for="feature in featureCards" :key="feature.id" class="feature-card" shadow="never">
              <div class="feature-title">
                <component :is="feature.icon" class="feature-icon" />
                <div>
                  <h3>{{ feature.title }}</h3>
                  <p>{{ feature.desc }}</p>
                </div>
              </div>
              <ul class="feature-list">
                <li v-for="point in feature.points" :key="point">
                  <span class="dot"></span>
                  <span>{{ point }}</span>
                </li>
              </ul>
              <div class="feature-footer">
                <div class="tags">
                  <el-tag v-for="tag in feature.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
                </div>
                <el-button size="small" type="primary" plain :disabled="feature.id !== 'roadmap'">
                  {{ feature.action }}
                </el-button>
              </div>
            </el-card>
          </div>
        </section>

        <section class="checklist">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">研发提示</p>
              <h2>上线前需要确认的事项</h2>
            </div>
          </div>
          <div class="checklist-cards">
            <el-card v-for="item in checklist" :key="item.title" class="check-card" shadow="hover">
              <h3>{{ item.title }}</h3>
              <p>{{ item.detail }}</p>
            </el-card>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at top, #f4f6fb 0%, #e4e9f2 55%, #d7deea 100%);
  padding: 30px 0;
}

.toolbox-window {
  width: 1200px;
  height: 720px;
  background: #ffffff;
  border-radius: 24px;
  box-shadow: 0 25px 60px rgba(15, 36, 71, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hero {
  display: flex;
  padding: 40px;
  gap: 24px;
  background: linear-gradient(135deg, #111c44 0%, #2c4674 70%);
  color: #ffffff;
}

.hero-copy {
  flex: 1;
}

.hero-eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  margin-bottom: 12px;
  color: rgba(255, 255, 255, 0.8);
}

.hero h1 {
  margin: 0;
  font-size: 30px;
  line-height: 1.3;
}

.hero-desc {
  margin: 16px 0 24px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.update-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
}

.hero-note {
  margin-top: 18px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.hero-panel {
  width: 360px;
  display: grid;
  grid-template-columns: repeat(1, 1fr);
  gap: 14px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-label {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.stat-value {
  margin: 10px 0 6px;
  font-size: 22px;
  font-weight: 600;
}

.stat-desc {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
}

.content {
  flex: 1;
  padding: 32px 40px;
  overflow: auto;
  background: #f6f8fb;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.section-eyebrow {
  font-size: 12px;
  letter-spacing: 0.2em;
  color: #7c879c;
  text-transform: uppercase;
  margin-bottom: 6px;
}

h2 {
  margin: 0;
  font-size: 24px;
  color: #1d2433;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.feature-card {
  min-height: 220px;
  border-radius: 18px;
}

.feature-title {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.feature-title h3 {
  margin: 0;
  font-size: 18px;
  color: #1e2235;
}

.feature-title p {
  margin: 4px 0 0;
  color: #6f7586;
}

.feature-icon {
  width: 42px;
  height: 42px;
  padding: 10px;
  border-radius: 14px;
  background: #eef2ff;
  color: #4058d7;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #4a5162;
}

.feature-list li {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.4;
}

.dot {
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: 50%;
  background: #4058d7;
  flex-shrink: 0;
}

.feature-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.checklist {
  margin-top: 34px;
}

.checklist-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.check-card {
  border-radius: 16px;
  min-height: 120px;
}

.check-card h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #232735;
}

.check-card p {
  margin: 0;
  color: #5a6070;
  line-height: 1.5;
  font-size: 13px;
}

@media (max-width: 1280px) {
  .app-shell {
    padding: 16px;
  }

  .toolbox-window {
    transform: scale(0.95);
    transform-origin: center;
  }
}
</style>
