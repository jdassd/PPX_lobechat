# 第三方组件声明

PPX 发布包内置以下独立第三方组件。第三方组件的版权与许可不因 PPX 自身许可证而改变。

## FlyingMouse Format

- 名称：FlyingMouse Format
- 作者：牢蜂（LaoFeng）
- 上游项目：https://github.com/LaoFeng-mouse/flyingmouse-format
- 固定源码：`vendor/flyingmouse-format` Git 子模块
- 许可：`vendor/flyingmouse-format/LICENSE`

PPX 经授权将 FlyingMouse Format 的 CLI 运行时嵌入安装包。界面和文档必须保留原作者署名，不得把该组件声明为 PPX 自研实现。

构建脚本会把生产依赖的许可证摘要写入发布包内的 `vendor/flyingmouse-format/THIRD_PARTY_LICENSES.md`，并在 `node_modules` 中保留各依赖包随附的许可证文件。

## Node.js

PPX 安装包包含当前目标平台的 Node.js 运行时，用于启动内置 FlyingMouse Format CLI。构建脚本会随包复制 Node.js 上游许可证；若本机构建环境未提供许可证文件，则写入对应版本的官方许可证地址。

## 可选转换引擎

FFmpeg、LibreOffice、Poppler、Tesseract、qpdf 等大型引擎不作为 FlyingMouse 源码的一部分重新授权。PPX 仅在用户系统或独立合规运行时提供这些组件时启用相应格式，实际可用能力以“转换中心 → 引擎与许可”页面为准。
