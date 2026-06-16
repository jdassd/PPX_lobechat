# PPX - 现代化跨平台桌面工具箱

<p align="center">
  <img src="./gui/src/assets/vue.png" alt="PPX Logo" width="120" height="120">
</p>

<p align="center">
  <strong>基于 Vue 3 + Python + Pywebview 构建的轻量级、高性能桌面应用框架</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vue-3.0+-4FC08D?style=flat-square&logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Pywebview-5.0+-FFD43B?style=flat-square&logo=python&logoColor=blue" alt="Pywebview" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
</p>

---

## 📖 简介

**PPX** 是一款集成了众多实用功能的现代化桌面工具箱。它利用 Web 技术（Vue 3）构建精美的用户界面，同时发挥 Python 强大的生态能力处理后台业务逻辑。通过 `pywebview` 将两者完美融合，提供轻量、流畅的跨平台体验（Windows, macOS, Linux）。

无论是日常办公的文件处理，还是开发调试的系统工具，PPX 都能为你提供便捷的解决方案。

## ✨ 主要功能

PPX 内置了丰富的工具模块，满足多样化的需求：

### 📄 文档处理
- **PDF 工具箱**：支持 PDF 合并、拆分、页面提取、文本提取。
- **电子签章**：支持 PDF 文件添加水印、电子印章，保障文档安全。
- **Excel 助手**：高效读取、编辑 XLSX 表格数据，支持自定义格式化导出。

### 🖼️ 多媒体工具
- **图片处理**：格式转换、压缩、尺寸调整。
- **视频工具**：基础视频处理功能。

### 🛠️ 系统与效率
- **文件管理**：提供系统级文件/文件夹选择器，批量文件操作。
- **系统监控**：实时查看系统进程、CPU 及内存占用情况。
- **自动化工具**：内置自动化脚本执行能力（基于 Python）。

### 💾 数据存储
- **多模式存储**：支持轻量级 `TinyDB` (JSON) 和 关系型 `SQLite` 数据库。
- **安全备份**：自动备份关键数据，支持本地加密存储。

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
- **Python** (3.8 - 3.11)

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