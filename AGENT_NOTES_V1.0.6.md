# PPX_lobechat 功能优化 V1.0.6 – 进度与待办（给后续模型看的自用笔记）

> 状态时间：以当前工作目录 `D:\bc\PPX_lobechat` 为准，已跑过 `python -m py_compile api/*.py` 和 `pnpm -C gui run build`，均通过。

本文件用于在“失忆”后快速恢复上下文，说明：

- 《功能优化文档V1.0.6.md》的需求完成度（后端 / 前端分别看）。
- 关键实现位置。
- 尚未完成或只做了一半的点。

尽量只描述**当前仓库真实状态**，不依赖之前对话记忆。

---

## 1. 功能按模块的当前状态

### 1.1 进程管理（system）

- 文件：
  - 后端：`api/system.py`
  - 前端：`gui/src/components/system/ProcessManager.vue`
- 已完成：
  - `system_listProcesses` 支持 `keyword`（按命令行 / 名称模糊匹配）与 `port` 过滤。
  - 性能优化：只有传 `port` 时才枚举端口连接。
  - 前端 UI 已对接关键字、端口、limit。
- TODO：文档需求基本满足，无明显缺口。

### 1.2 图片处理（image）

- 文件：
  - 后端：`api/image.py`
  - 前端：`gui/src/components/image/ImageTool.vue`

#### 1.2.1 格式转换

- 已完成：
  - 后端 `ImageTool._valid_formats` 包含：`png, jpg, jpeg, webp, bmp, tiff, gif, svg`。
  - 前端“格式转换” Tab 的目标格式下拉包含：`PNG/JPG/GIF/SVG/WEBP/TIFF`。
- TODO：与文档一致，基本 OK。

#### 1.2.2 批量缩放（证件照尺寸）

- 已完成：
  - 前端“批量缩放” Tab：
    - `state.resize.mode` 支持 `percent` / `pixel`。
    - 在 `pixel` 模式下新增证件照预设下拉：
      - 1 寸（295×413）
      - 2 寸（413×579）
      - 小一寸（260×378）
      - 大一寸（390×567）
    - 通过 `photoSizeMap` 和 `watch(state.resize.photoPreset)` 自动填充 `width/height`。
  - 后端缩放逻辑仍按像素/比例工作，与 UI 匹配。
- TODO：如果后续需要更多国家/地区的证件照尺寸，可在 `photoSizeMap` 扩展。

#### 1.2.3 批量水印（平铺 / 旋转）

- 已完成（前端）：
  - `state.watermark` 新增字段：
    - `tile: false`
    - `tileSpacing: 80`
    - `rotation: 0`
  - `runWatermark` 传参中已增加：
    - `tile`, `tileSpacing`, `rotation`
  - “批量水印”面板中新增：
    - “平铺 / 间距”行：
      - `el-switch` 控制是否平铺，文案为“按间距平铺/单个水印”。
      - `el-input-number` 设置 `tileSpacing`（20–600 px，禁用条件为 `!tile`）。
    - “旋转角度”行：
      - `el-slider` 控制 `rotation`（-90~90°，带输入框）。
- 当前后端状态：
  - `image_add_watermark` 目前**仍然只按单点位置渲染一次水印**，尚未根据 `tile/tileSpacing/rotation` 做真正的平铺/旋转渲染。
- TODO（后端必做）：
  - 在 `api/image.py:image_add_watermark`：
    - 若 `tile=True`：
      - 按 `tileSpacing` 对整张图进行网格遍历，重复粘贴文字/图片水印。
    - 水印旋转：
      - 对文字：使用 `Image.rotate` 或先绘制到独立图层再旋转后贴到 overlay。
      - 对图片：对 `wm_resized` 做旋转后再 paste。

#### 1.2.4 裁剪工具（预览 + 拖拽）

