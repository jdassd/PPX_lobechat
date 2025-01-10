## 介绍

本项目是为了将 lobechat 打包到各个平台，原本使用的是 Tauri 2.1.1 打包，但是因为不熟悉 Rust 语言的原因，所以改用了 Python 的方式进行打包。

借用开源项目 PPX ，可以很方便的将 Vue 嵌入各个平台，虽然在某些打包方式上略有遗憾，比如 Mac M芯片 打包的安装包，只能安装在 M芯片的 Mac 上面，但是依旧可以完成许多内容，没有必要在事事的开始就追求完美，走一步算一步先用起来才是好的方案。

### 问题与解决
当有人帮忙把遇到的问题与解决方案明确详细的告知时，会让进度明显的加快，你，我的朋友，你应该也需要充分利用你的时间，所以我们应该让整个过程都加快，所以我会毫无保留的写下问题与我的解决方式，供你参考。
1. 对于 pnpm 的问题，首先需要将 pnpm 换源：
`pnpm config set registry https://registry.npmmirror.com `
2. 对于 安装时报错 有时候是因为 vs 组件的问题，到这里 https://visualstudio.microsoft.com/visual-cpp-build-tools/ 下载C++生成工具，一定要完整安装，并且卸载以前有问题的版本，就可以解决问题。

3. 运行项目时提示 "ModuleNotFoundError: No module named 'keyboard'" 错误：
   - 这是因为需要在项目自带的虚拟环境中安装 keyboard 包，而不是在全局环境或其他虚拟环境中安装
   - 解决方法：
     ```bash
     # Windows系统
     .\pyapp\pyenv\pyenv\Scripts\activate  # 激活项目自带的虚拟环境
     pip install keyboard                  # 安装 keyboard 包
     deactivate                           # 退出虚拟环境
     
     # macOS/Linux系统
     ./pyapp/pyenv/bin/pip install keyboard
     ```

4. 全局快捷键在不同操作系统上的支持：
   - Windows/Linux: 使用 Alt + Shift + Q 切换窗口显示/隐藏
   - macOS: 使用 Option(Alt) + Shift + Q 切换窗口显示/隐藏
   - 注意：在 macOS 上可能需要授予应用辅助功能权限才能使用全局快捷键

### 打包客户端

```
###########
# 简单用法 #
###########

# 初始化
pnpm run init

# 开发模式
pnpm run start

# 正式打包
pnpm run build

# 预打包，带console，方便输出日志信息
pnpm run pre


###########
# 进阶用法 #
###########

# 初始化，cef兼容模式
pnpm run init:cef

# 开发模式，cef兼容模式【仅win系统】
pnpm run start:cef

# 预打包，带console，cef兼容模式【仅win系统】
pnpm run pre:cef

# 预打包，带console，生成文件夹【仅win系统】
pnpm run pre:folder

# 预打包，带console，生成文件夹，cef兼容模式【仅win系统】
pnpm run pre:folder:cef

# 正式打包，单个exe程序【仅win系统】
pnpm run build:pure

# 正式打包，cef兼容模式【仅win系统】
pnpm run build:cef

# 正式打包，生成文件夹【仅win系统】
pnpm run build:folder

# 正式打包，生成文件夹，cef兼容模式【仅win系统】
pnpm run build:folder:cef
```

## 历史版本

### V5.2.3

- 修复了文本选择功能，现在可以在程序窗口中选择文字
- 优化了全局快捷键实现方式，解决了在输入框输入时快捷键失效的问题
- 改进了窗口置顶和显示/隐藏切换的稳定性

#### V5.2.2

- 新增全局快捷键功能（Alt+Shift+Q）用于显示/隐藏窗口
- 优化窗口显示逻辑，实现显示时临时置顶效果
- 修复了浏览器缓存数据丢失的问题（设置 private_mode=False）

#### V5.2.1

- pywebview 模块升级到 5.3.2
- pyinstaller 模块升级到 6.11.0

