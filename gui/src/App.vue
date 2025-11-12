<script setup>
import { markRaw, ref } from 'vue'
import { Document, Files, Monitor, Setting, Stamp } from '@element-plus/icons-vue'
import BtnUpdate from './components/BtnUpdate.vue'
import PdfTool from './components/pdf/PdfTool.vue'
import ExcelTool from './components/excel/ExcelTool.vue'
import SealTool from './components/seal/SealTool.vue'
import ProcessManager from './components/system/ProcessManager.vue'

const heroStats = []

const featureCards = [
  {
    id: 'excel',
    title: 'Excel 工具',
    desc: '针对固定结构的电子表格批处理',
    icon: markRaw(Document),
    tags: ['数据标准化', '图表导出'],
    action: '立即体验',
    disabled: false,
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
    action: '立即体验',
    disabled: false,
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
    action: '立即体验',
    disabled: false,
    points: [
      '提供常见圆章、椭圆章等基础模板',
      '可自定义文字、字号、弧度与描边',
      '导出透明 PNG，方便在 PDF/图片中叠加'
    ]
  },
  {
    id: 'process',
    title: '进程管理',
    desc: '定位占用端口的进程并一键结束',
    icon: markRaw(Monitor),
    tags: ['端口排查', '强制结束'],
    action: '打开面板',
    disabled: false,
    points: [
      '按进程名或命令模糊搜索',
      '支持根据端口筛查冲突来源',
      '内置强制结束能力，排除僵尸进程'
    ]
  },
  {
    id: 'roadmap',
    title: '功能预告',
    desc: '共 6 类工具正在设计中',
    icon: markRaw(Setting),
    tags: ['需求收集中'],
    action: '提交想法',
    disabled: true,
    points: [
      '更多 Office/PDF 自动化脚本接入',
      '结合 TinyDB/SQLite 打造轻量数据管理',
      '计划加入任务编排与批处理命令面板'
    ]
  }
]

const checklist = [
  {
    title: '检查更新',
    detail: '检查更新请点击上方小地球图标的方式进行更新，下载后的文件在用户的下载文件夹中，请打开安装即可完成更新操作。如果下载失败，请检查网络代理情况'
  },
  {
    title: '通知公告',
    detail: '该软件一次付费后永久更新，不再收费，没有广告，如需反馈软件使用问题，请发送名称为：“工具软件问题反馈”的邮件到邮箱：dassdj@yandex.com'
  }
]

const pdfToolVisible = ref(false)
const excelToolVisible = ref(false)
const sealToolVisible = ref(false)
const processToolVisible = ref(false)

const onFeatureAction = (feature) => {
  if (feature.disabled) {
    return
  }
  if (feature.id === 'excel') {
    excelToolVisible.value = true
    return
  }
  if (feature.id === 'pdf') {
    pdfToolVisible.value = true
    return
  }
  if (feature.id === 'seal') {
    sealToolVisible.value = true
    return
  }
  if (feature.id === 'process') {
    processToolVisible.value = true
    return
  }
}

</script>

<template>
  <div class="app-shell">
    <div class="toolbox-window">
      <header class="hero">
        <div class="hero-copy">
          <p class="hero-eyebrow">PPX 桌面工具箱</p>
          <h1>Excel、PDF、印章、线程等小工具</h1>
          <p class="hero-desc">
            数据安全不离开本机，无广告，界面简洁美观
          </p>
          <div class="hero-actions">
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
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :disabled="feature.disabled"
                  @click="onFeatureAction(feature)"
                >
                  {{ feature.action }}
                </el-button>
              </div>
            </el-card>
          </div>
        </section>

        <section class="checklist">
          <div class="section-head">
            <div>
              <p class="section-eyebrow">使用提示与软件介绍</p>
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
  <PdfTool v-model="pdfToolVisible" />
  <ExcelTool v-model="excelToolVisible" />
  <SealTool v-model="sealToolVisible" />
  <ProcessManager v-model="processToolVisible" />
</template>

<style scoped>
.app-shell {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at top, #f4f6fb 0%, #e4e9f2 55%, #d7deea 100%);
  padding: 0;
}

.toolbox-window {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  background: #ffffff;
  border-radius: 0;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.hero {
  display: flex;
  padding: 24px 32px;
  gap: 24px;
  background: linear-gradient(135deg, #111c44 0%, #2c4674 70%);
  color: #ffffff;
  flex-shrink: 0;
  min-height: auto;
  max-height: 140px;
  overflow: hidden;
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
  display: none;
}

.hero-panel {
  display: none;
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
  padding: 20px 24px;
  overflow: auto;
  background: #f6f8fb;
  min-height: 0;
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

@media (max-width: 1440px) {
  .hero {
    padding: 20px 28px;
    max-height: 160px;
  }

  .content {
    padding: 16px 20px;
  }

  .feature-grid {
    gap: 14px;
  }

  .hero-panel {
    width: 300px;
  }
}

@media (max-width: 1200px) {
  .hero {
    flex-direction: column;
    padding: 16px 20px;
    max-height: none;
    gap: 16px;
  }

  .hero-copy h1 {
    font-size: 24px;
  }

  .hero-desc {
    font-size: 13px;
    margin: 12px 0 16px;
  }

  .hero-panel {
    width: 100%;
    grid-template-columns: repeat(3, 1fr);
  }

  .content {
    padding: 14px 16px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .checklist-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 900px) {
  .hero-copy h1 {
    font-size: 20px;
  }

  .hero-actions {
    flex-wrap: wrap;
    gap: 10px;
  }

  .hero-panel {
    grid-template-columns: repeat(2, 1fr);
  }

  h2 {
    font-size: 20px;
  }

  .section-head {
    margin-bottom: 14px;
  }

  .checklist-cards {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .hero {
    padding: 12px 14px;
  }

  .hero-copy h1 {
    font-size: 18px;
    line-height: 1.2;
  }

  .hero-eyebrow {
    font-size: 11px;
  }

  .hero-desc {
    font-size: 12px;
    line-height: 1.5;
  }

  .hero-panel {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .stat-card {
    padding: 12px 14px;
  }

  .stat-value {
    font-size: 18px;
  }

  .content {
    padding: 12px;
  }

  h2 {
    font-size: 18px;
  }

  .section-head {
    margin-bottom: 12px;
  }

  .feature-card {
    min-height: auto;
  }

  .feature-icon {
    width: 36px;
    height: 36px;
    padding: 8px;
  }

  .feature-title h3 {
    font-size: 16px;
  }

  .feature-list li {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .hero {
    padding: 8px 12px;
  }

  .hero-copy h1 {
    font-size: 16px;
  }

  .hero-desc {
    display: none;
  }

  .hero-actions {
    gap: 8px;
  }

  .hero-note {
    font-size: 11px;
  }

  .hero-panel {
    display: none;
  }

  .content {
    padding: 8px;
  }

  h2 {
    font-size: 16px;
  }

  .section-head {
    margin-bottom: 10px;
  }

  .section-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .feature-title h3 {
    font-size: 14px;
  }

  .feature-list {
    gap: 6px;
    margin: 0 0 12px;
  }

  .feature-list li {
    font-size: 11px;
    gap: 6px;
  }

  .dot {
    width: 5px;
    height: 5px;
    margin-top: 5px;
  }

  .check-card h3 {
    font-size: 14px;
    margin-bottom: 8px;
  }

  .check-card p {
    font-size: 12px;
  }
}
</style>