- 已完成：
  - `state.crop` 新增：
    - `previewUrl`：本地图片 `file:///` URL，用于 `<img>` 预览。
    - `imageWidth/imageHeight`：原始像素尺寸。
    - `displayWidth/displayHeight`：在预览容器中的显示尺寸。
  - 选图时 `selectSingleImage('crop')`：
    - 自动计算 `previewUrl`。
    - 重置 `crop` 的坐标和尺寸，等待图片加载完成后重算。
  - 新增内部状态：
    - `cropPreviewRef = ref(null)`：预览区域 DOM。
    - `cropInteraction = reactive({ dragging, startX, startY })`：记录拖拽起点。
  - 新增逻辑：
    - `updateCropRectByRatio()`：按原图尺寸 + 当前比例字符串（如 `16:9`）计算居中裁剪框。
    - `updateCropRectFromDisplay()`：将预览中的拖拽矩形映射回原图坐标，更新 `x/y/width/height`。
    - `onCropImageLoaded()`：在 `<img>` 加载完后记录原图/显示尺寸，并根据模式设置默认裁剪框：
      - `mode === 'ratio'`：居中按比例裁剪。
      - `mode === 'custom'` 且尚未设置大小：默认整图。
    - 鼠标事件：
      - `onCropMouseDown/onCropMouseMove/onCropMouseUp`：实现拖拽绘制裁剪框。
  - 模板：
    - 在“裁剪工具”里增加 `v-if="state.crop.file"` 的“预览裁剪”表单项：
      - `<img>` 显示整图。
      - 叠加 `<div class="crop-preview-rect">` 高亮当前裁剪区域。
      - 提示文案：“在图片上拖动绘制裁剪区域，坐标会自动填入上方字段”。
- TODO：
  - 需求基本达成，如需更精准体验，可考虑支持拖动现有框的四角/边缘，而不仅仅是重新绘制。

#### 1.2.5 方向调整（自定义旋转 / 翻转）

- 已完成（背后是上一轮的改动，这里确认）：
  - 后端：`image_rotate_flip` 已支持：
    - `operation='custom'`，并接受 `angle`, `flipHorizontal`, `flipVertical`。
  - 前端：
    - “旋转 / 翻转”页新增 `自定义角度 / 翻转` 选项；
    - 显示角度滑条和水平/垂直翻转勾选。
    - 调用时传上述参数。
- 未完成：
  - 文档要求“增加预览”，目前前端没有对旋转结果做预览，只是显示输出路径。

#### 1.2.6 图片转 PDF（页面尺寸）

- 已完成：
  - 后端 `ImageTool._page_sizes` 中已有：
    - `a3`, `square`, `slide_16_9` 等预设。
  - 前端 ImageTool.vue “图片 → PDF”：
    - 页面尺寸下拉中已加入：
      - `A3` (`a3`)、`正方形` (`square`)、`16:9 投影` (`slide_16_9`)。
- TODO：
  - 文档仅要求增加常见页面尺寸，此处已满足。

---

### 1.3 文本工具（text）

- 文件：
  - 后端：`api/text.py`
  - 前端：`gui/src/components/text/TextTool.vue`
- 已完成：
  - `text_format_json` 在**任意异常**情况下统一返回错误信息：
    - `"不是JSON格式数据"`（通过 `api_error` 封装）。
  - 前端只展示该统一文案，不再暴露 Python trace。

---

### 1.4 视频处理（video）

- 文件：
  - 后端：`api/video.py`
  - 前端：`gui/src/components/video/VideoTool.vue`

#### 1.4.1 视频格式转换 – 原画模式

- 已完成：
  - 后端 `video_format_convert`：
    - 当 `qualityPreset` 为 `origin/original/source/copy` 时：
      - 构造 `ffmpeg ... -c copy`，尽量只做容器转换，不重编码音视频（保持“原画”）。
    - 原有 `high/medium/low` 保持按 CRF（18/22/28）策略。
  - 前端“格式转换”：
    - 质量预设中已加入“原画”按钮（label 中文，value `original`），与后端匹配。

#### 1.4.2 视频压缩 – 预设文案

- 已完成（上一轮）：
  - 前端将 ffmpeg `preset` 文案改为中文描述：
    - 极快（调试用）/ 很快（画质较低）/ 快速（体积较小）/ 均衡（推荐）/ 更好画质（编码更慢）。
  - 传给后端的值仍是 `ultrafast/superfast/fast/medium/slow`，`video_compress` 逻辑未改。

#### 1.4.3 视频截取 – 播放预览 + 拖动时间条

- 已完成（前端 + 与现有后端兼容）：
  - 后端 `video_cut` 早已有 `start/end` 处理逻辑。
  - 前端 `VideoTool.vue`：
    - `state.cut` 新增：
      - `duration`, `rangeStart`, `rangeEnd`, `previewUrl`。
    - 工具函数：
      - `parseTimeToSeconds` / `secondsToTime`：在文本时间与秒数之间转换。
      - `toFileUrl`：视频本地路径转为 `file:///` URL。
    - 引入：
      - `cutVideoRef = ref(null)` 和 `cutRange = computed([...])`。
      - `onCutLoadedMetadata`：从 `<video>` 的 `duration` 初始化区间。
      - `onCutRangeChange`：拖动滑块后，将视频播放进度跳到区间开始。
    - 选文件时：
      - `selectVideo('cut')` 会设置 `previewUrl`，并重置区间与文本时间。
    - 模板：
      - “视频截取”面板顶部增加一块预览：
        - `<video :src="state.cut.previewUrl" controls ... />`
        - `el-slider`（`range` 模式）控制 `[start,end]`。
        - 下方显示：开始时间、结束时间（支持“视频末尾”）、总时长。
  - `runCut` 仍用 `state.cut.start/end` 调后端，无需改动后端接口。