#### V5.2.0

- 在 `macOS` 环境下，打包程序由 [appdmg](https://github.com/LinusU/node-appdmg) 改换成 [dmgbuild](https://github.com/dmgbuild/dmgbuild)

#### V5.1.0

- 修复打包成 Linux 系统程序中遇到的一些问题
- 将 Actions 自动生成的程序包拆分为 3 个不同系统的程序包，方便分批下载

#### V5.0.0

- 新增支持打包成 Linux 系统可用的程序（仅测试 Ubuntu 22.04.2 版系统）
- pywebview 模块升级到 5.2
- pyinstaller 模块升级到 6.10.0

#### V4.4.0

- Python 的安装源由[清华源](https://pypi.tuna.tsinghua.edu.cn/simple)改为[中科大源](https://pypi.mirrors.ustc.edu.cn/simple/)。
- 在 win 系统下，执行 `pnpm run build` 打包命令时，PPX 会先生成文件夹式程序（而非是先打包成一个 exe 程序），再打包成安装程序。经测试，打包成文件夹式程序比打包成一个 exe 程序的运行速度会更快些。
- 明确 `Config.codeDir` 为代码根目录，一般情况下，也是程序所在的绝对目录（但在 build:pure 打包成的独立 exe 程序中，codeDir 是执行代码的缓存根目录，而非程序所在的绝对目录）；明确 `Config.appDataDir` 为电脑上可持久使用的隐藏目录。更多细节请查看 `pyapp/config/config.py` 中的【系统配置信息】部分。

#### V4.3.0

- 修复某些情况下，打包后软件打开白屏的问题。（[pull#50](https://github.com/pangao1990/PPX/pull/50)）

#### V4.2.2

- 修复在 win 系统下，设置中文软件名时，打包找不到正确路径的问题。

#### V4.2.1

- 修复自带数据库存储变量命名错误的问题（[issues#33](https://github.com/pangao1990/PPX/issues/33)）

#### V4.2.0

- 删除字节码加密功能（原因见[issues](https://github.com/pyinstaller/pyinstaller/pull/6999)）
- pywebview 模块升级到 4.4.1
- pyinstaller 模块升级到 6.2.0

#### V4.1.0

- 修复某些情况下，自动检测软件升级失效的问题
- 访问网络资源的库由 requests 改为 httpx
- pywebview 模块升级到 4.1
- pyinstaller 模块升级到 5.10.1

#### V4.0.1

- 修复 python 创建 venv 虚拟环境时，pip 不是最新版的问题

#### V4.0.0

- 新增 MacOS 环境打包成 .dmg 安装包，Windows 环境打包成 .exe 安装包（基于 Github Action 可实现同时打包两种安装包）
- 新增自动检测软件升级
- 改 npm 为 pnpm ，节省磁盘空间并提升安装速度
- 项目正式改名为 PPX

#### V3.1.1

- 解决数据库操作时，session 冲突的问题
- 修复了一些已知问题

#### V3.1.0

- 优化数据迁移

#### V3.0.0

- 新增 SQLite 数据库支持，使用 sqlalchemy 进行 ORM 操作，使用 alembic 进行数据迁移与映射
- 新增 static 静态文件夹，可以存放 cache 缓存、db 数据库等，这些文件都将被直接打包到程序包中
- 新增 python 调用 js 函数的示例
- 在 config.py 中新增配置信息，如代码所在绝对目录等
- 修复 python 代码无法打印日志的问题
- 构建程序包时，实时更新打包配置文件 spec
- 调整项目文件夹结构
- pywebview 模块升级到 4.0

#### V2.0.0

- 将 Vue3 框架整体分离至 gui 文件夹，如此一来，你可以随意替换 gui 文件夹下的前端框架，使用 Vue、React、Angular、HTML ，或者你喜欢的其他框架均可
- 整理框架结构，优化代码逻辑

#### V1.3.0

- 新增热更新

#### V1.0.0

- 初始版本
