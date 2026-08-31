# PPX - 现代化跨平台桌面工具箱

<p align="center">
  <img src="./logo.png" alt="PPX Logo" width="120" height="120">
</p>

<p align="center">
  <strong>本地优先的图片、文档、表格与文件批处理工作台</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3.0+-4FC08D?style=flat-square&logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/Python-3.10-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10" />
  <img src="https://img.shields.io/badge/Pywebview-5.0+-FFD43B?style=flat-square&logo=python&logoColor=blue" alt="Pywebview" />
  <img src="https://img.shields.io/badge/version-2.6.1-2b6fff?style=flat-square" alt="Version 2.6.1" />
  <img src="https://img.shields.io/badge/License-AGPL--3.0-green?style=flat-square" alt="License" />
</p>

---

## 📖 简介

**PPX 2.6.1** 是一款面向日常办公的本地桌面工作台。它通过 Vue 3 提供统一界面，由 Python 在本机完成图片、PDF、Word、Excel、全文检索和文件批处理；文件默认不上传到第三方服务。

2.6 系列新增内置 FlyingMouse Format 的转换中心，将原先分散在图片、PDF 和视频工具中的格式转换收拢为统一的本地批处理流程，同时延续“动作 → 持久任务 → 可恢复结果”的可观测闭环。

## ✨ 主要功能

PPX 2.6.1 的核心能力包括：

### 📄 文档与数据

- **转换中心**：通过本机 FlyingMouse Format 引擎统一处理图片、文本、Office / WPS、PDF、音频、视频、电子书与 ZIP，支持混合批量、目标格式记忆、图片合成 PDF 和 PDF 合并。
- **PDF 工具**：合并、拆分、压缩、切割、页面缩略图重排、页码、水印、永久脱敏及 AES-256 安全副本；PDF / Word / 图片互转集中在转换中心。
- **离线 OCR**：识别图片或扫描 PDF，可生成纯文本、可搜索 PDF，并将规则表格导出为 Excel / CSV / JSON。
- **Word 工具**：按结构或真实页码拆分、切割及多文档合并。
- **Excel 工具**：结构预览、数据清洗、列画像、质量报告、按列拆分及多表合并。
- **文档中心**：对 PDF、Word、Excel、Markdown 等本地文档或单文件建立增量全文索引，离线搜索并提示过期、变化或缺失的源文件。
- **文本诊断**：支持 JSON 查询、文本与列表 Diff，以及不上传、不落任务历史的 JWT 结构与时效诊断。

### 🖼️ 图片与媒体

- **图片处理**：批量压缩、裁剪、水印、旋转翻转、拼接、批量命名与 OCR；格式转换和合成 PDF 集中在转换中心。
- **视频处理（可选）**：使用 FFmpeg 完成压缩、截取、音频提取与合并；格式转换集中在转换中心。

### 🛠️ 文件与自动化

- **文件批处理**：搜索、分类、复制、安全删除、回收站恢复、批量改名与撤销、查重及压缩解压。
- **自动化工作流**：使用安全白名单串联本地工具，支持参数引用、步骤重试与退避、内置模板、周期运行、目录监听、触发器启停/立即运行、模板包导入导出及运行历史导出/清理。
- **网页数据采集**：点选字段、翻页采集并导出 Excel / Word。
- **安全边界**：删除操作可恢复且必须预览；重命名不覆盖；系统启动项只读。

### 🧭 工作台

- **任务中心**：持久保存队列与历史，支持筛选分页、批量取消/重试、7 天趋势、方法可靠性、失败诊断、多输出资产的打开/定位/复制，以及 JSON/CSV 导出和可预览清理。
- **模块中心**：按需开启可选能力，并检查 OCR、FFmpeg、LibreOffice 与 Playwright 依赖。
- **全局搜索**：按 `Ctrl/⌘ + K` 搜索工具或具体动作。
- **设置与维护**：跨平台健康检查、SHA-256 完整备份、延迟安全恢复、隐私诊断报告及窗口状态记忆；旧版备份继续兼容并明确标注校验等级。

## 🏗️ 技术栈

本项目采用前后端分离的架构设计，确保了代码的可维护性和扩展性。

