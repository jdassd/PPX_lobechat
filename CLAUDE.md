# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

PPX 是一个跨平台桌面工具箱应用，基于 **Vue 3 + Python + Pywebview** 构建。前端使用 Vue 3 + Element Plus，后端使用 Python 提供本地 API，通过 Pywebview 将 Web 界面嵌入到桌面应用中。

## 核心架构

### 双进程架构
- **前端进程**: Vite 开发服务器（开发环境）或静态文件服务（生产环境）
- **后端进程**: Python Pywebview 窗口，暴露 API 给前端通过 `window.pywebview.api.*` 调用

### 目录结构
```
├── gui/                    # Vue 3 前端应用
│   ├── src/               # Vue 源码
│   ├── vite.config.js     # Vite 配置（包含自定义端口探测插件）
│   └── package.json       # 前端依赖
├── api/                   # Python 业务逻辑层（暴露给前端的 API）
│   ├── api.py            # API 主类，聚合所有功能模块
│   ├── pdf.py            # PDF 工具
│   ├── excel.py          # Excel 工具
│   ├── system.py         # 系统工具
│   ├── storage.py        # 数据存储
│   ├── seal.py           # 签章工具
│   ├── image.py          # 图像工具
│   ├── text.py           # 文本工具
│   ├── video.py          # 视频工具
│   ├── file.py           # 文件工具
│   └── core/             # 任务上下文、处理进程、SQLite 状态库与原子输出
├── static/               # 应用静态资源
├── pyapp/                # Python 应用配置和打包
│   ├── config/           # 配置文件（Config 类）
│   ├── db/               # 数据库层（支持 JSON/SQLite）
│   ├── spec/             # PyInstaller 打包配置
│   ├── package/          # 平台打包脚本（Inno Setup, dmgbuild, dpkg）
│   └── requirements.txt  # Python 依赖
├── main.py               # 应用入口，创建 Pywebview 窗口
└── package.json          # 根 package.json，管理构建和打包脚本
```

### API 架构
- `api/api.py` 的 `API` 通过独立服务实例委托公开方法，服务私有辅助方法互相隔离。
- `api/operation_catalog.json` 声明动作参数，`api/operations.py` 定义明确的结果资产契约。
- `api/core/worker.py` 用独立进程执行阻塞处理，`api/core/context.py` 传递取消与进度。
- 前端通过 `window.pywebview.api.<methodname>()` 调用 Python 方法
- API 类在 `main.py` 中实例化并注入到 Pywebview 窗口

### 已退役模块的数据保护
- 思维导图的入口、服务和打包资源已移除，不接入替代项目。
- 用户应用数据目录中的原导图数据库和文件保留，不能随代码清理删除。
- 前端只清理旧导图收藏与导航记录。任务、工作流迁移到 SQLite 时保留旧 JSON 与迁移备份。

### 配置系统
- `pyapp/config/config.py` 中的 `Config` 类管理所有配置
- 关键配置项：
  - `appName`: 应用名称
  - `appVersion`: 版本号
  - `appISSID`: Inno Setup 打包唯一编号（自动生成）
  - `typeDB`: 数据库类型（json 或 sql）
  - `pwDB`: JSON 数据库加密密码
  - `devPort`: 开发环境前端端口

### 数据库系统
- 支持两种模式：`typeDB='json'`（默认）或 `typeDB='sql'`
- JSON 模式：使用 TinyDB + Cryptography 加密存储
- SQL 模式：使用 SQLAlchemy + Alembic 迁移（当前被注释）
- 数据存储在 `Config.appDataDir`（各平台的应用数据目录）

## 开发环境命令

### 环境初始化
```bash
# Windows（首次运行）
pnpm run init

# Linux
pnpm run init  # 自动安装 Python 依赖和系统依赖

# macOS
pnpm run init
```

**初始化流程**:
1. 清空缓存和旧构建产物
2. 安装前端依赖（`gui/` 目录）
3. 创建 Python 虚拟环境（`pyapp/pyenv/`）
4. 安装 Python 依赖（从清华源）
5. 生成应用唯一标识符（`appISSID` 和数据库密钥）

### 开发模式
```bash
# 启动开发环境（前端 + 后端同时运行）
pnpm start
# 等同于: pnpm run dev (启动 Vite) + pnpm run startos (启动 Python)

# 仅启动前端（Vite 开发服务器）
pnpm run dev
# 在 gui/ 目录运行: vite

# 仅启动后端（Windows）
pnpm run startos
# 执行: nodemon 监听 Python 文件变更，运行 main.py --dev

# CEF 模式开发（使用 CEF 渲染引擎）
pnpm run start:cef
```

