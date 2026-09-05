# PPX 重构实施与验收记录

六阶段涉及的主要代码已接入现有应用。按用户后续明确要求，本次升级为 v2.8.0 并推送标签触发 GitHub 正式发版；三平台安装、升级和逐功能人工验收尚未全部完成，验收记录保持 pending，不将发版等同于全部验收通过。

## 已实施

| 范围 | 现在的行为 | 主要实现 |
| --- | --- | --- |
| 桌面接口与基础故障 | 桌面 API 通过独立服务实例委托调用；保留非导图旧方法名，PDF、Word、印章辅助方法互不覆盖。修复 Word 默认后缀及仅设置输出目录的情况。 | `api/api.py`、`api/word.py`、`api/seal.py` |
| 导图退役 | 删除入口、前后端代码、打包静态资源及专用依赖；清理旧导图收藏和最近使用项；SQLAlchemy 等共享依赖继续保留。未删除用户的导图文件或数据库。 | 导航配置、收藏迁移、依赖清单、打包资源过滤 |
| 公共操作底座 | 61 个动作具备字段描述、依赖、预览和执行信息；明确输出资产；旧入口映射到动作；复杂操作在可终止子进程中运行。 | `api/operations.py`、`api/operation_catalog.json`、`api/core/` |
| 任务与历史 | 排队、运行、取消中、成功、部分成功、失败、已取消、中断八种状态；逐文件/页面结果；统一轮询；队列暂停只阻止新任务。批量图片、转换、目录文件、PDF 页面、采集和工作流均可跳过已完成部分重试。 | `api/tasks.py`、`gui/src/utils/taskCenter.js`、`TaskItemResults.vue` |
| 持久化与迁移 | 任务、工作流和采集记录进入带版本的 SQLite 存储；旧 JSON 导入可重复执行并保留原文件；数据库迁移前一致性备份；启动发现未完成任务时标记中断。 | `api/core/store.py`、`api/core/database.py` |
| 工作区与结果交接 | 大模块按需加载并缓存；参数草稿、预览、结果在切换时保留；重启恢复非敏感配置；共享队列支持追加、移除、排序、批选和分页；预设保存；结果按目标模块交接，避免其他工具误用待接收文件。 | `gui/src/App.vue`、`workspace.js`、共享组件 |
| 文档转换 | 按格式分组或逐文件设定目标；重复转换入口进入转换中心；统一输出检查、独立文件失败反馈及重试。 | `api/format_center.py`、转换中心 |
| PDF | 缩略图按 24 页加载并限制缓存；千页文件可生成结果；批选、拖动排序、旋转、删除、撤销、重做；提交前检查源文件变化；图像/扫描输出按页隔离失败并可单页重试。 | `api/pdf.py`、`PageWorkbenchPanel.vue` |
| Word | 结构按段落和表格行显示，提供 LibreOffice 分页预览；拆分保留所选表格行、重复表头、分节版式及继承的页眉页脚。对于落在跨页段落或跨页单个表格行内部的截断，明确拒绝，避免输出范围错误。 | `api/word.py`、`WordPreview.vue` |
| Excel | 只读分页预览；保留数字、日期、文本前导零及显示格式；数值排序；区分数值和文本分组；表头选择、字段映射、清洗样本对比；公式可选择保留或读取缓存值。 | `api/excel.py`、Excel 工具 |
| 图片、视频、OCR、印章 | 图片效果预览和批量应用；视频时间段预览、编码检查、真实进度、异规格合并规范化；OCR 整页方向校正、低置信度标记、表格人工修正与导出；印章预览和导出使用相同渲染及纹理随机种子，补齐椭圆模板。 | `api/image.py`、`api/video.py`、`api/ocr.py`、`api/seal.py`、对应面板 |
| 文件与文本 | 文件整理预演、冲突处理、原子输出、回收与撤销记录；记录在操作前落盘；撤销保留已经被修改的文件。文本差异可定位；文本工具参数和内容保留当前草稿。 | `api/file.py`、`api/core/journal.py`、文件/文本面板 |
| 工作流、采集与检索 | 工作流可通过动作表单、文件选择器、字段映射和前序输出引用编排；保留高级 JSON；失败续跑复用成功步骤；触发器排除自身输出。采集支持点选、样本、正式执行和历史导出，保留会话并仅重试失败详情。索引支持增量更新、OCR、页码/行号/段落定位及来源变化提示。 | `api/workflow.py`、`api/webauto.py`、`api/document_index.py`、对应面板 |
| 维护与交付 | SQLite 备份包含 WAL 中已提交数据；恢复校验、启动前应用和失败回退；旧 JSON 备份可导入当前状态库；可选依赖独立检测；保留诊断只读边界。统一使用 Python 3.10；Windows 安装更新不再先清空目录或卸载旧版。 | `api/maintenance.py`、`pyapp/package/`、CI |

## 使用与兼容规则

