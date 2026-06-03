<script setup>
import { markRaw, ref, onMounted, onUnmounted } from 'vue'
import { Document, Files, Monitor, Setting, Stamp, PictureFilled, Edit, VideoPlay, FolderOpened, Coin } from '@element-plus/icons-vue'
import ToolCard from './ToolCard.vue'

const emit = defineEmits(['open'])

const isScrolled = ref(false)
const contentAreaRef = ref(null)

// 滚动监听处理
const handleScroll = () => {
  if (contentAreaRef.value) {
    isScrolled.value = contentAreaRef.value.scrollTop > 30
  }
}

onMounted(() => {
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
    desc: '转换、压缩、水印',
    icon: markRaw(PictureFilled),
    color: 'cyan',
    // tags: ['批量操作', '高清输出'],
    // action: '打开面板',
    disabled: false,
    points: [
      'PNG、JPG、TIFF、WEBP 格式互转',
      '图片拼接、转 PDF、批量重命名',
      '按质量或目标大小压缩',
      '添加水印、裁剪、旋转'
    ]
  },
  {
    id: 'text',
    title: '文本工具',
    desc: '编码转换、格式化',
    icon: markRaw(Edit),
    color: 'purple',
    // tags: ['Base64', 'JSONPath', '正则'],
    // action: '打开面板',
    disabled: false,
    points: [
      'Base64、URL、HTML、UTF-8/GBK 编码',
      'JSON 格式化、校验、路径查询',
      '正则匹配、CSV/JSON 互转',
      'MD5、SHA 哈希计算'
    ]
  },
  {
    id: 'video',
    title: '视频处理',
    desc: '转换、压缩、剪辑',
    icon: markRaw(VideoPlay),
    color: 'pink',
    // tags: ['FFmpeg', '音频提取'],
    // action: '打开面板',
    disabled: false,
    points: [
      'MP4、MOV、AVI、MKV 格式互转',
      '预设、码率、目标大小三种压缩',
      '按时间轴截取片段',
      '提取音频、导出帧图'
    ]
  },
  {
    id: 'file',
    title: '文件管理',
    desc: '搜索、批处理、压缩',
    icon: markRaw(FolderOpened),
    color: 'green',
    // tags: ['ZIP/7Z', '批量处理'],
    // action: '打开面板',
    disabled: false,
    points: [
      '按名称、类型、大小搜索文件',
      '批量复制、删除、重命名',
      'ZIP、7Z 压缩解压，支持加密'
    ]
  },
    {
    id: 'automation',
    title: '自动化',
    desc: '录制回放、图像识别',
    icon: markRaw(Setting),
    color: 'gray',
    // tags: ['宏录制', '图片识别'],
    // action: '打开面板',
    disabled: false,
    points: [
      '录制鼠标键盘操作',
      '循环自动回放',
      '图片定位点击',
      '脚本导入导出'
    ]
  },
  {
    id: 'excel',
    title: 'Excel 工具',
    desc: '数据清洗、分组导出',
    icon: markRaw(Document),
    color: 'blue',
    // tags: ['数据标准化', '图表导出'],
    // action: '立即体验',
    disabled: false,
    points: [
      '自定义字段，快速匹配分隔符',
      '逐行清洗，插入自定义逻辑',
      '按列分组输出多表',
      '多表合并统一处理'
    ]
  },
  {
    id: 'pdf',
    title: 'PDF 工具',
    desc: '转换、合并、拆分',
    icon: markRaw(Files),
    color: 'orange',
    // tags: ['高清转换', '批量任务'],
    // action: '立即体验',
    disabled: false,
    points: [
      'PDF 转高清图片',
      '生成仿真扫描件',
      '多文件合并',
      '按页码拆分切割'
    ]
  },
  {
    id: 'seal',
    title: '公章生成',
    desc: '电子印章快速制作',
    icon: markRaw(Stamp),
    color: 'red',
    // tags: ['模板管理', '透明导出'],
    // action: '立即体验',
    disabled: false,
    points: [
      '圆章、椭圆章等模板',
      '自定义文字、字号、弧度',
      '导出透明 PNG'
    ]
  },
]

const financeCards = [
  {
    id: 'finance',
    title: '财务工具',
    desc: '金额大写转换',
    icon: markRaw(Coin),
    color: 'orange',
    // tags: ['人民币', '票据填写'],
    // action: '打开面板',
    disabled: false,
    points: [
      '数字转中文大写',
      '自动补全元角分',
      '符合票据填写规范',
      '内置常见示例'
    ]
  }
]