#### 1.4.4 音频导出 – 播放预览（部分完成）

- 当前状态：
  - 后端 `video_extract_audio`：
    - 只接受 `filePath, audioFormat, quality, outputDir` 等参数；
    - **目前未解析 `start/end`**，也没有 `-ss/-t` 支持。
  - 前端：
    - `state.audio` 增加了：
      - `start, end, duration, rangeStart, rangeEnd, previewUrl`。
    - `selectVideo('audio')`：
      - 会设置 `previewUrl` 并重置区间。
    - `runAudio` 已将 `start/end` 文本传给 `video_extract_audio`。
    - **时间轴预览 UI 只完成了一半**：
      - 逻辑函数已有（`audioVideoRef`, `audioRange`、`onAudioLoadedMetadata`, `onAudioRangeChange` 和相应 `watch`），
      - 但模板中的 `<video>` + `el-slider` 预览块在该 Tab 里尚未全部插入成功（由于模板存在乱码，自动 patch 多次失败）。
      - 当前“音频提取”面板仍然是：源视频 + 音频格式 + 质量 + 输出目录 + “提取音频”按钮，没有可视化时间轴。
- TODO：
  1. 在 `VideoTool.vue` 的“音频提取” Tab 中**手工**（编辑器中）加入预览 `<video>` + `audioRange` 滑块 UI，参考“视频截取”的那一段。
  2. 在 `api/video.py:video_extract_audio` 中：
     - 增加 `start/end` 处理逻辑：
       - 若传入 `start`：使用 `-ss start_label`；
       - 若传 `end`：转换为 `duration = end - start` 并加 `-t duration_label`。

---

### 1.5 文件管理（file）

- 文件：
  - 后端：`api/file.py`
  - 前端：`gui/src/components/file/FileTool.vue`

#### 1.5.1 文件搜索 – 使用 fd/fdfind

- 已完成：
  - 后端新增 `_search_with_fd`：
    - 优先尝试 `fd` / `fdfind` 命令：
      - 选项包括 `--hidden --follow --type f --max-results` 等，
      - 再用 `_match_common_filters` 做二次过滤。
    - 若系统不存在 `fd`，或命令失败，则回落到 Python 遍历。
  - `file_search` 先尝试 `_search_with_fd`，失败再用原逻辑。
  - 前端调用接口保持不变。

#### 1.5.2 压缩/解压密码 – ZIP/7Z

- 已完成：
  - `file_compress`：
    - `fmt='zip'` 且有 `password` 时：
      - 优先调用 `7z/7za/7zz` 创建 `ZipCrypto` 加密 ZIP。
      - 若 7-Zip 不存在，抛出环境错误提示。
    - `fmt='7z'`：
      - 使用 `py7zr.SevenZipFile(..., password=password)`。
  - `file_decompress`：
    - ZIP 使用标准库 `ZipFile.extractall(pwd=...)`。
    - 7Z 使用 `py7zr`，已支持密码。
  - 前端：
    - “压缩”卡片已有 `password` 字段并传给后端；
    - “解压”卡片已有密码输入传给 `file_decompress`。

---

### 1.6 PDF 工具（pdf）

- 文件：
  - 后端：`api/pdf.py`
  - 前端：`gui/src/components/pdf/PdfTool.vue`

#### 1.6.1 PDF → 图片（高清图）

- 后端（已存在逻辑，当前确认）：
  - `_image_formats` 覆盖了 `png/jpg/tiff/webp`，并据此前修改应已包含 `gif/svg`（需要手动确认）。
  - `pdf_convert_to_images`：
    - 对 `format='svg'` 使用 `page.get_svg_image` 输出矢量 SVG。
    - 其他格式使用 `get_pixmap` + DPI。
