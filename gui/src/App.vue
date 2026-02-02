<script setup>
import { markRaw, ref, onMounted, onUnmounted } from 'vue'
import { Document, Files, Monitor, Setting, Stamp, PictureFilled, Edit, VideoPlay, FolderOpened, Coin } from '@element-plus/icons-vue'
import BtnUpdate from './components/BtnUpdate.vue'
import PdfTool from './components/pdf/PdfTool.vue'
import ExcelTool from './components/excel/ExcelTool.vue'
import SealTool from './components/seal/SealTool.vue'
import SystemCenter from './components/system/SystemCenter.vue'
import ImageTool from './components/image/ImageTool.vue'
import TextTool from './components/text/TextTool.vue'
import VideoTool from './components/video/VideoTool.vue'
import FileTool from './components/file/FileTool.vue'
import FinanceTool from './components/finance/FinanceTool.vue'
import AutomationTool from './components/automation/AutomationTool.vue'

const isLoaded = ref(false)
const isScrolled = ref(false)
const contentAreaRef = ref(null)

// 滚动监听处理
const handleScroll = () => {
  if (contentAreaRef.value) {
    isScrolled.value = contentAreaRef.value.scrollTop > 30
  }
}

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)

  // 添加滚动监听
  if (contentAreaRef.value) {
    contentAreaRef.value.addEventListener('scroll', handleScroll)
  }
})

onUnmounted(() => {
  // 移除滚动监听
  if (contentAreaRef.value) {
    contentAreaRef.value.removeEventListener('scroll', handleScroll)
  }
})

const featureCards = [
  {
    id: 'image',
    title: '图片处理',
    desc: '格式转换 / 缩放 / 压缩 / 水印',
    icon: markRaw(PictureFilled),
    color: 'cyan',
    tags: ['批量操作', '高清输出'],
    action: '打开面板',
    disabled: false,
    points: [
      '支持 PNG / JPG / TIFF / WEBP 互转',
      '按百分比或像素缩放，支持锁定比例',
      '体积压缩支持质量或目标大小模式',
      '新增文字/图片水印、裁剪、旋转'
    ]
  },
  {
    id: 'text',
    title: '文本工具',
    desc: '编码、JSON、正则、去重',
    icon: markRaw(Edit),
    color: 'purple',
    tags: ['Base64', 'JSONPath', '正则'],
    action: '打开面板',
    disabled: false,
    points: [
      'Base64 / URL / HTML / UTF-8↔GBK',
      'JSON 美化、压缩、校验与路径查询',
      '正则工具、CSV↔JSON 转换',
      '内置 MD5 / SHA 系列哈希'
    ]
  },
  {
    id: 'video',
    title: '视频处理',
    desc: '格式转换 / 压缩 / 截取',
    icon: markRaw(VideoPlay),
    color: 'pink',
    tags: ['FFmpeg', '音频提取'],
    action: '打开面板',
    disabled: false,
    points: [
      'MP4、MOV、AVI、MKV 等互转',
      '三种压缩模式：预设、码率、目标大小',
      '按时间轴快速截取片段',
      '一键提取 MP3/WAV、导出帧图'
    ]
  },
  {
    id: 'file',
    title: '文件管理',
    desc: '搜索 / 目录分析 / 批处理',
    icon: markRaw(FolderOpened),
    color: 'green',
    tags: ['ZIP/7Z', '批量处理'],
    action: '打开面板',
    disabled: false,
    points: [
      '按关键字、扩展名、大小范围搜索',
      '批量复制、删除、重命名',
      'ZIP / 7Z 压缩与解压，支持密码'
    ]
  },
    {
    id: 'automation',
    title: '自动化',
    desc: '录制回放 / 图片识别',
    icon: markRaw(Setting),
    color: 'gray',
    tags: ['宏录制', '图片识别'],
    action: '打开面板',
    disabled: false,
    points: [
      '录制鼠标和键盘操作轨迹',
      '可循环自动回放的设置',
      '支持图片定位与自动点击',
      '脚本可导入导出'
    ]
  },
  {
    id: 'excel',
    title: 'Excel 工具',
    desc: '固定结构电子表格批处理',
    icon: markRaw(Document),
    color: 'blue',
    tags: ['数据标准化', '图表导出'],
    action: '立即体验',
    disabled: false,
    points: [
      '自定义字段定义，分隔符快速匹配',
      '逐行清洗，可插入自定义逻辑',
      '按任意列分组输出分表',
      '多分表可先合并再统一处理'
    ]
  },
  {
    id: 'pdf',
    title: 'PDF 工具',
    desc: '转换、合并与切割一体化',
    icon: markRaw(Files),
    color: 'orange',
    tags: ['高清转换', '批量任务'],
    action: '立即体验',
    disabled: false,
    points: [
      'PDF 转高清图片，保留矢量细节',
      '一键生成仿真扫描件效果',
      '多份 PDF 合并为单文件',
      '按区间或指定页码拆分/切割'
    ]
  },
  {
    id: 'seal',
    title: '公章生成',
    desc: '内置模板快速生成电子印章',
    icon: markRaw(Stamp),
    color: 'red',
    tags: ['模板管理', '透明导出'],
    action: '立即体验',
    disabled: false,
    points: [
      '提供常见圆章、椭圆章等基础模板',
      '可自定义文字、字号、弧度与描边',
      '导出透明 PNG，方便叠加使用'
    ]
  },
]

