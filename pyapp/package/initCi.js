#!/usr/bin/env node
/*
 * initCi.js —— CI 专用的精简初始化（替代 `pnpm run init`）。
 *
 * 与本地 `init` 的区别（均为提速 / 适配全新 runner）：
 *   1. 不执行 `clean`：CI 是全新机器，无旧产物可清，且 clean 会删 lockfile / 反复 `pnpm add shx`。
 *   2. 不安装 LibreOffice：它只是最终用户的运行时可选依赖，不参与构建打包（见 api/word.py）。
 *   3. 使用默认 PyPI 源：GitHub runner 在境外，阿里云源反而更慢；配合 setup-python 的 pip 缓存。
 *   4. venv 可缓存复用：虚拟环境已存在且可用时，整体跳过创建与 pip 安装。
 *
 * 仍然完成：Linux 构建系统依赖、前端依赖、Python venv、appISSID 与数据库密钥生成。
 */

'use strict'

const { spawnSync } = require('child_process')
const fs = require('fs')
const path = require('path')

const isWin = process.platform === 'win32'
const isLinux = process.platform === 'linux'
const root = path.resolve(__dirname, '..', '..')

// venv 布局与既有脚本保持一致：Windows 为 pyapp\pyenv\pyenv，其余为 pyapp/pyenv
const venvDir = isWin ? path.join('pyapp', 'pyenv', 'pyenv') : path.join('pyapp', 'pyenv')
const pyBin = isWin ? path.join(venvDir, 'Scripts', 'python.exe') : path.join(venvDir, 'bin', 'python')
const pipBin = isWin ? path.join(venvDir, 'Scripts', 'pip.exe') : path.join(venvDir, 'bin', 'pip')

function run(cmd) {
  console.log('\n> ' + cmd)
  const res = spawnSync(cmd, { stdio: 'inherit', cwd: root, shell: true })
  if (res.status !== 0) {
    console.error(`命令失败（退出码 ${res.status}）：${cmd}`)
    process.exit(res.status || 1)
  }
}

// 缓存恢复的 venv 可能因基础解释器路径变动而失效，做一次可用性自检
function venvUsable() {
  if (!fs.existsSync(path.join(root, pyBin))) return false
  const res = spawnSync(pyBin, ['-c', 'import sys'], { cwd: root, shell: true, stdio: 'ignore' })
  return res.status === 0
}

// 1) Linux 构建 / 打包所需系统依赖（pywebview、dpkg 等）——系统级，不在 venv 缓存内，每次必装
if (isLinux) run('pnpm run initInstallLinuxPre')

// 2) 前端依赖（pnpm store 已缓存，命中即快）
run('pnpm -C ./gui install')

// 3) Python venv：可用则跳过；不可用但残留则重建
if (venvUsable()) {
  console.log('\n[init:ci] 命中可用的虚拟环境缓存，跳过 venv 创建与依赖安装。')
} else {
  if (fs.existsSync(path.join(root, venvDir))) {
    console.log('\n[init:ci] 检测到不可用的虚拟环境残留，删除后重建。')
    fs.rmSync(path.join(root, venvDir), { recursive: true, force: true })
  }
  console.log('\n[init:ci] 创建虚拟环境并安装 Python 依赖（默认 PyPI 源）。')
  run(isWin ? `py -3.10 -m venv ${venvDir}` : `python3 -m venv ${venvDir}`)
  run(`${pyBin} -m pip install --upgrade pip`)
  run(`${pipBin} install -r pyapp/requirements.txt`)
  run(`${pipBin} install -r pyapp/requirements-dev.txt`)
}

// 4) 生成 appISSID 与数据库密钥（幂等、快速）——每次执行，确保后续 build 可用
run(`${pyBin} pyapp/package/exe/getAppISSID.py`)
run(`${pyBin} pyapp/db/json/getKeyDB.py`)

console.log('\n[init:ci] 初始化完成。')
