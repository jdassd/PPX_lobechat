// ============================================================
// gui/src/config/tools.js —— 工具元数据 + 分组
// 供侧边栏、首页、命令面板、工作区共用。
// 图标名沿用 @element-plus/icons-vue 组件名。
// ============================================================
import { markRaw } from 'vue'
import { HomeFilled, PictureFilled, Files, Document, Edit, VideoPlay, FolderOpened, Cpu, Stamp, Monitor } from '@element-plus/icons-vue'

export const TOOLS = [
  { id: 'image', name: '图片处理', desc: '格式转换 · 压缩 · 水印', icon: markRaw(PictureFilled), group: 'media', hue: '#2b6fff', points: ['14 种格式互转', '按质量/目标大小压缩', '批量水印 · 裁剪 · 旋转', '图片合成 PDF'] },
  { id: 'pdf', name: 'PDF 工具', desc: '转换 · 合并 · 拆分', icon: markRaw(Files), group: 'media', hue: '#e0533d', points: ['转高清图 / 仿真扫描件', '合并 · 拆分 · 页码切割', '提取文本/图片 · 转 Word', '生成目录 · 页面重排'] },
  { id: 'excel', name: 'Excel 工具', desc: '数据清洗 · 分组导出', icon: markRaw(Document), group: 'media', hue: '#1f9d55', points: ['自定义字段匹配分隔符', '逐行清洗插入逻辑', '按列分组输出多表', '多表合并统一处理'] },
  { id: 'text', name: '文本工具', desc: '编码 · 格式化 · 哈希', icon: markRaw(Edit), group: 'media', hue: '#7c5cff', points: ['Base64 / URL / HTML 编码', 'JSON 格式化 · 校验 · 查询', '正则匹配 · CSV/JSON 互转', 'MD5 / SHA 哈希'] },
  { id: 'video', name: '视频处理', desc: '转换 · 压缩 · 剪辑', icon: markRaw(VideoPlay), group: 'media', hue: '#d6447a', points: ['MP4/MOV/AVI/MKV 互转', '预设/码率/目标大小压缩', '按时间轴截取片段', '提取音频 · 导出帧'] },
  { id: 'file', name: '文件管理', desc: '搜索 · 批处理 · 压缩', icon: markRaw(FolderOpened), group: 'media', hue: '#0c9c8f', points: ['按名称/类型/大小搜索', '批量复制 · 删除 · 重命名', 'ZIP / 7Z 压缩解压(加密)'] },
  { id: 'webauto', name: '网页自动化', desc: '点选采集 · 自动翻页 · 导出', icon: markRaw(Cpu), group: 'media', hue: '#0a8f6b', points: ['可视化点选要采集的内容', '自动翻页 · 进入帖子详情', '批量提取网页信息', '一键导出 Word / Excel'] },
  { id: 'seal', name: '公章生成', desc: '电子印章制作', icon: markRaw(Stamp), group: 'media', hue: '#d6342f', points: ['圆章 / 椭圆章模板', '自定义文字 · 字号 · 弧度', '导出透明 PNG'] },
  { id: 'system', name: '系统管理', desc: '性能监控 · 启动项', icon: markRaw(Monitor), group: 'system', hue: '#3b7de0', points: ['CPU/内存/磁盘/GPU 监控', '温度 · 电压 · 风扇', '启动项 · 运行时长'] }
]

export const GROUPS = [
  { id: 'media', label: '常用工具' },
  { id: 'system', label: '系统' }
]

export const HOME = { id: 'home', name: '首页', icon: markRaw(HomeFilled) }

// 便捷查询
export const toolById = (id) => TOOLS.find((t) => t.id === id)