const financeCards = [
  {
    id: 'finance',
    title: '财务工具',
    desc: '人民币大写 / 票据规范',
    icon: markRaw(Coin),
    color: 'orange',
    tags: ['人民币', '票据填写'],
    action: '打开面板',
    disabled: false,
    points: [
      '输入金额快速生成中文大写',
      '自动补全人民币前缀与元/角/分',
      '符合银行票据填写规范',
      '内置常见示例便于核对'
    ]
  }
]


const systemCards = [
  {
    id: 'system',
    title: '系统管理',
    desc: '性能监控、温度/电压/风扇、启动项',
    icon: markRaw(Monitor),
    color: 'indigo',
    tags: ['CPU / GPU', '系统状态'],
    action: '打开面板',
    disabled: false,
    points: [
      'CPU / 内存 / 磁盘 / GPU 性能监控',
      '温度、电压、风扇转速实时展示',
      '开机启动项管理、系统运行时间'
    ]
  }
]

const checklist = [
  {
    title: '检查更新',
    icon: '🔄',
    detail: '点击上方地球图标检测更新，下载后打开安装即可。如下载失败，请检查网络代理'
  },
  {
    title: '通知公告',
    icon: '📢',
    detail: '一次付费永久更新，无广告。问题反馈请发邮件至：dassdj@yandex.com'
  },
  {
    title: '视频功能配置',
    icon: '🎬',
    parts: [
      '部分功能需安装 FFMPEG，',
      {
        text: '点击查看教程',
        url: 'https://blog.csdn.net/weixin_43914278/article/details/131722929'
      }
    ]
  }
]

const pdfToolVisible = ref(false)
const excelToolVisible = ref(false)
const sealToolVisible = ref(false)
const systemToolVisible = ref(false)
const imageToolVisible = ref(false)
const textToolVisible = ref(false)
const videoToolVisible = ref(false)
const fileToolVisible = ref(false)
const financeToolVisible = ref(false)
const automationToolVisible = ref(false)

const onFeatureAction = (feature) => {
  if (feature.disabled) return

  const visibilityMap = {
    excel: excelToolVisible,
    pdf: pdfToolVisible,
    seal: sealToolVisible,
    system: systemToolVisible,
    image: imageToolVisible,
    text: textToolVisible,
    video: videoToolVisible,
    file: fileToolVisible,
    finance: financeToolVisible,
    automation: automationToolVisible
  }

  if (visibilityMap[feature.id]) {
    visibilityMap[feature.id].value = true
  }
}
</script>

