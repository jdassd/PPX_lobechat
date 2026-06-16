# V1.0.4 Phase 2 开发记录

## 阶段目标
- 在 Phase 1 P0 能力基础上补全设计文档列出的 P1 级功能，覆盖图片水印/裁剪/旋转、文本正则与数据转换、视频音频提取与帧导出、文件批量操作与去重。
- 保持 Python API 与 Vue 前端的一致性，确保桌面端 pywebview 可以直接调度新增接口。

## 本次交付内容

### 后端能力
1. **图片工具（`api/image.py`）**
   - 新增 `image_add_watermark`、`image_crop`、`image_rotate_flip`、`image_to_pdf`，支持文字/图片水印、自由/比例裁剪、旋转翻转及多图合成 PDF。
2. **文本工具（`api/text.py`）**
   - 新增 `text_regex_match`、`text_convert_csv_json`、`text_deduplicate_sort`、`text_timestamp_convert`，覆盖正则匹配/替换、CSV/JSON 文件互转、去重排序与时间戳/时区转换。
3. **视频工具（`api/video.py`）**
   - 新增 `video_extract_audio`、`video_extract_frames`、`video_get_info`，基于 FFmpeg/ffprobe 提供音频抽取、帧图导出与媒体信息解析。
4. **文件工具（`api/file.py`）**
   - 新增 `file_batch_copy`、`file_batch_delete`、`file_batch_rename`、`file_deduplicate`，支持按条件复制/删除/重命名文件及基于内容或文件名的去重扫描。

### 前端界面
1. **ImageTool**：追加水印、裁剪、旋转和图片转 PDF Tab，表单支持透明度、位置、比例等参数，结果面板可直接打开文件/目录。
2. **TextTool**：引入正则工具、CSV/JSON 转换、去重排序、时间戳转换 Tab，并对原有卡片文案与阶段标签升级为 Phase 2。
3. **VideoTool**：新增“音频提取”“帧图导出”“视频信息”三个 Tab，支持音频格式/质量选择、帧输出目录及视频参数展示。
4. **FileTool**：新增批量复制、删除、改名、文件去重 Tab，配套目录选择、过滤条件、预览/执行结果与统计信息。
5. **首页卡片**：更新图片/文本/视频/文件四个入口的描述与亮点，突出 Phase 2 新增功能。

## 验证建议
1. **通用**：运行 `pnpm run start` 启动桌面端，确保 pywebview API 可用；视频相关功能需本地已安装 FFmpeg/ffprobe。
2. **图片**：使用若干 PNG/JPG 测试添加文字/图片水印、裁剪比例、旋转与 PDF 合成，检查输出目录与预览链接。
3. **文本**：输入带正则命中的文本、CSV/JSON 文件、长文本列表与时间戳，确认后端返回的匹配/转换/统计结果与提示信息。
4. **视频**：用示例 MP4 调用音频提取、帧图导出（time/frame 两种模式）及信息获取，观察输出路径与 ffprobe 数据。
5. **文件**：在临时目录准备测试文件，验证复制/删除/改名/去重操作的过滤、预览以及冲突/回收站策略，再确认 ZIP/7Z 功能无回归。

## 后续展望
- Phase 3 将聚焦高级图片拼接/批量命名、文本批量替换/Unicode 工具、视频合成/GIF、文件分类整理等 P2 需求。
- 视 FFmpeg 与 TinyDB 的实际部署情况，评估在 `pnpm run init` 中添加依赖检测与提示。