- **输出**：处理先写临时文件，成功后提交；默认生成新文件，名称冲突自动避让。失败或取消保留已经提交的结果；任务中心可逐项检查。
- **取消**：普通批次在文件/页间检查；阻塞型操作由独立进程执行，超出取消宽限期后终止该进程及其子进程。暂停队列不会暂停正在运行的任务。
- **重试**：使用原始输入计划和逐项记录，避免目录重试意外纳入新文件；工作流重试检查步骤签名和已完成输出是否存在，配置已变化则要求重新运行。
- **Excel 公式**：支持安全的同一行相对引用随行移动。跨行、绝对引用、跨表引用等不能可靠重写时返回明确错误；缓存值模式要求源文件已有计算缓存，不会把公式文本当数值。
- **Word 页码**：页码依赖本机 LibreOffice 排版。将标记版与原版的页数和文字分布比较，检测标记改变排版的情况；不把段落计数假装成页码。跨页段落/表格行内部的视觉切割仍应使用 PDF 工具。
- **预览**：PDF 缩略图、Excel 预览和结构列表分页；查询/预览不生成普通历史任务。图片、Word 和媒体预览仍需要完成单个样本的引擎处理。
- **数据**：旧 JSON 原文件和迁移前备份保留；升级备份在用户数据目录的 `upgrade-backups`；历史输出文件不会随清理任务记录被删除。已退役导图的用户数据仍留在原位置。
- **依赖**：LibreOffice、FFmpeg、OCR、浏览器能力按模块检查。OCR 自动方向主要面向横排文档；竖排、多方向混排文档应通过显式方向参数和预览核对。

## 本机验证

环境：Windows，Python **3.10.20**。原有 Python 3.13 虚拟环境保留；新启动器拒绝使用不匹配的 Python 版本。本机具备 LibreOffice、FFmpeg/ffprobe、RapidOCR 和 Edge。

| 检查 | 结果 |
| --- | --- |
| `pnpm test` | 65 项 unittest 通过，保留原有 34 项并补充真实桌面 API、输出正确性、迁移和故障回归 |
| `pnpm lint` | 前端 0 错误、91 条风格警告；Python Ruff 通过 |
| `pnpm -C gui run build` | 生产构建通过 |
| `pnpm test:e2e` | 浏览器连接真实 API/工作进程：草稿、参数恢复、部分失败、失败重试、结果交接、千页 PDF 编辑导出、两步骤表单工作流、队列暂停/取消；所有模块加载无页面脚本错误 |
| 网页采集集成验证 | 受控浏览器页面与真实采集器：单条详情失败、只重试失败请求、无重复记录、登录失效和关闭会话反馈；历史结果分开保存 |
| 原生引擎 | LibreOffice 真分页切割、FFmpeg 小数时间裁剪和异规格视频合并回归通过；RapidOCR 从旋转图片识别 `PPX DOCUMENT 12345`，自动纠正为 270°，置信度约 0.9999 |
| 规模 | 1000 页 PDF 按需缩略图和导出、100000 行 Excel 的限定预览（测试峰值内存门槛 64 MiB）、1000 个文件含空文件复制通过 |
| 数据/故障 | WAL 一致性备份、迁移失败回退和重复迁移、旧备份恢复、公式保护、文件冲突与撤销、原子写失败、取消、部分结果保留通过 |
| 原生桌面源码启动 | 生产前端 + 真实 Pywebview 桥接 + 独立工作进程 + SQLite 状态 + 图片尺寸/透明度检查通过 |
| Windows 打包 | 最终 PyInstaller 与 Inno Setup 构建通过；冻结程序的前端、真实桥接、61 个动作、独立工作进程和输出校验通过；打包资源排除导图及开发数据库 |

验证输出保存在 `build/verification/`，该目录不提交到仓库。CI 在 Windows、macOS、Linux 上配置了静态检查、unittest、浏览器流程和打包，并上传浏览器验证证据。上述本机检查发生在标签推送之前，远端三平台构建结果以 GitHub Actions 为准，不能把工作流配置视为三个平台已经通过。

重构验证结果及当时安装包 SHA-256：`build/verification/validation.json`。验证阶段的本地安装包仍带 2.7.0 版本号；v2.8.0 正式安装包由 GitHub Actions 基于对应标签重新构建，请从 v2.8.0 Release 获取，不要用较早的本地验证包替代。

可复验命令（项目根目录）：

```bash
pnpm lint
pnpm test
pnpm test:e2e
node pyapp/package/python.js tests/e2e/native_ocr.py
pnpm -C gui run build
node pyapp/package/python.js main.py --desktop-smoke build/verification/desktop-source.json
```

独立 Windows 候选包目录：

```bash
node pyapp/package/python.js pyapp/spec/getSpec.py --output-root build/refactor-delivery
node pyapp/package/python.js -m PyInstaller --noconfirm --clean pyapp/spec/windows-folder.spec
node pyapp/package/python.js pyapp/package/exe/getIss.py --output-root build/refactor-delivery
pyapp/package/exe/InnoSetup6/ISCC.exe pyapp/package/exe/InnoSetup.iss
```

## 尚未满足的完整发布门槛

1. **三平台真实安装与升级验收**：macOS/Linux 尚未在原生系统构建、安装和运行；Windows 尚未执行安装器首次安装、旧版原位升级、卸载及用户数据保留验证。打包成功和隐藏窗口桥接检查不能替代这些步骤。
2. **逐功能真实数据验收**：每个保留动作需要正常、失败、结果核对记录。当前自动化覆盖关键链路与风险场景，尚未覆盖所有文件变体、办公文档版式、媒体编码器和实际网站登录流程。
3. **真实升级、退出与恢复联测**：已有文件/数据库级回归，还需在安装后的应用中执行恢复后首次启动、升级回退、系统重启、进程异常退出和磁盘故障后的完整流程。
4. **真实登录网站验证**：采集集成测试使用受控页面，真实站点的登录持久化、二次验证、动态翻页和会话失效需要选定站点后的实际验收。

`docs/refactor-acceptance.json` 分别记录待验收项目与用户明确的 v2.8.0 发布决定。`pyapp/package/verifyRelease.js` 始终校验版本一致性；仅对该明确指定的正式标签允许带 pending 验收项发布，并输出未完成清单。此决定不自动适用于后续版本。
