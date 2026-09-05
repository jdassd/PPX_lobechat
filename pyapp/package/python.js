#!/usr/bin/env node
'use strict'
const { spawnSync } = require('child_process')
const path = require('path')
const fs = require('fs')
const root = path.resolve(__dirname, '../..')
const candidates = [process.env.PPX_PYTHON,
  path.join(root, 'pyapp/pyenv/pyenv/Scripts/python.exe'),
  path.join(root, 'pyapp/pyenv/bin/python'),
  path.join(root, 'pyapp/pyenv/refactor310/Scripts/python.exe'),
  path.join(root, '.venv/Scripts/python.exe'), path.join(root, '.venv/bin/python')].filter(Boolean)
const python = candidates.find(candidate => fs.existsSync(candidate) && spawnSync(candidate, ['-c', 'import sys; raise SystemExit(sys.version_info[:2] != (3, 10))'], { windowsHide: true, stdio: 'ignore' }).status === 0)
if (!python) {
  console.error('需要 Python 3.10 虚拟环境。请初始化项目，或将 PPX_PYTHON 指向已安装项目依赖的 Python 3.10。')
  process.exit(1)
}
const result = spawnSync(python, process.argv.slice(2), { cwd: root, stdio: 'inherit', windowsHide: true })
if (result.error) console.error(result.error.message)
process.exit(result.status ?? 1)