**开发环境特性**:
- Vite 自动写入端口到 `.ppx-dev-port` 文件
- `main.py` 通过探测该文件或扫描端口范围（5173-5189）自动连接前端
- Nodemon 监听 Python 文件变更并自动重启

### 构建和打包

#### 预打包（带日志输出，用于调试）
```bash
# Windows 预打包
pnpm run pre

# Linux/macOS 预打包
pnpm run pre
```

#### 正式打包
```bash
# Windows 打包（生成安装程序）
pnpm run build
# 流程: 构建前端 → PyInstaller 打包 → Inno Setup 生成 .exe 安装包

# Linux 打包（生成 .deb 包）
pnpm run build

# macOS 打包（生成 .dmg）
pnpm run build

# 单个 exe 程序（无安装器）
pnpm run build:pure

# 文件夹模式（便于调试）
pnpm run build:folder
```

**打包流程**:
1. `pnpm -C ./gui run build`: 构建前端到 `gui/dist/`
2. `pyinstaller`: 将 Python 代码和前端静态文件打包
3. 平台特定打包工具生成安装包

#### CEF 模式打包
```bash
# CEF 模式正式打包（Windows）
pnpm run build:cef

# CEF 模式文件夹打包
pnpm run build:folder:cef
```

### 数据库迁移（仅 SQL 模式）
```bash
# Windows
m=信息备注 pnpm run alembic

# Linux/macOS
m=信息备注 pnpm run alembic
```

## 关键技术细节

### 前后端通信
- 前端调用：`await window.pywebview.api.methodName(params)`
- 后端定义：在 `api/*.py` 中定义方法，通过 `API` 类聚合
- Pywebview 自动将 Python 方法暴露为 Promise

### 动态端口探测
- Vite 插件 `devPortReporter` 在 `vite.config.js` 中写入端口信息
- `main.py` 中的 `_resolve_dev_server()` 读取端口或扫描常用端口
- 支持 Vite 端口自动递增场景

### 跨平台打包差异
- **Windows**: PyInstaller → Inno Setup (.exe 安装器)
- **macOS**: PyInstaller → dmgbuild (.dmg 镜像)
- **Linux**: PyInstaller → dpkg (.deb 包)
- **CEF 模式**: 使用 cefpython3 替代系统 WebView（需单独虚拟环境）

### 配置密钥生成
- 首次 `pnpm run init` 时：
  - 生成 `appISSID`（Inno Setup 唯一标识符）
  - 生成 `pwDB`（数据库加密密钥）
- 生成后写入 `pyapp/config/config.py`，**不应再修改**

## 常见开发任务

### 添加新的 API 功能
1. 在 `api/` 目录创建新模块（如 `api/newtool.py`）
2. 定义功能类（如 `class NewTool`）
3. 在 `api/api.py` 中继承该类：
   ```python
   from api.newtool import NewTool
   class API(..., NewTool):
   ```
4. 前端调用：`window.pywebview.api.newMethod()`

### 修改应用配置
- 编辑 `pyapp/config/config.py` 中的 `Config` 类
- **注意**: `appISSID` 和 `pwDB` 生成后不应手动修改

### 调试打包问题
1. 使用 `pnpm run pre` 预打包（带日志）
2. 使用 `pnpm run build:folder` 生成文件夹模式
3. 检查 `build/` 目录中的日志文件

### 切换数据库模式
1. 在 `pyapp/config/config.py` 中设置 `typeDB = 'sql'`
2. 取消注释 `requirements.txt` 中的 SQLAlchemy 依赖
3. 重新运行 `pnpm run init`
4. 使用 `pnpm run alembic` 管理迁移

## Python 虚拟环境路径
- **默认模式**: `pyapp/pyenv/pyenv/` (Windows) 或 `pyapp/pyenv/` (Linux/macOS)
- **CEF 模式**: `pyapp/pyenv/pyenvCEF/`

## 注意事项

### 依赖管理
- 前端依赖在 `gui/package.json`，使用 pnpm 管理
- Python 依赖在 `pyapp/requirements.txt`，使用清华镜像源

### 端口冲突
- 默认开发端口 5173
- 如果端口被占用，Vite 会自动递增
- Python 后端会自动探测正确端口

### 平台特定命令
- 根 `package.json` 使用 `run-script-os` 自动选择平台脚本
- Windows 命令使用反斜杠路径和 `.exe`
- Linux/macOS 使用正斜杠路径和 `bin/` 目录

### 数据持久化
- 应用数据存储在系统标准目录：
  - Windows: `%APPDATA%\ppx.jdassd.tools`
  - macOS: `~/Library/Application Support/ppx.jdassd.tools`
  - Linux: `~/.ppx.jdassd.tools`