| 模块 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **前端 (GUI)** | **Vue 3** | 渐进式 JavaScript 框架 |
| | **Element Plus** | 基于 Vue 3 的桌面端组件库 |
| | **Vite** | 下一代前端构建工具 |
| | **Sass** | CSS 预处理器 |
| **后端 (Core)** | **Python 3** | 强大的脚本语言，处理所有业务逻辑 |
| | **Pywebview** | 轻量级跨平台 webview 包装器 |
| | **SQLAlchemy** | Python SQL 工具包和 ORM |
| **打包构建** | **PyInstaller** | 将 Python 程序打包为独立可执行文件 |
| | **Inno Setup** | Windows 安装包制作工具 |
| | **dmgbuild** | macOS 磁盘映像构建工具 |

## 🚀 快速开始

### 环境要求

确保你的开发环境已安装以下工具：
- **Node.js** (18+；仅开发和自行构建需要，安装包已内置运行时)
- **pnpm** (8.x+)
- **Python** (3.10)
- **OCR 运行时**（随完整安装包提供，无需联网识别）
- **FFmpeg**（可选；视频转换、压缩、截取、音频提取需要 `ffmpeg` 与 `ffprobe`）
- **LibreOffice**（可选；Word 按真实页码拆分/切割需要）
- **FlyingMouse Format**（已作为固定上游组件内置，安装版无需单独安装）

### 安装步骤

1.  **克隆项目**
    ```bash
    git clone --recurse-submodules https://github.com/jdassd/PPX_lobechat.git
    cd PPX_lobechat
    ```

2.  **初始化项目**
    执行初始化脚本，自动安装前端依赖、创建 Python 虚拟环境并安装所需库。
    ```bash
    # Windows/macOS/Linux
    pnpm run init
    ```

3.  **启动开发环境**
    同时启动前端热更新服务器和 Python 后端。
    ```bash
    pnpm run start
    ```

`pnpm run init` 会准备内置 FlyingMouse 的生产依赖；若克隆时未带子模块，可先运行 `git submodule update --init --recursive`。运行时与许可细节见[转换引擎接入说明](docs/flyingmouse-format-integration.md)。

### 质量检查

```bash
# 前端 ESLint + Python Ruff
pnpm run lint

# Python 标准库 unittest（无需额外测试依赖）
pnpm run test
```

## 📦 打包指南

PPX 支持构建为对应平台的可执行文件或安装包。

### Windows
```bash
# 构建绿色版文件夹 (推荐测试用)
pnpm run build:folder

# 构建单个 EXE 文件
pnpm run build:pure

# 构建安装包 (需安装 Inno Setup)
pnpm run build:exe
```

### macOS
```bash
# 构建 .app 应用
pnpm run build:macos

# 构建 .dmg 安装盘
pnpm run build:dmg
```

### Linux
```bash
# 构建 .deb 安装包 (仅限 Debian/Ubuntu 系)
pnpm run build:linux
```

*注意：跨平台打包建议使用 GitHub Actions，详情请查看 `.github/workflows/main.yml`。*

## 📂 目录结构

```
PPX/
├── api/                 # Python 业务接口 (后端核心)
│   ├── automation/      # 自动化模块
│   ├── db/              # 数据库模型与操作
│   ├── excel/           # Excel 处理逻辑
│   ├── pdf/             # PDF 处理逻辑
│   └── ...
├── gui/                 # Vue 前端项目
│   ├── src/
│   │   ├── components/  # Vue 组件
│   │   ├── assets/      # 静态资源
│   │   └── ...
├── pyapp/               # Python 应用配置与打包脚本
│   ├── config/          # 全局配置
│   ├── icon/            # 应用图标
│   └── spec/            # PyInstaller 打包配置
├── main.py              # 应用入口文件
├── package.json         # 项目脚本配置
└── README.md            # 项目说明文档
```

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request 来改进 PPX！

- **Issues**: [GitHub Issues](https://github.com/jdassd/PPX_lobechat/issues)

## 📄 开源协议

PPX 自有代码采用 [GNU AGPL v3](LICENSE) 开源协议。

安装包内置的 FlyingMouse Format 仍是具有独立版权与许可的上游组件，其许可不因 PPX 的 AGPL v3 而改变。作者署名、授权边界和依赖声明见[转换引擎接入说明](docs/flyingmouse-format-integration.md)与[第三方组件声明](THIRD_PARTY_NOTICES.md)。