<template>
  <div class="app-container" :class="{ loaded: isLoaded }">
    <!-- 背景装饰 -->
    <div class="bg-decorations">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="grid-pattern"></div>
    </div>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部导航栏 -->
      <header class="top-bar">
        <div class="logo-area">
          <div class="logo-icon">
            <span class="logo-text">PPX</span>
          </div>
          <span class="logo-label">桌面工具箱</span>
        </div>
        <div class="top-bar-actions">
          <BtnUpdate />
          <span class="update-hint">检测更新</span>
        </div>
      </header>

      <!-- Hero 区域 -->
      <section class="hero-section" :class="{ collapsed: isScrolled }">
        <div class="hero-content">
          <h1 class="hero-title">
            <span class="title-gradient">多功能</span>桌面工具集
          </h1>
          <p class="hero-subtitle" :class="{ hidden: isScrolled }">
            Excel / PDF / 图片 / 文本 / 视频 / 文件 —— 数据安全不离开本机
          </p>
        </div>
      </section>

      <!-- 工具卡片网格 -->
      <main ref="contentAreaRef" class="content-area">
        <div class="section-header">
          <div class="section-title">
            <span class="section-badge">核心能力</span>
            <h2>常用工具</h2>
          </div>
        </div>

        <div class="feature-grid">
          <div
            v-for="(feature, index) in featureCards"
            :key="feature.id"
            class="feature-card"
            :class="[`card-${feature.color}`, { disabled: feature.disabled }]"
            :style="{ '--delay': `${index * 0.05}s` }"
            @click="onFeatureAction(feature)"
          >
            <!-- 卡片发光效果 -->
            <div class="card-glow"></div>

            <!-- 卡片内容 -->
            <div class="card-header">
              <div class="icon-wrapper">
                <component :is="feature.icon" class="feature-icon" />
              </div>
              <div class="title-area">
                <h3>{{ feature.title }}</h3>
                <p>{{ feature.desc }}</p>
              </div>
            </div>

            <ul class="feature-points">
              <li v-for="point in feature.points" :key="point">
                <span class="point-dot"></span>
                <span>{{ point }}</span>
              </li>
            </ul>

            <div class="card-footer">
              <div class="tag-list">
                <span v-for="tag in feature.tags" :key="tag" class="feature-tag">
                  {{ tag }}
                </span>
              </div>
              <button class="action-btn" :disabled="feature.disabled">
                {{ feature.action }}
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>

        <div class="section-header">
          <div class="section-title">
            <span class="section-badge">财务专区</span>
            <h2>财务工具</h2>
          </div>
        </div>

        <div class="feature-grid">
          <div
            v-for="(feature, index) in financeCards"
            :key="feature.id"
            class="feature-card"
            :class="[`card-${feature.color}`, { disabled: feature.disabled }]"
            :style="{ '--delay': `${index * 0.05}s` }"
            @click="onFeatureAction(feature)"
          >
            <div class="card-glow"></div>

            <div class="card-header">
              <div class="icon-wrapper">
                <component :is="feature.icon" class="feature-icon" />
              </div>
              <div class="title-area">
                <h3>{{ feature.title }}</h3>
                <p>{{ feature.desc }}</p>
              </div>
            </div>

            <ul class="feature-points">
              <li v-for="point in feature.points" :key="point">
                <span class="point-dot"></span>
                <span>{{ point }}</span>
              </li>
            </ul>

            <div class="card-footer">
              <div class="tag-list">
                <span v-for="tag in feature.tags" :key="tag" class="feature-tag">
                  {{ tag }}
                </span>
              </div>
              <button class="action-btn" :disabled="feature.disabled">
                {{ feature.action }}
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>

        <div class="section-header">
          <div class="section-title">
            <span class="section-badge">系统管理专区</span>
            <h2>系统管理</h2>
          </div>
        </div>

        <div class="feature-grid">
          <div
            v-for="(feature, index) in systemCards"
            :key="feature.id"
            class="feature-card"
            :class="[`card-${feature.color}`, { disabled: feature.disabled }]"
            :style="{ '--delay': `${index * 0.05}s` }"
            @click="onFeatureAction(feature)"
          >
            <div class="card-glow"></div>

            <div class="card-header">
              <div class="icon-wrapper">
                <component :is="feature.icon" class="feature-icon" />
              </div>
              <div class="title-area">
                <h3>{{ feature.title }}</h3>
                <p>{{ feature.desc }}</p>
              </div>
            </div>

            <ul class="feature-points">
              <li v-for="point in feature.points" :key="point">
                <span class="point-dot"></span>
                <span>{{ point }}</span>
              </li>
            </ul>

            <div class="card-footer">
              <div class="tag-list">
                <span v-for="tag in feature.tags" :key="tag" class="feature-tag">
                  {{ tag }}
                </span>
              </div>
              <button class="action-btn" :disabled="feature.disabled">
                {{ feature.action }}
                <span class="btn-arrow">→</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 提示信息 -->
        <section class="tips-section">
          <div class="tips-header">
            <span class="tips-badge">使用提示</span>
          </div>
          <div class="tips-grid">
            <div v-for="item in checklist" :key="item.title" class="tip-card">
              <div class="tip-icon">{{ item.icon }}</div>
              <div class="tip-content">
                <h4>{{ item.title }}</h4>
                <p v-if="item.detail">{{ item.detail }}</p>
                <p v-else class="tip-with-link">
                  <template v-for="(part, idx) in item.parts" :key="idx">
                    <span v-if="typeof part === 'string'">{{ part }}</span>
                    <a v-else :href="part.url" target="_blank" rel="noopener noreferrer" class="tip-link">
                      {{ part.text }}
                    </a>
                  </template>
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>

  <!-- 工具弹窗 -->
  <ImageTool v-model="imageToolVisible" />
  <TextTool v-model="textToolVisible" />
  <VideoTool v-model="videoToolVisible" />
  <FileTool v-model="fileToolVisible" />
  <AutomationTool v-model="automationToolVisible" />
  <PdfTool v-model="pdfToolVisible" />
  <ExcelTool v-model="excelToolVisible" />
  <SealTool v-model="sealToolVisible" />
  <SystemCenter v-model="systemToolVisible" />
  <FinanceTool v-model="financeToolVisible" />
