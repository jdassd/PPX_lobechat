#!/usr/bin/env node
/*
 * ensureLibreOffice.js —— init 安装流程的一环：尽力安装 LibreOffice。
 *
 * 背景：
 *   Word 工具的「按页码拆分 / 切割」依赖 LibreOffice 将 .docx 渲染为 PDF 以获取真实分页。
 *   LibreOffice 是系统级应用（非 pip 包），需按平台单独安装：
 *     - macOS  : Homebrew  ->  brew install --cask libreoffice
 *     - Windows: winget / choco
 *     - Linux  : apt -> libreoffice-writer
 *
 * 设计原则（重要）：
 *   该能力对整个应用而言是「可选」的（仅 Word 按页码功能用到）。因此本脚本始终以退出码 0
 *   结束——即使未检测到包管理器、用户拒绝 sudo、或安装失败，也只打印提示而不让 `pnpm run init`
 *   中断。其余功能不受影响。
 */

'use strict'

const { spawnSync } = require('child_process')
const fs = require('fs')

const GREEN = '\x1b[32m'
const YELLOW = '\x1b[33m'
const RESET = '\x1b[0m'

function log(msg) {
  console.log(`${GREEN}[LibreOffice]${RESET} ${msg}`)
}
function warn(msg) {
  console.log(`${YELLOW}[LibreOffice]${RESET} ${msg}`)
}

/** 命令是否存在于 PATH。 */
function hasCommand(cmd) {
  const probe = process.platform === 'win32' ? 'where' : 'which'
  const res = spawnSync(probe, [cmd], { stdio: 'ignore' })
  return res.status === 0
}

/** 是否已安装 LibreOffice（PATH 或各平台默认安装路径）。 */
function alreadyInstalled() {
  if (hasCommand('soffice') || hasCommand('libreoffice')) return true
  const candidates = []
  if (process.platform === 'darwin') {
    candidates.push('/Applications/LibreOffice.app/Contents/MacOS/soffice')
  } else if (process.platform === 'win32') {
    candidates.push('C:\\Program Files\\LibreOffice\\program\\soffice.exe')
    candidates.push('C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe')
  }
  return candidates.some((p) => {
    try {
      return fs.existsSync(p)
    } catch (_) {
      return false
    }
  })
}

/** 执行安装命令，继承 stdio 以便用户看到进度；返回是否成功。 */
function run(cmd, args) {
  log(`执行：${cmd} ${args.join(' ')}`)
  const res = spawnSync(cmd, args, { stdio: 'inherit', shell: false })
  return res.status === 0
}

function installMac() {
  if (!hasCommand('brew')) {
    warn('未检测到 Homebrew，无法自动安装。')
    warn('请手动安装：https://www.libreoffice.org/download/ 或 `brew install --cask libreoffice`')
    return
  }
  if (!run('brew', ['install', '--cask', 'libreoffice'])) {
    warn('Homebrew 安装失败，请稍后手动执行：brew install --cask libreoffice')
  }
}

function installWindows() {
  if (hasCommand('winget')) {
    const ok = run('winget', [
      'install', '-e', '--id', 'TheDocumentFoundation.LibreOffice',
      '--accept-source-agreements', '--accept-package-agreements'
    ])
    if (ok) return
    warn('winget 安装失败，尝试其它方式…')
  }
  if (hasCommand('choco')) {
    if (run('choco', ['install', 'libreoffice-fresh', '-y'])) return
    warn('choco 安装失败。')
  }
  warn('未检测到 winget / choco，无法自动安装。')
  warn('请手动安装：https://www.libreoffice.org/download/')
}

function installLinux() {
  if (!hasCommand('apt-get')) {
    warn('未检测到 apt-get，无法自动安装。请使用发行版包管理器安装 libreoffice-writer。')
    return
  }
  // 已在 initInstallLinuxPre 中执行过 apt update，这里只补装 writer 组件
  if (!run('sudo', ['apt-get', 'install', '-y', 'libreoffice-writer'])) {
    warn('apt 安装失败，请手动执行：sudo apt-get install -y libreoffice-writer')
  }
}

function main() {
  if (alreadyInstalled()) {
    log('已检测到 LibreOffice，跳过安装。')
    return
  }
  log('未检测到 LibreOffice，Word「按页码」功能需要它，正在尝试安装…')
  try {
    if (process.platform === 'darwin') installMac()
    else if (process.platform === 'win32') installWindows()
    else installLinux()
  } catch (err) {
    warn(`安装过程出现异常：${err && err.message ? err.message : err}`)
  }
  if (alreadyInstalled()) {
    log('LibreOffice 已就绪。')
  } else {
    warn('LibreOffice 未安装成功——不影响其它功能；如需 Word 按页码功能，请稍后手动安装。')
  }
}

main()
// 始终以 0 退出：LibreOffice 为可选依赖，不应中断 init 流程。
process.exit(0)