- 前端（本轮新增）：
  - `state.toImage`：
    - 添加 `dpiPreset: 'ultra'`，`dpi: 400`。
  - 脚本：
    - 新增 `toImageDpiPresetMap = { ultra: 400, high: 300, standard: 200 }`。
    - `watch`：
      - 当 `dpiPreset` 为 `ultra/high/standard` 时自动覆盖 `dpi`。
      - 若用户手动修改 `dpi` 且与当前预设不一致，则将 `dpiPreset` 调整为 `'custom'`。
  - 模板“PDF 转高清图片” Tab：
    - “分辨率 (DPI)”表单项变为：
      - 上侧：`el-radio-group`（超清 / 高清 / 标清 / 自定义）。
      - 旁边：`el-input-number` 控制实际 `dpi`，仅在“自定义”时启用。
      - 下方一行 `p.dpi-hint` 文案说明 DPI 与清晰度/体积关系，并推荐：
        - 超清 400 DPI、高清 300 DPI、标清 200 DPI。
    - “图片格式”下拉新增：
      - `GIF`（`gif`）、`SVG`（`svg`）。

#### 1.6.2 PDF 合并 – 每个文件的页码选择（前端部分完成）

- 后端当前状态：
  - `pdf_merge` 仍按“整个文档”合并，不解析每个文件的页码。
    - 入口参数 `files` 目前只看 path。
- 前端改动：
  - 选文件（`selectPdf('merge', true)`）：
    - 对每个返回的 item 进行浅拷贝，并补充 `pageSpec: ''` 字段后 push 到 `state.merge.files`。
  - 合并列表 `<el-table>`：
    - 在序号后新增一列“页码选择”：
      - 每行一个 `el-input size="small"` 绑定 `scope.row.pageSpec`；
      - 提示文本形如“如 1-3,5,8”。
  - 调用 `runMerge`：
    - 参数改为：
      - `files: state.merge.files.map(item => ({ path: item.path, pageSpec: item.pageSpec || '' }))`
- TODO（后端必须完善）：
  - 在 `api/pdf.py:pdf_merge`：
    - 支持 `files` 数组元素为 `{ path, pageSpec }` 或直接字符串：
      - 若是 dict：
        - 用 `path` 定位 PDF。
        - 用 `pageSpec` 解析页码集合；为空则默认为全部页。
      - 若是字符串：
        - 兼容旧行为，合并全部页。
    - 汇总合并总页数，返回 `mergedPages` 等信息（可选）。

#### 1.6.3 拆分 PDF / 页码切割

- 现状：
  - `split` Tab：按固定页数拆分，调用 `pdf_split`。
  - `cut` Tab：按自定义页码区间切割，调用 `pdf_cut`。
  - 两个 Tab 在功能上已经分别实现“按固定页数拆分”和“按页码拆分”。
- TODO（UI 层面）：
  - 按文档需求，可以通过说明文案或视觉上将两者归为“拆分模式”的不同选项，而不是完全独立功能。
  - 功能本身问题不大，主要是用户认知上的统一。

#### 1.6.4 页面重排

- 现状：
  - `reorder` Tab：
    - 用户手工填写 `state.reorder.orderText`（如 `3,1,2`）作为新顺序。
    - 有“自动追加剩余页码”选项。
  - 无页面缩略图预览 / 拖拽。
- TODO：
  - 需求是“支持预览 PDF，并在预览中拖拽调整顺序”。
  - 建议：
    - 新增一个缩略图网格（可调用 `pdf_convert_to_images` 生成小尺寸 PNG）。
    - 利用前端拖拽库或原生 `dragstart/drop` 实现顺序调整。
    - 将最终顺序转为 `orderText` 或直接传数组给 `pdf_reorder_pages`。

#### 1.6.5 图片转 PDF（PDF 工具中的 imagePdf）

- 现状：
  - `state.imagePdf` + 对应 Tab 已存在，功能上等价于 ImageTool 的“图片 → PDF”。
  - 当前未显式“跳转/提示”两者是同一类功能。
- TODO：
  - 可在 PDF 工具的“图片合集转 PDF”页增加一行说明：
    - 例如“与图片工具中的 图片转 PDF 功能等价”，并可加一个按钮调用 ImageTool 抽屉。

#### 1.6.6 PDF 转 Word

- 当前仓库状态：
  - `api/pdf.py` 中**尚未找到** `pdf_to_word` 函数（可以再次用 `rg "pdf_to_word" api/pdf.py` 确认）。
  - 前端 `PdfTool.vue` 也没有相应 Tab。