</template>

<style scoped>
/* ========================================
   深空玻璃主题 - App 布局
   ======================================== */

.app-container {
  width: 100%;
  height: 100%;
  background: var(--ppx-bg-deep);
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.bg-decorations {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 20s ease-in-out infinite;
}

.orb-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.3) 0%, transparent 70%);
  top: -100px;
  left: -100px;
  animation-delay: 0s;
}

.orb-2 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.25) 0%, transparent 70%);
  top: 50%;
  right: -80px;
  animation-delay: -7s;
}

.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(244, 114, 182, 0.2) 0%, transparent 70%);
  bottom: -50px;
  left: 30%;
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -30px) scale(1.05); }
  50% { transform: translate(-20px, 20px) scale(0.95); }
  75% { transform: translate(10px, 30px) scale(1.02); }
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse at center, black 0%, transparent 70%);
}

/* 主容器 */
.main-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

/* 顶部导航 */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 28px;
  background: rgba(12, 13, 22, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--ppx-glass-border);
  flex-shrink: 0;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--ppx-gradient-primary);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
}

.logo-text {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.5px;
}

.logo-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  letter-spacing: 0.5px;
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.update-hint {
  font-size: 12px;
  color: var(--ppx-text-muted);
}

/* Hero 区域 */
.hero-section {
  padding: 32px 28px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  transition: padding 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-section.collapsed {
  padding: 16px 28px 12px;
}

.hero-content {
  flex: 1;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--ppx-text-primary);
  margin: 0 0 10px;
  letter-spacing: -0.5px;
  opacity: 0;
  transform: translateY(20px);
  animation: slideUp 0.6s ease forwards;
  animation-delay: 0.1s;
  transition: margin 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-section.collapsed .hero-title {
  margin-bottom: 0;
}

.title-gradient {
  background: var(--ppx-gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 15px;
  color: var(--ppx-text-secondary);
  margin: 0;
  opacity: 0;
  transform: translateY(20px);
  animation: slideUp 0.6s ease forwards;
  animation-delay: 0.2s;
  max-height: 30px;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-subtitle.hidden {
  max-height: 0;
  opacity: 0 !important;
  margin-top: -5px;
  transform: translateY(-10px);
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 24px;
  background: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  opacity: 0;
  transform: translateY(20px);
  animation: slideUp 0.6s ease forwards;
  animation-delay: 0.3s;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-number {
  font-size: 22px;
  font-weight: 700;
  background: var(--ppx-gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-label {
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--ppx-glass-border);
}

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 内容区 */
.content-area {
  flex: 1;
  padding: 0 28px 24px;
  overflow-y: auto;
  overflow-x: hidden;
}

.section-header {
  margin-bottom: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--ppx-neon-blue);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 4px 10px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 6px;
}

.section-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

/* 功能卡片网格 */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.feature-card {
  position: relative;
  background: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  opacity: 0;
  transform: translateY(20px);
  animation: cardEnter 0.5s ease forwards;
  animation-delay: var(--delay);
}

@keyframes cardEnter {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feature-card:hover {
  transform: translateY(-4px);
  border-color: var(--ppx-glass-border-hover);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.feature-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feature-card.disabled:hover {
  transform: none;
}

/* 卡片发光效果 */
.card-glow {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100px;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.feature-card:hover .card-glow {
  opacity: 1;
}

/* 不同颜色的卡片 */
.card-cyan .icon-wrapper { background: rgba(0, 212, 255, 0.15); }
.card-cyan .feature-icon { color: #00d4ff; }
.card-cyan .card-glow { background: radial-gradient(ellipse at top, rgba(0, 212, 255, 0.15) 0%, transparent 70%); }
.card-cyan .point-dot { background: #00d4ff; }

.card-purple .icon-wrapper { background: rgba(168, 85, 247, 0.15); }
.card-purple .feature-icon { color: #a855f7; }
.card-purple .card-glow { background: radial-gradient(ellipse at top, rgba(168, 85, 247, 0.15) 0%, transparent 70%); }
.card-purple .point-dot { background: #a855f7; }

.card-pink .icon-wrapper { background: rgba(244, 114, 182, 0.15); }
.card-pink .feature-icon { color: #f472b6; }
.card-pink .card-glow { background: radial-gradient(ellipse at top, rgba(244, 114, 182, 0.15) 0%, transparent 70%); }
.card-pink .point-dot { background: #f472b6; }

.card-green .icon-wrapper { background: rgba(74, 222, 128, 0.15); }
.card-green .feature-icon { color: #4ade80; }
.card-green .card-glow { background: radial-gradient(ellipse at top, rgba(74, 222, 128, 0.15) 0%, transparent 70%); }
.card-green .point-dot { background: #4ade80; }

.card-blue .icon-wrapper { background: rgba(96, 165, 250, 0.15); }
.card-blue .feature-icon { color: #60a5fa; }
.card-blue .card-glow { background: radial-gradient(ellipse at top, rgba(96, 165, 250, 0.15) 0%, transparent 70%); }
.card-blue .point-dot { background: #60a5fa; }

.card-orange .icon-wrapper { background: rgba(251, 146, 60, 0.15); }
.card-orange .feature-icon { color: #fb923c; }
.card-orange .card-glow { background: radial-gradient(ellipse at top, rgba(251, 146, 60, 0.15) 0%, transparent 70%); }
.card-orange .point-dot { background: #fb923c; }

.card-red .icon-wrapper { background: rgba(248, 113, 113, 0.15); }
.card-red .feature-icon { color: #f87171; }
.card-red .card-glow { background: radial-gradient(ellipse at top, rgba(248, 113, 113, 0.15) 0%, transparent 70%); }
.card-red .point-dot { background: #f87171; }

.card-indigo .icon-wrapper { background: rgba(129, 140, 248, 0.15); }
.card-indigo .feature-icon { color: #818cf8; }
.card-indigo .card-glow { background: radial-gradient(ellipse at top, rgba(129, 140, 248, 0.15) 0%, transparent 70%); }
.card-indigo .point-dot { background: #818cf8; }

.card-gray .icon-wrapper { background: rgba(148, 163, 184, 0.1); }
.card-gray .feature-icon { color: #94a3b8; }
.card-gray .card-glow { background: radial-gradient(ellipse at top, rgba(148, 163, 184, 0.1) 0%, transparent 70%); }
.card-gray .point-dot { background: #94a3b8; }

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 14px;
}

.icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-icon {
  width: 24px;
  height: 24px;
}

.title-area h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.title-area p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

/* 功能列表 */
.feature-points {
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-points li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--ppx-text-secondary);
  line-height: 1.5;
}

.point-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

/* 卡片底部 */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: auto;
}

.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.feature-tag {
  font-size: 10px;
  font-weight: 500;
  padding: 3px 8px;
  background: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 4px;
  color: var(--ppx-text-muted);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--ppx-text-primary);
  background: var(--ppx-glass-bg-hover);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.action-btn:hover:not(:disabled) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.3);
  color: var(--ppx-neon-blue);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-arrow {
  transition: transform 0.2s;
}

.action-btn:hover:not(:disabled) .btn-arrow {
  transform: translateX(3px);
}

/* 提示区域 */
.tips-section {
  margin-top: 8px;
}

.tips-header {
  margin-bottom: 14px;
}

.tips-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--ppx-text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tips-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.tip-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 12px;
  transition: all 0.2s;
}

.tip-card:hover {
  border-color: var(--ppx-glass-border-hover);
}

.tip-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.tip-content h4 {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.tip-content p {
  margin: 0;
  font-size: 12px;
  color: var(--ppx-text-muted);
  line-height: 1.6;
}

.tip-link {
  color: var(--ppx-neon-blue);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.tip-link:hover {
  color: #4de0ff;
  text-decoration: underline;
}

/* 响应式 */
@media (max-width: 1200px) {
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }

  .hero-stats {
    width: 100%;
    justify-content: center;
  }
}

@media (max-width: 900px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }

  .tips-grid {
    grid-template-columns: 1fr;
  }

  .hero-title {
    font-size: 26px;
  }

  .hero-stats {
    flex-wrap: wrap;
    gap: 16px;
  }

  .stat-divider {
    display: none;
  }
}

@media (max-width: 600px) {
  .top-bar {
    padding: 12px 16px;
  }

  .hero-section {
    padding: 20px 16px;
  }

  .content-area {
    padding: 0 16px 20px;
  }

  .hero-title {
    font-size: 22px;
  }

  .feature-card {
    padding: 16px;
  }
}
</style>
