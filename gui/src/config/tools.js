// v2.0 工具注册表：导航、首页、命令面板和模块中心共享同一份元数据。
import { markRaw } from 'vue'
import { Cpu, Document, Edit, Files, FolderOpened, HomeFilled, Monitor, PictureFilled, Share, Stamp, Tickets, VideoPlay } from '@element-plus/icons-vue'

const feature = (id, label, keywords = [], options = {}) => ({ id, label, keywords, ...options })

export const TOOLS = [
  {
    id: 'image',
    name: '图片处理',
    desc: '转换 · 压缩 · OCR',
    icon: markRaw(PictureFilled),
    group: 'office',
    hue: '#2b6fff',
    locked: true,
    defaultEnabled: true,
    points: ['14 种格式互转', '批量压缩与水印', '本地图片文字识别'],
    features: [feature('convert', '图片格式转换', ['格式', 'PNG', 'JPG', 'WEBP'], { featured: true }), feature('compress', '批量压缩图片', ['质量', '目标大小'], { featured: true }), feature('crop', '图片裁剪', ['尺寸', '比例']), feature('watermark', '批量添加水印', ['文字水印', '图片水印']), feature('pdf', '图片合成 PDF', ['图片转 PDF'], { featured: true }), feature('ocr', '图片 OCR 文字识别', ['扫描', '识别文字'], { featured: true })]
  },
  {
    id: 'pdf',
    name: 'PDF 工具',
    desc: '转换 · OCR · 合并',
    icon: markRaw(Files),
    group: 'office',
    hue: '#e0533d',
    locked: true,
    defaultEnabled: true,
    points: ['扫描件 OCR', '合并、拆分与压缩', '转换 Word / 图片'],
    features: [
      feature('image', 'PDF 转高清图片', ['DPI', 'PNG', 'JPG']),
      feature('scan', 'PDF 转仿真扫描件', ['扫描效果']),
      feature('compress', '压缩 PDF', ['减小体积'], { featured: true }),
      feature('merge', '合并 PDF', ['组合 PDF'], { featured: true }),
      feature('split', '拆分 PDF', ['按页拆分']),
      feature('cut', '按页码切割 PDF', ['提取页面']),
      feature('text', '提取 PDF 文本', ['Markdown', 'HTML']),
      feature('ocr', '扫描 PDF OCR', ['可搜索 PDF', '扫描件文字识别'], { featured: true }),
      feature('word', 'PDF 转 Word', ['DOCX'], { featured: true }),
      feature('images', '提取 PDF 图片', ['内嵌图片'])
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
    features: [feature('structure', '预览 Excel 结构', ['字段', '工作表']), feature('process', '清洗 Excel 数据', ['排序', '分组'], { featured: true }), feature('merge', '合并 Excel 表格', ['多表合并'], { featured: true })]
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
    features: [feature('search', '搜索文件', ['名称', '类型', '大小'], { featured: true }), feature('classify', '自动分类文件', ['整理', '移动']), feature('copy', '批量复制文件', ['复制']), feature('delete', '安全批量删除', ['回收站', '预演'], { danger: true }), feature('rename', '批量重命名', ['正则', '序号'], { featured: true }), feature('dedup', '查找重复文件', ['去重', 'MD5']), feature('archive', '压缩与解压', ['ZIP', '7Z'], { featured: true })]
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
    desc: 'JSON · 转换 · 替换',
    icon: markRaw(Edit),
    group: 'more',
    hue: '#7c5cff',
    defaultEnabled: true,
    points: ['JSON 格式化', '大小写与全半角转换', '去重与批量替换'],
    features: [feature('json', '格式化 JSON', ['校验', '查询']), feature('transform', '转换文本', ['大小写', '全半角']), feature('dedup', '文本去重与排序', ['排序']), feature('replace', '批量查找替换', ['正则', '替换'])]
  },
  {
    id: 'video',
    name: '视频处理',
    desc: '转换 · 压缩 · 截取',
    icon: markRaw(VideoPlay),
    group: 'more',
    hue: '#d6447a',
    defaultEnabled: false,
    capability: 'ffmpeg',
    badge: '需要 FFmpeg',
    points: ['常见格式互转', '压缩与截取', '提取音频'],
    features: [feature('convert', '转换视频格式', ['MP4', 'MOV', 'MKV']), feature('compress', '压缩视频', ['码率', '目标大小']), feature('cut', '截取视频片段', ['时间轴']), feature('audio', '提取视频音频', ['MP3', 'AAC']), feature('concat', '合并视频', ['拼接'])]
  },
  {
    id: 'seal',
    name: '印章图片生成',
    desc: '图形设计 · PNG 导出',
    icon: markRaw(Stamp),
    group: 'more',
    hue: '#d6342f',
    defaultEnabled: false,
    badge: '不含数字签名',
    points: ['圆形或椭圆图形', '自定义文字与弧度', '透明 PNG'],
    features: [feature('design', '生成印章图片', ['圆章', '椭圆章', 'PNG'])]
  },
  {
    id: 'mindmap',
    name: '思维导图（实验性）',
    desc: '本机服务 · 局域网协作',
    icon: markRaw(Share),
    group: 'advanced',
    hue: '#8a5cf5',
    defaultEnabled: false,
    experimental: true,
    badge: '可选服务',
    points: ['多结构导图', '本机或远程服务', '团队协作'],
    features: [feature('mindmap', '打开思维导图', ['组织架构', '时间轴', '鱼骨图'])]
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