- TODO（完整新功能）：
  1. 后端：
     - 在 `api/pdf.py` 新增 `pdf_to_word(self, options: Dict | None = None)`：
       - 读取 PDF 文本，支持 `textMode: plain/markdown/html` 三种模式（与文档一致）。
       - 生成最小 docx 结构（`[Content_Types].xml`, `_rels/.rels`, `word/document.xml` 等），打包为 `.docx`。
       - 返回 `code=0, msg, output, outputDir`。
  2. 前端：
     - 在 PdfTool.vue 中新增 Tab“PDF 转 Word”：
       - 文件选择 + 输出目录 + 文本模式单选（plain/markdown/html）。
       - 调用 `callApi('pdf_to_word', {...})`，并提供“打开文件”按钮（用 `system_pyOpenFile`）。

#### 1.6.7 OCR 识别

- 按文档标注为“后期功能”，当前未有实现，也暂不在本轮范围。

---

### 1.7 公章生成（seal）

- 文件：
  - 后端：`api/seal.py`
  - 前端：`gui/src/components/seal/SealTool.vue`

#### 1.7.1 导出报错修复

- 状态：
  - `seal_generate` 已使用 `_resolve_output_path(config)`，不再有“resolve output path() missing 2 required positional arguments” 的问题。

#### 1.7.2 敏感功能密码门禁

- 前端：
  - 使用常量密码 `Jd_251114` 控制访问：
    - `state.locked`，`state.password`，`state.passwordError`。
    - 抽屉打开时先显示密码输入；验证通过后才展示原有配置 + 预览。
  - `watch(props.modelValue)`：
    - 只有在 `!state.locked && !state.preview` 时才自动调用 `runPreview()`。
  - **本轮新增**：
    - `resetDefaults()` 现在会检查锁定状态：
      - 原来：重置默认配置后，只要抽屉开着就直接 `runPreview()`，即使锁定状态也会触发预览生成。
      - 现在：只有在 `props.modelValue && !state.locked` 时才执行 `runPreview()`，避免绕过密码门禁。
- 后端：
  - 尚未添加审计/日志功能，不是本轮必需。

---

### 1.8 软件图标统一

- 文件：
  - Web favicon：`gui/index.html`
  - 打包脚本：`pyapp/spec/getSpec.py`, `pyapp/package/**`（未详细检查）
  - logo 文件：项目根 `logo.png`
- 状态：
  - `gui/index.html` 中的 `<link rel="icon" href="/logo.ico">` 已改为 `/logo.png`。
  - deb 打包脚本使用的是 `pyapp/icon/logo.png`（或相关路径），Windows/Mac 仍指向 `.ico/.icns`，假定由 `logo.png` 转换产生。
- TODO（如要“完全统一”）：
  - 在打包脚本中添加逻辑，用 Pillow 或其他工具将根目录 `logo.png` 自动转换生成 `.ico/.icns` 到 `pyapp/icon/`，保持单一源图。

---

## 2. 下一步建议的工作清单（给后续模型）

按优先级大致排序：

1. **图片批量水印后端补完**
   - 文件：`api/image.py:image_add_watermark`
   - 目标：
     - 实现 `tile/tileSpacing` 布局（整幅图片平铺）。
     - 实现水印旋转（文字 + 图片）。

2. **视频音频提取的时间轴预览 + 后端时间段导出**
   - 文件：
     - 前端：`gui/src/components/video/VideoTool.vue`
     - 后端：`api/video.py:video_extract_audio`
   - 目标：
     - 在“音频提取” Tab 中，手动插入视频预览 + `audioRange` 滑块 UI。
     - 后端根据 `start/end` 文本参数加上 `-ss/-t` 支持，只导出指定区间的音频。

3. **PDF 合并 – 按每个文件页码选择**
   - 文件：
     - 后端：`api/pdf.py:pdf_merge`
     - 前端：`gui/src/components/pdf/PdfTool.vue`（已收集 `pageSpec`）
   - 目标：
     - 支持 `files` 数组项为 `{path, pageSpec}`；
     - 正确解析 `pageSpec`，按页号合并；
     - 可选：返回 `mergedPages` 供前端展示。

4. **PDF 转 Word 功能**
   - 文件：
     - 后端：`api/pdf.py` 新增 `pdf_to_word`
     - 前端：`gui/src/components/pdf/PdfTool.vue` 新增 Tab
   - 目标：
     - 最小工作版即可：按文档抽文本，生成段落型 docx。

5. **PDF 页面重排可视化**
   - 文件：
     - 前端：`PdfTool.vue` 的 `reorder` Tab
     - 后端：`api/pdf.py:pdf_reorder_pages`（假设已有）
   - 目标：
     - 使用缩略图列表 + 拖拽排序，自动生成 `orderText` 或直接生成数组传给后端。

