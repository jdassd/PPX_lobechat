# PPX - 跨平台工具箱

一个集成 PDF、Excel、系统工具的桌面应用，基于 Vue 3 + Python + Pywebview 构建。

## 功能

### PDF
- 合并/分割
- 文本提取
- 水印、签章

### Excel
- 读写 XLSX 格式
- 格式化导出

### 系统工具
- 文件/文件夹选择器
- 进程管理
- 系统资源监控

### 数据存储
- 本地加密存储（JSON / SQLite）
- 自动备份

## 技术栈

**前端**
- Vue 3 + Element Plus
- Vite + Sass

**后端**
- Python 3.8+
- Pywebview
- PyPDF2 / openpyxl / psutil

**打包**
- PyInstaller
- Inno Setup (Windows)
- dmgbuild (macOS)
- dpkg (Linux)

## 快速开始

### 开发环境

```bash
# 安装前端依赖
pnpm install

# 启动前端开发服务器
pnpm dev

# 启动 Python 后端
python main.py
```

### 构建

```bash
# 构建前端
pnpm build

# 打包应用
pyinstaller ppx.spec
```

### 下载安装包

前往 [Releases](https://github.com/jdassd/PPX_lobechat/releases) 下载对应平台的安装包。

## 目录结构

```
├── src/           # Vue 前端
├── backend/       # Python 后端
├── dist/          # 构建输出
└── scripts/       # 打包脚本
```

## 反馈

- Issue: https://github.com/jdassd/PPX_lobechat/issues
- Discussion: https://github.com/jdassd/PPX_lobechat/discussions

## License

MIT
