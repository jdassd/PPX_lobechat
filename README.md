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
