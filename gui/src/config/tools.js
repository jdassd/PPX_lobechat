// v2.6 工具注册表：导航、首页、命令面板和模块中心共享同一份元数据。
import { markRaw } from 'vue'
import { Connection, Cpu, Document, Edit, Files, FolderOpened, HomeFilled, Monitor, PictureFilled, Refresh, Stamp, Tickets, VideoPlay } from '@element-plus/icons-vue'

const feature = (id, label, keywords = [], options = {}) => ({ id, label, keywords, ...options })

export const TOOLS = [
  {
    id: 'conversion',
    name: '转换中心',
    desc: '图片 / Office / PDF / 音视频互转',
    icon: markRaw(Refresh),
    group: 'office',
    hue: '#0c9c8f',
    locked: true,
    defaultEnabled: true,
    capability: 'flyingmouse',
    badge: '内置 FlyingMouse',
    points: ['图片、Office、PDF、音视频互转', '混合批量与目标格式记忆', '图片合成 PDF 与 PDF 合并'],
    features: [feature('universal', '通用格式转换', ['格式', '转换', 'Office', '音频', '视频'], { featured: true }), feature('images-pdf', '图片合成 PDF', ['图片转 PDF', '装订'], { featured: true }), feature('merge-pdf', 'PDF 合并', ['组合 PDF']), feature('engine', '转换引擎与许可', ['FlyingMouse', '依赖', '运行时'])]
  },
  {
    id: 'image',
    name: '图片处理',
    desc: '压缩 · 水印 · 裁剪 · OCR',
    icon: markRaw(PictureFilled),
    group: 'office',
    hue: '#2b6fff',
    locked: true,
    defaultEnabled: true,
    points: ['批量压缩与水印', '裁剪、拼接与批量命名', '本地图片文字识别'],
    features: [feature('compress', '批量压缩图片', ['质量', '目标大小'], { featured: true }), feature('crop', '图片裁剪', ['尺寸', '比例']), feature('watermark', '批量添加水印', ['文字水印', '图片水印']), feature('rotate', '旋转与翻转', ['旋转', '镜像', '翻转']), feature('concat', '图片拼接', ['长图', '网格', '横向', '纵向']), feature('rename', '图片批量命名', ['重命名', '序号', '预演']), feature('ocr', '图片 OCR 文字识别', ['扫描', '识别文字'], { featured: true })]
  },
  {
    id: 'pdf',
    name: 'PDF 工具',
    desc: '压缩 · 拆分 · OCR · 安全',
    icon: markRaw(Files),
    group: 'office',
    hue: '#e0533d',
    locked: true,
    defaultEnabled: true,
    points: ['扫描件 OCR', '合并、拆分与压缩', '页面编辑与安全副本'],
    features: [
      feature('scan', 'PDF 转仿真扫描件', ['扫描效果']),
      feature('compress', '压缩 PDF', ['减小体积'], { featured: true }),
      feature('merge', '合并 PDF', ['组合 PDF'], { featured: true }),
      feature('split', '拆分 PDF', ['按页拆分']),
      feature('cut', '按页码切割 PDF', ['提取页面']),
      feature('text', '提取 PDF 文本', ['Markdown', 'HTML']),
      feature('ocr', '扫描 PDF OCR', ['可搜索 PDF', '扫描件文字识别'], { featured: true }),
      feature('images', '提取 PDF 图片', ['内嵌图片']),
      feature('pages', 'PDF 页面工作台', ['缩略图', '重排', '旋转', '页码'], { featured: true }),
      feature('security', 'PDF 安全副本', ['水印', '脱敏', '密码', '元数据'])
    ]
  },
  {
    id: 'word',
    name: 'Word 工具',
    desc: '拆分 · 切割 · 合并',
    icon: markRaw(Tickets),
    group: 'office',
    hue: '#2b579a',
    locked: true,
    defaultEnabled: true,
    capability: 'libreoffice',
    points: ['按页码或标题拆分', '按范围切割', '多文档合并'],
    features: [feature('split', '拆分 Word', ['页码', '段落', '标题'], { featured: true }), feature('cut', '切割 Word', ['页码范围']), feature('merge', '合并 Word', ['多文档'], { featured: true })]
  },
  {
    id: 'excel',
    name: 'Excel 工具',
    desc: '清洗 · 分组 · 合并',
    icon: markRaw(Document),
    group: 'office',
    hue: '#1f9d55',
    locked: true,
    defaultEnabled: true,
    points: ['数据结构预览', '批量清洗', '按列分组导出'],
    features: [feature('structure', '预览 Excel 结构', ['字段', '工作表']), feature('profile', 'Excel 数据质检', ['列画像', '缺失值', '唯一值'], { featured: true }), feature('process', '清洗 Excel 数据', ['排序', '分组'], { featured: true }), feature('split', '按列拆分 Excel', ['分组导出', '拆表']), feature('merge', '合并 Excel 表格', ['多表合并'], { featured: true })]
  },
  {
    id: 'document',
    name: '文档中心',
    desc: '本地搜索 · 表格 OCR',
    icon: markRaw(Document),
    group: 'office',
    hue: '#4f7cff',
    defaultEnabled: true,
    badge: '本地索引',
    points: ['PDF / Word / Excel 全文检索', '增量索引与智能收件箱', '图片和 PDF 表格识别'],
    features: [feature('search', '本地文档全文搜索', ['索引', '检索', 'PDF', 'Word'], { featured: true }), feature('index', '智能收件箱', ['目录', '增量索引']), feature('table', '表格 OCR', ['图片表格', 'PDF 表格', 'Excel'], { featured: true })]
  },
  {
    id: 'file',
    name: '文件批处理',
    desc: '搜索 · 整理 · 压缩',
    icon: markRaw(FolderOpened),
    group: 'files',
    hue: '#0c9c8f',
    locked: true,
    defaultEnabled: true,
    points: ['按条件查找文件', '批量改名与分类', 'ZIP / 7Z 压缩'],
    features: [
      feature('search', '搜索文件', ['名称', '类型', '大小'], { featured: true }),
      feature('classify', '自动分类文件', ['整理', '移动']),
      feature('copy', '批量复制文件', ['复制']),
      feature('delete', '安全批量删除', ['回收站', '预演'], { danger: true }),
      feature('recycle', 'PPX 回收站', ['恢复', '撤销', '清理']),
      feature('rename', '批量重命名', ['正则', '序号'], { featured: true }),
      feature('dedup', '查找重复文件', ['去重', 'MD5']),
      feature('archive', '压缩与解压', ['ZIP', '7Z'], { featured: true })
    ]
  },
  {
    id: 'workflow',
    name: '自动化工作流',
    desc: '串联工具 · 定时执行 · 目录监听',
    icon: markRaw(Connection),
    group: 'automation',
    hue: '#8b5cf6',
    defaultEnabled: true,
    badge: 'v2.5',
    points: ['可视化串联本地工具', '模板包导入导出', '可筛选、导出的逐步骤运行记录'],
    features: [feature('workflows', '编排工作流', ['流水线', '批处理', '模板包'], { featured: true }), feature('triggers', '自动触发器', ['定时', '目录监听'], { featured: true }), feature('history', '运行记录', ['日志', '步骤结果', '导出'])]
  },
  {
    id: 'webauto',
    name: '网页数据采集',
    desc: '点选字段 · 翻页 · 导出',
    icon: markRaw(Cpu),
    group: 'automation',
    hue: '#0a8f6b',
    defaultEnabled: true,
    capability: 'playwright',
    badge: '按需下载内核',
    points: ['可视化点选字段', '自动翻页与详情页', '导出 Excel / Word'],
    features: [feature('collect', '采集网页数据', ['抓取', '爬取', '翻页', 'Excel'], { featured: true })]
  },
  {
    id: 'text',
    name: '文本工具',
    desc: '格式化 · 差异比较 · 编码',
    icon: markRaw(Edit),
    group: 'more',
    hue: '#7c5cff',
    defaultEnabled: true,
    points: ['JSON 格式化与查询', '文本和列表差异比较', 'JWT 本地结构与时效诊断'],
    features: [feature('json', '格式化 JSON', ['校验', '查询']), feature('transform', '转换文本', ['大小写', '全半角']), feature('dedup', '文本去重与排序', ['排序']), feature('replace', '批量查找替换', ['正则', '替换']), feature('diff', '文本差异比较', ['Diff', '列表', '对比'], { featured: true }), feature('jwt', 'JWT 本地诊断', ['Token', 'Payload', '过期'], { featured: true })]
  },
  {
    id: 'video',
    name: '视频处理',
    desc: '压缩 · 截取 · 合并',
    icon: markRaw(VideoPlay),
    group: 'more',
    hue: '#d6447a',
    defaultEnabled: false,
    capability: 'ffmpeg',
    badge: '需要 FFmpeg',
    points: ['压缩与截取', '提取音频', '多段视频合并'],
    features: [feature('compress', '压缩视频', ['码率', '目标大小']), feature('cut', '截取视频片段', ['时间轴']), feature('audio', '提取视频音频', ['MP3', 'AAC']), feature('concat', '合并视频', ['拼接'])]
  },
  {
    id: 'seal',
    name: '印章图片生成',
    desc: '圆形 / 椭圆印章 · PNG 导出',
    icon: markRaw(Stamp),
    group: 'more',
    hue: '#d6342f',
    defaultEnabled: false,
    badge: '不含数字签名',
    points: ['圆形或椭圆图形', '自定义文字与弧度', '透明 PNG'],
    features: [feature('design', '生成印章图片', ['圆章', '椭圆章', 'PNG'])]
  },
  {
    id: 'maintenance',
    name: '设置与维护',
    desc: '健康检查 · 备份恢复',
    icon: markRaw(Monitor),
    group: 'advanced',
    hue: '#536dfe',
    defaultEnabled: true,
    badge: '跨平台',
    points: ['核心环境与可选能力检查', '完整本地备份与安全恢复', '隐私安全的诊断报告'],
    features: [feature('health', '应用健康检查', ['诊断', '依赖', '环境'], { featured: true }), feature('backup', '备份与恢复', ['迁移', '数据', '设置'], { featured: true }), feature('diagnostics', '生成诊断报告', ['日志', '支持'])]
  },
  {
    id: 'system',
    name: '系统诊断（高级）',
    desc: '启动项 · 进程查看',
    icon: markRaw(Monitor),
    group: 'advanced',
    hue: '#3b7de0',
    defaultEnabled: false,
    platforms: ['windows'],
    badge: '仅 Windows',
    points: ['只读查看启动项', '查看进程资源', '结束进程需确认'],
    features: [feature('startup', '查看开机启动项', ['启动项', '只读']), feature('process', '查看运行进程', ['PID', '内存'])]
  }
]

export const GROUPS = [
  { id: 'office', label: '文档与数据' },
  { id: 'files', label: '文件' },
  { id: 'automation', label: '自动化' },
  { id: 'more', label: '更多工具' },
  { id: 'advanced', label: '高级工具' }
]

export const HOME = { id: 'home', name: '首页', icon: markRaw(HomeFilled) }

export const toolById = (id) => TOOLS.find((tool) => tool.id === id)
export const featureById = (toolId, featureId) => toolById(toolId)?.features?.find((item) => item.id === featureId)

export const FEATURED_ACTIONS = TOOLS.flatMap((tool) => (tool.features || []).filter((item) => item.featured).map((item) => ({ ...item, tool: tool.id, toolName: tool.name, hue: tool.hue, icon: tool.icon })))