const systemCards = [
  {
    id: 'system',
    title: '系统管理',
    desc: '性能监控、启动项管理',
    icon: markRaw(Monitor),
    color: 'indigo',
    // tags: ['CPU / GPU', '系统状态'],
    // action: '打开面板',
    disabled: false,
    points: [
      'CPU、内存、磁盘、GPU 监控',
      '温度、电压、风扇转速',
      '启动项管理、运行时间'
    ]
  }
]

const checklist = [
  {
    title: '检查更新',
    icon: '🆕',
    detail: '点击上方地球图标检测更新，下载后打开安装即可。如下载失败，请检查网络代理'
  },
  {
    title: '通知公告',
    icon: '📢',
    // detail: '一次付费永久更新，无广告。问题反馈请发邮件至：dassdj@yandex.com'
    detail: '问题反馈请发邮件至：dassdj@yandex.com'
  },
  {
    title: '图片/视频功能配置',
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

const onFeatureAction = (featureId) => {
  emit('open', featureId)
}
</script>

<template>
  <!-- 工具卡片网格 -->
  <main ref="contentAreaRef" class="content-area">
    <!-- Hero 区域 -->
    <section class="hero-section" :class="{ collapsed: isScrolled }">
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="title-gradient">多功能</span>工具箱
        </h1>
        <p class="hero-subtitle" :class="{ hidden: isScrolled }">
          Excel / PDF / 图片 / 文本 / 视频 / 文件 / 自动化 —— 数据安全不离开本机
        </p>
      </div>
    </section>

    <div class="section-header">
      <div class="section-title">
        <span class="section-badge">常用工具</span>
      </div>
    </div>

    <div class="feature-grid">
      <ToolCard
        v-for="(feature, index) in featureCards"
        :key="feature.id"
        :feature="feature"
        :style="{ '--delay': `${index * 0.05}s` }"
        @open="onFeatureAction"
      />
    </div>

    <div class="section-header">
      <div class="section-title">
        <span class="section-badge">财务工具</span>
      </div>
    </div>

    <div class="feature-grid">
      <ToolCard
        v-for="(feature, index) in financeCards"
        :key="feature.id"
        :feature="feature"
        :style="{ '--delay': `${index * 0.05}s` }"
        @open="onFeatureAction"
      />
    </div>

    <div class="section-header">
      <div class="section-title">
        <span class="section-badge">系统管理工具</span>
      </div>
    </div>

    <div class="feature-grid">
      <ToolCard
        v-for="(feature, index) in systemCards"
        :key="feature.id"
        :feature="feature"
        :style="{ '--delay': `${index * 0.05}s` }"
        @open="onFeatureAction"
      />
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
</template>

<style scoped>
/* Hero ?? */
.hero-section {
  padding: 30px 28px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: padding 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-section.collapsed {
  padding: 14px 28px 10px;
}

.hero-content {
  flex: 1;
}

.hero-title {
  font-size: 34px;
  font-weight: 700;
  font-family: var(--ppx-font-display);
  color: var(--ppx-text-primary);
  margin: 0 0 10px;
  letter-spacing: 0.5px;
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
  font-size: 14px;
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

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ??? */
.content-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.section-header {
  margin: 18px 28px 18px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-badge {
  font-size: 13px;
  font-weight: 700;
  color: var(--ppx-neon-blue);
  text-transform: uppercase;
  letter-spacing: 1.6px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(14, 165, 164, 0.12);
  border: 1px solid rgba(14, 165, 164, 0.25);
  font-family: var(--ppx-font-display);
}

.section-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

/* ???? */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
  margin: 0 28px 28px;
  padding: 0;
}

/* ???? */
.tips-section {
  margin: 8px 28px 28px;
  padding-bottom: 24px;
}

.tips-header {
  margin-bottom: 14px;
}

.tips-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--ppx-text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tips-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.tip-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 16px;
  transition: all var(--ppx-transition-fast);
  box-shadow: var(--ppx-shadow-sm);
}

.tip-card:hover {
  border-color: var(--ppx-glass-border-hover);
  box-shadow: var(--ppx-shadow-md);
}

.tip-icon {
  font-size: 20px;
  flex-shrink: 0;
  font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'Segoe UI Symbol', sans-serif;
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
  font-weight: 600;
  transition: color 0.2s;
}

.tip-link:hover {
  color: #0f766e;
  text-decoration: underline;
}

/* ??? */
@media (max-width: 1200px) {
  .hero-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }
}

@media (max-width: 900px) {
  .hero-title {
    font-size: 28px;
  }
}

@media (max-width: 600px) {
  .hero-section {
    padding: 20px 16px;
  }

  .section-header {
    margin: 18px 16px 18px;
  }

  .feature-grid {
    margin: 0 16px 28px;
  }

  .tips-section {
    margin: 8px 16px 28px;
  }

  .hero-title {
    font-size: 24px;
  }
}
</style>