6. **拆分 PDF / 页码切割 UI 合理化**
   - 文件：
     - 前端：`PdfTool.vue` 中 `split` 与 `cut` 两个 Tab
   - 目标：
     - 不一定要合并代码，但可以增加清晰的文案说明，让用户理解两个模式。

7. **图标与打包脚本统一（可选）**
   - 文件：
     - `pyapp/spec/getSpec.py`, `pyapp/package/**`
   - 目标：
     - 确保桌面端所有入口（exe、dmg、桌面快捷方式）都基于根目录 `logo.png` 统一生成。

---

## 3. 使用仓库时的一些注意事项

1. **中文乱码问题**
   - 很多 Vue 模板和部分字符串在文件里是乱码（例如 `λ��` 等），但浏览器里能正常显示。
   - 使用 `apply_patch` 做文本替换时容易匹配不上，建议：
     - 精确到一小段上下文再 patch；
     - 或直接在编辑器里手改再由工具整体写回。

2. **前端 API 调用约定**
   - 默认通过 `window.pywebview.api.*` 调用后端：
     - 常见的文件/目录选择封装：
       - `system_pyCreateFileDialog(filter)`
       - `system_pySelectDirDialog(currentDir)`
       - `system_pyOpenFile(path)`
   - 新增功能时，优先复用这些已有 helper。

3. **构建与检查**
   - Python 语法检查：
     - `Get-ChildItem api -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }`
   - 前端构建：
     - `pnpm -C gui run build`
   - 若改动较多（尤其是模板），建议每轮改完跑一次。

4. **错误提示文案风格**
   - 文档与 UI 均使用简洁中文，错误信息尽量统一、面向用户，不暴露内部栈信息。
   - 例如 JSON 工具统一用“不是JSON格式数据”。

---

这个文件的作用，就是在你“失忆”之后，只要打开 `AGENT_NOTES_V1.0.6.md`，就能快速知道：

- 当前仓库到底完成了哪些功能（而不是需求文档里写的那些）；
- 哪些地方前端已经接好了但后端还没实现；
- 下一步优先从哪里下手。

后续模型如果有新的大块改动，也可以在本文件末尾继续追加版本小节（例如“2025-11-20 更新：xxx”），保持这个笔记是**事实的单一来源**。 

---

## 4. 2025-11-14 更新（本轮由 Codex 执行）

### 4.1 图片批量水印
- 后端：`api/image.py:image_add_watermark`
  - 新增 `tile` / `tileSpacing` / `rotation` 参数支持：
    - `tile=true` 时按间距在整张图上平铺文字或图片水印；
    - 对文字水印先绘制到独立 RGBA 图层，再整体旋转和平铺；
    - 对图片水印在缩放并按透明度处理后整体旋转和平铺。
- 前端：`gui/src/components/image/ImageTool.vue`
  - 将“平铺 / 间距”“旋转角度”表单项从“格式转换”页移回“批量水印”页，并继续使用 `state.watermark.tile/tileSpacing/rotation` 传参。

### 4.2 视频音频提取区间
- 后端：`api/video.py:video_extract_audio`
  - 新增 `start/end` 解析逻辑，使用 `parse_timespan` 转为 `-ss/-t`，支持只导出选定时间段的音频；
  - 当 `end <= start` 且 `end` 非 0 时抛错，防止无效区间。
- 前端：`gui/src/components/video/VideoTool.vue`
  - “音频提取”页新增 `<video>` 预览和双端滑块 `audioRange`，使用 `audioVideoRef`、`onAudioLoadedMetadata`、`onAudioRangeChange` 联动；
  - 文本框 `state.audio.start/end` 与滑块双向同步，调用 `runAudio` 时一并传给后端。

### 4.3 PDF 合并按文件页码选择
- 后端：`api/pdf.py:pdf_merge`
  - `files` 支持两种形式：
    - 字符串：按整份 PDF 全部页合并（兼容旧版本）；
    - 字典 `{ path, pageSpec }`：按每个文件的 `pageSpec`（如 `1-3,5,8`）解析页码集合合并；
  - 跳过 `pageSpec` 为空或解析结果为空的条目；
  - 返回值中增加 `mergedPages`，表示实际合并的页数。
- 前端：`gui/src/components/pdf/PDFTool.vue`
  - 之前已在“合并 PDF”表格中增加 `pageSpec` 输入列，本轮验证与新后端逻辑匹配，无需再改动。

