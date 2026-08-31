# FlyingMouse Format 内置转换引擎

PPX 2.6.0 将 FlyingMouse Format 的公开 CLI、生产依赖和当前平台 Node.js 运行时装入软件本体。Vue 页面、文件选择、任务历史与结果定位仍由 PPX 管理；文件只在本机进程之间传递，不上传到云端服务。

## 组成与固定版本

- 上游源码以 Git 子模块固定在 `vendor/flyingmouse-format/`。
- `pyapp/package/prepareFlyingMouse.js` 使用上游 `package-lock.json` 安装生产依赖。
- 同一脚本把打包平台的 Node 可执行文件、运行文件清单、上游提交号和许可证摘要暂存到 `build/`。
- `pyapp/spec/getSpec.py` 将源码运行文件、`node_modules`、Node 和许可材料写入 PyInstaller 成品。
- 完整安装包运行时不依赖同级源码仓库，也不要求用户另行安装 FlyingMouse Format。

FFmpeg、LibreOffice、Poppler、Tesseract、qpdf 等大型可选引擎具有各自的分发与平台约束，不属于 FlyingMouse 源码依赖树。PPX 继续复用本机已有组件并动态收敛目标格式。

## 开发与构建

推荐首次检出时包含子模块：

```bash
git clone --recurse-submodules https://github.com/jdassd/PPX_lobechat.git
cd PPX_lobechat
pnpm run init
```

已有工作区可执行：

```bash
git submodule update --init --recursive
pnpm run prepare:flyingmouse
```

`pnpm run init`、`pnpm run init:ci` 和各平台 `getSpec.py` 都会准备内置运行时。依赖锁、Node 版本、操作系统或 CPU 架构变化时会自动重建生产依赖。

## 运行时发现顺序

1. 调试环境变量 `PPX_FLYINGMOUSE_CLI_PATH` / `FLYINGMOUSE_FORMAT_CLI_PATH` 指定的 CLI。
2. 发布包或源码树中的 `vendor/flyingmouse-format/cli.js`，并优先搭配包内 Node。
3. `PPX_FLYINGMOUSE_ROOT` / `FLYINGMOUSE_FORMAT_ROOT` 指定的开发源码。
4. PPX 同级的 `../flyingmouse-format/cli.js`，作为旧开发布局兼容。
5. Windows 或 macOS 上已安装的 FlyingMouse Format，作为修复回退。

`PPX_FLYINGMOUSE_NODE_PATH` 只用于显式调试覆盖；正常安装版始终使用内置 Node。

## 输出与任务

- 未选择输出目录时，结果写入系统下载目录下的 `PPX转换结果/`。
- 每个文件独立执行；批量中的某一项失败不会丢失已成功的输出。
- 转换、图片合成 PDF 与 PDF 合并均进入 PPX 持久任务队列。
- PDF 加密与解密继续使用 PPX 的“PDF 工具 → 安全副本”，转换中心不会把密码传入外部命令参数。

## 作者、授权与第三方许可

FlyingMouse Format 版权归牢蜂（LaoFeng）所有。PPX 经授权将其 CLI 运行时嵌入软件本体，继续显著保留作者、上游项目和原始许可信息，不把 FlyingMouse 代码声明为 PPX 自有实现。

上游 `LICENSE`、构建时生成的生产依赖许可证摘要、Node.js 许可证材料及 PPX 的第三方组件声明都会进入发布包。详见仓库根目录 `THIRD_PARTY_NOTICES.md`。
