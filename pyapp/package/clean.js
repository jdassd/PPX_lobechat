/**
 * 可复现的项目清理脚本。
 *
 * 只删除可重新生成的构建产物和本地依赖，不修改 package.json，
 * 也不删除 gui/pnpm-lock.yaml。
 */
const fs = require('node:fs')
const path = require('node:path')

const rootDir = path.resolve(__dirname, '..', '..')
const removable = [
  path.join(rootDir, 'build'),
  path.join(rootDir, 'gui', 'dist'),
  path.join(rootDir, 'gui', 'node_modules'),
  path.join(rootDir, 'pyapp', 'pyenv')
]

for (const target of removable) {
  fs.rmSync(target, { recursive: true, force: true })
}

const specDir = path.join(rootDir, 'pyapp', 'spec')
if (fs.existsSync(specDir)) {
  for (const name of fs.readdirSync(specDir)) {
    if (name.startsWith('macos') || name.startsWith('windows')) {
      fs.rmSync(path.join(specDir, name), { recursive: true, force: true })
    }
  }
}

console.log('已清理构建产物、本地依赖和生成式 spec；锁文件已保留。')