### 4.4 PDF 转 Word 功能
- 后端：`api/pdf.py`
  - 利用已有 `_write_simple_docx`，新增 `pdf_to_word`：
    - 参数：`filePath`, `outputDir`, `textMode`（`plain/markdown/html`）；
    - 遍历所有页，按 `textMode` 使用 `page.get_text()` 提取文本，每行作为一个段落写入 docx；
    - 输出目录为 `<源文件名>_word/`，文件名默认 `<源名>.docx`，返回 `output` 与 `outputDir`。
- 前端：`gui/src/components/pdf/PDFTool.vue`
  - `state` 中新增 `word` 分支（`file/textMode/outputDir/output`）；
  - 新增 Tab “PDF 转 Word”（`name="word"`）：
    - 支持选择 PDF、选择文本模式（纯文本 / Markdown / HTML）、选择输出目录；
    - 点击“转换为 Word”调用 `pdf_to_word`，并在结果区域展示可点击打开的输出路径。

### 4.5 构建与校验
- 后端：已执行 `python -m py_compile api/*.py`，全部通过；
- 前端：已执行 `pnpm -C gui run build`，打包成功（Vite 4.x）。

### 4.6 仍未覆盖的 TODO（延续第 2 节）
- PDF 页面重排：仍为纯文本 `orderText` 输入，尚未实现缩略图预览 + 拖拽排序；
- 拆分 PDF / 页码切割：UI 仍为两个 Tab，暂未做模式合并，仅文案略显抽象；
- 图标统一：打包脚本仍未改为统一从根目录 `logo.png` 生成 `.ico/.icns`。

---

### 4.7 2025-11-14 （前端补充：PDF 页面重排 / 拆分 UI / 图片转 PDF 说明）

- 前端：`gui/src/components/pdf/PDFTool.vue`
  - “页面重排” Tab：
    - 去掉了原来的“页码顺序”手动输入框，保留 `state.reorder.orderText` 仅作为内部辅助。
    - 新增 `state.reorder.pages`、`reorderDragState`、`loadReorderPreview` 等状态与方法：
      - 调用 `pdf_convert_to_images` 生成小尺寸 PNG 预览图列表。
      - 在表单中加入可拖拽缩略图网格（原生 HTML5 drag & drop），通过拖动缩略图调整顺序。
      - `runReorder` 优先根据 `pages` 生成新的顺序数组并传给 `pdf_reorder_pages`，仍兼容旧的 `orderText` 字符串逻辑。
  - “拆分 PDF / 页码切割” Tab：
    - 未改动后端 `pdf_split` / `pdf_cut` 行为，只调整标题和说明文案，明确这是“拆分模式一（按固定页数）/ 拆分模式二（按页码摘取）”两种模式。
  - “图片转 PDF” Tab：
    - 在 header 下方增加一行说明文本，提示该功能与图片工具中的“图片转 PDF”等价，这里仅提供一个快捷入口（仍调用 `pdf_images_to_pdf`）。

- 校验：
  - 再次执行 `python -m py_compile api/*.py` 与 `pnpm -C gui run build`，均通过。
### 4.8 2025-11-14 （PDF 页码多文件拆分功能补齐）

- 后端：`api/pdf.py`
  - 新增 `pdf_multi_cut(self, options)`：
    - 入参与 `pdf_cut` 基本一致，主要使用：`filePath`、`outputDir`、`outputName`、`mode`、`pageSpec`。
    - 仅支持 `mode='custom'`：否则直接抛错提示“多文件切割仅支持自定义页码模式”。
    - 将 `pageSpec` 按“换行或分号”拆分为多个区间字符串，每个区间内部仍沿用原有 `1-3,5,8` 语法并复用 `_parse_page_spec`。
    - 为每个非空区间创建一个新的 `PdfWriter`，按区间页码生成单独的 PDF：
      - 输出目录优先使用 `outputDir`，否则调用 `_ensure_output_dir(source, '', 'cut')` 在源文件旁创建 `*_cut` 目录。
      - 输出文件名规则：`<outputName 或 源文件名>_part01.pdf`、`_part02.pdf`……；若 `outputName` 已带 `.pdf` 后缀，会去掉后缀再追加 `_partXX`。
    - 返回结构：`{ code: 0, msg, files: [..], outputDir }`，其中 `files` 为所有生成文件的完整路径列表。

