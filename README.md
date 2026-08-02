# PPX - 现代化跨平台桌面工具箱

<p align="center">
  <img src="./gui/src/assets/vue.png" alt="PPX Logo" width="120" height="120">
</p>

<p align="center">
  <strong>本地优先的图片、文档、表格与文件批处理工作台</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3.0+-4FC08D?style=flat-square&logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/Python-3.10-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10" />
  <img src="https://img.shields.io/badge/Pywebview-5.0+-FFD43B?style=flat-square&logo=python&logoColor=blue" alt="Pywebview" />
  <img src="https://img.shields.io/badge/version-2.0.0-2b6fff?style=flat-square" alt="Version 2.0.0" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
</p>

---

## 📖 简介

**PPX 2.0** 是一款面向日常办公的本地桌面工作台。它通过 Vue 3 提供统一界面，由 Python 在本机完成图片、PDF、Word、Excel 和文件批处理；文件默认不上传到第三方服务。

2.0 以“动作 → 任务 → 结果”为主线：从首页或全局搜索直接进入具体功能，在任务中心查看状态和输出；非核心模块可以按需启用。

## ✨ 主要功能

PPX 2.0 的核心能力包括：

### 📄 文档与数据

- **PDF 工具**：合并、拆分、压缩、切割、图片 / Word 转换、文本与图片提取。
- **离线 OCR**：识别图片或扫描 PDF，可生成纯文本和可搜索 PDF。
- **Word 工具**：按结构或真实页码拆分、切割及多文档合并。
- **Excel 工具**：结构预览、数据清洗、分组导出及多表合并。

### 🖼️ 图片与媒体

- **图片处理**：多格式转换、批量压缩、裁剪、水印、合成 PDF 和 OCR。
- **视频处理（可选）**：使用 FFmpeg 完成格式转换、压缩、截取、音频提取与合并。

### 🛠️ 文件与自动化

- **文件批处理**：搜索、分类、复制、安全删除、批量改名、查重及压缩解压。
- **网页数据采集**：点选字段、翻页采集并导出 Excel / Word。
- **安全边界**：删除操作可恢复且必须预览；重命名不覆盖；系统启动项只读。

### 🧭 工作台

- **任务中心**：记录处理状态、耗时、输出路径和失败原因，数据仅保存在本机。
- **模块中心**：按需开启可选能力，并检查 OCR、FFmpeg、LibreOffice 与 Playwright 依赖。
- **全局搜索**：按 `Ctrl/⌘ + K` 搜索工具或具体动作。

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
- **Node.js** (16.14+)
- **pnpm** (8.x+)
- **Python** (3.10)
- **OCR 运行时**（随完整安装包提供，无需联网识别）
- **FFmpeg**（可选；视频转换、压缩、截取、音频提取需要 `ffmpeg` 与 `ffprobe`）
- **LibreOffice**（可选；Word 按真实页码拆分/切割需要）

### 安装步骤

1.  **克隆项目**
    ```bash
    git clone https://github.com/jdassd/PPX_lobechat.git
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

本项目采用 [MIT License](LICENSE) 开源协议。