- 前端：`gui/src/components/pdf/PDFTool.vue`
  - `state.cut` 结构扩展：
    - 新增 `multi: false` 控制是否按多个区间导出多个 PDF；
    - 新增 `outputs: []` 保存多文件模式下的返回文件列表。
  - “页码切割” Tab：
    - 将“页码列表”输入框改为多行 textarea，placeholder 提示“示例：1-3,5,8；支持用分号或换行分隔多个区间”。
    - 在 `mode === 'custom'` 时增加一个勾选项：`按多个区间分别导出多个 PDF 文件`（绑定 `state.cut.multi`）。
    - 结果展示区支持单文件和多文件两种情况：
      - 若 `state.cut.outputs` 非空，则遍历该数组生成多个可点击 `el-tag`；
      - 否则退回到单个 `state.cut.output` 的行为。
  - 调用逻辑：
    - `runCut` 现在根据 `mode` 和 `multi` 决定调用 `pdf_cut` 还是 `pdf_multi_cut`：
      - 组装 `payload`（`filePath/outputDir/outputName/mode/startPage/endPage/pageSpec`）。
      - 当 `mode==='custom' && multi===true` 且 `pageSpec` 非空时，调用 `pdf_multi_cut`；否则继续调用 `pdf_cut`。
      - 解析返回：优先使用 `res.files` 填充 `state.cut.outputs`，并将第一个文件写入 `state.cut.output` 以兼容旧 UI；无 `files` 时保持原来只读 `res.output` 的逻辑。

- 校验：
  - 执行 `python -m py_compile api/*.py` 与 `pnpm -C gui run build`，均通过。
### 4.9 2025-11-14 （图片裁剪拖拽手柄 / 旋转预览、PDF 预览性能小优化）

- 图片裁剪：`gui/src/components/image/ImageTool.vue`
  - 裁剪框拖拽增强：
    - 在现有拖拽绘制矩形的基础上，为裁剪框四角与四边增加 8 个“控制手柄”（`crop-handle-*`），支持从边缘/角拖动调整尺寸。
    - 新增 `getCropDisplayRect()` 帮助函数，将当前裁剪框从图像坐标转换为预览区域中的像素矩形，用于计算锚点和拖拽目标点。
    - 新增 `onCropHandleMouseDown(position, event)`：
      - 根据手柄位置（nw/ne/sw/se/n/s/w/e）选择裁剪框对角或边中点作为锚点；
      - 将锚点写入 `cropInteraction.startX/startY`，当前光标位置作为另一点，调用 `updateCropRectFromDisplay` 重用原有逻辑完成重算。
    - `crop-preview-rect` 允许 pointer-events，内部的 8 个手柄使用整数 px 定位 + CSS cursor 类型（nwse-resize 等）增强可视反馈。
  - 防抖调整：
    - `updateCropRectFromDisplay` 若 `startX === currentX && startY === currentY`，直接返回，避免点击手柄时生成 1px 宽高的无意义矩形。

- 图片旋转预览：`gui/src/components/image/ImageTool.vue`
  - 新增计算属性：
    - `rotatePreviewUrl`：自动取 `state.rotate.files` 中第一张图片，通过已有的 `getFileUrl` 生成本地 file:/// 预览地址。
    - `rotatePreviewStyle`：根据 `state.rotate.operation`、`angle`、`flipHorizontal`、`flipVertical` 组合生成 CSS `transform`：
      - `rotate90/180/270` → 固定 `rotate(...)`；
      - `mirror/flip` → `scaleX(-1)` / `scaleY(-1)`；
      - `custom` → 自定义角度 + 可选水平/垂直翻转。
  - 在“旋转 / 翻转”Tab 中，操作表单下方增加预览块：
    - 若存在首张图片，则显示“效果预览（仅示意首张图片，不落盘）”，并用 `rotatePreviewStyle` 实时渲染 `<img>` 的旋转/翻转效果，交互时立刻可见。

- PDF 页面重排预览性能：`api/pdf.py` + `gui/src/components/pdf/PDFTool.vue`
  - 后端 `pdf_convert_to_images`：
    - 增加可选参数 `maxPages`：
      ```python
      max_pages = int(opts.get('maxPages') or 0)
      ...
      total_pages = doc.page_count
      limit = total_pages if max_pages <= 0 else min(total_pages, max_pages)
      for index in range(limit):
          ...
      ```
    - 默认调用（如“PDF 转高清图”）不传 `maxPages`，仍导出全部页；仅在重排预览中限制。
  - 前端 `PDFTool.vue`：
    - `loadReorderPreview` 调用 `pdf_convert_to_images` 时增加 `maxPages: 80`，重排预览最多生成前 80 页的缩略图，避免在极大文档上一次性生成所有页的代价。
    - 文案提示更新为“生成后可在下方拖动页面缩略图调整顺序（当前预览最多前 80 页）”，明确行为边界。

- 校验：
  - 本轮修改后再次执行 `python -m py_compile api/*.py` 与 `pnpm -C gui run build`，均通过。
