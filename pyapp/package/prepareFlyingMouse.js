#!/usr/bin/env node
/*
 * Prepare the embedded FlyingMouse Format runtime used by PPX packages.
 *
 * The upstream source stays pinned as a git submodule. This script installs
 * production-only Node dependencies, stages only the CLI runtime files, copies
 * the current platform's Node executable, and writes attribution metadata.
 */

'use strict'

const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const { spawnSync } = require('node:child_process')

const rootDir = path.resolve(__dirname, '..', '..')
const sourceDir = path.join(rootDir, 'vendor', 'flyingmouse-format')
const buildDir = path.join(rootDir, 'build')
const stagedAppDir = path.join(buildDir, 'flyingmouse-source')
const stagedRuntimeDir = path.join(buildDir, 'flyingmouse-runtime')
const packagePath = path.join(sourceDir, 'package.json')
const lockPath = path.join(sourceDir, 'package-lock.json')
const nodeModulesDir = path.join(sourceDir, 'node_modules')
const markerPath = path.join(nodeModulesDir, '.ppx-runtime.json')
const isWindows = process.platform === 'win32'

function fail(message) {
  console.error(`[FlyingMouse] ${message}`)
  process.exit(1)
}

function sha256(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex')
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function runtimeFingerprint() {
  return {
    lockHash: sha256(lockPath),
    platform: process.platform,
    arch: process.arch,
    nodeVersion: process.version
  }
}

function dependencyCacheReady(expected) {
  try {
    const marker = readJson(markerPath)
    return (
      marker.lockHash === expected.lockHash &&
      marker.platform === expected.platform &&
      marker.arch === expected.arch &&
      marker.nodeVersion === expected.nodeVersion &&
      fs.statSync(path.join(nodeModulesDir, 'express', 'package.json')).isFile() &&
      fs.statSync(path.join(nodeModulesDir, 'sharp', 'package.json')).isFile()
    )
  } catch {
    return false
  }
}

function installProductionDependencies(fingerprint) {
  if (dependencyCacheReady(fingerprint)) {
    console.log('[FlyingMouse] 生产依赖缓存有效，跳过 npm ci。')
    return
  }

  console.log('[FlyingMouse] 安装内置引擎生产依赖…')
  const npmCommand = isWindows ? 'npm.cmd' : 'npm'
  const result = spawnSync(npmCommand, ['ci', '--omit=dev', '--no-audit', '--no-fund'], {
    cwd: sourceDir,
    env: { ...process.env, NODE_ENV: 'production' },
    shell: isWindows,
    stdio: 'inherit'
  })
  if (result.error) fail(`无法运行 npm ci：${result.error.message}`)
  if (result.status !== 0) fail(`npm ci 失败（退出码 ${result.status}）`)

  fs.writeFileSync(markerPath, `${JSON.stringify(fingerprint, null, 2)}\n`, 'utf8')
}

function copyEntry(relativePath, options = {}) {
  const source = path.join(sourceDir, relativePath)
  const destination = path.join(stagedAppDir, relativePath)
  if (!fs.existsSync(source)) fail(`上游运行文件缺失：${relativePath}`)
  fs.mkdirSync(path.dirname(destination), { recursive: true })
  fs.cpSync(source, destination, {
    recursive: true,
    force: true,
    dereference: Boolean(options.dereference)
  })
}

function stageRuntimeSource(packageJson) {
  fs.rmSync(stagedAppDir, { recursive: true, force: true })
  fs.mkdirSync(stagedAppDir, { recursive: true })

  const entries = Array.isArray(packageJson.build?.files) ? packageJson.build.files : []
  for (const entry of entries) {
    if (entry === 'node_modules/**/*') continue
    copyEntry(entry.endsWith('/**/*') ? entry.slice(0, -5) : entry)
  }
  // npm creates relative symlinks in node_modules/.bin on Unix. PyInstaller's
  // macOS BUNDLE relocates symlinks and data into different bundle roots, which
  // breaks the npm tree before its Resources target exists. Materialize those
  // links while staging so the embedded runtime is a self-contained data tree.
  copyEntry('node_modules', { dereference: true })
  for (const entry of ['LICENSE', 'README.md', 'package-lock.json']) copyEntry(entry)
}

function upstreamCommit() {
  const result = spawnSync('git', ['-C', sourceDir, 'rev-parse', 'HEAD'], { encoding: 'utf8' })
  return result.status === 0 ? String(result.stdout || '').trim() : 'unknown'
}

function packageName(location, metadata) {
  if (metadata.name) return metadata.name
  const marker = 'node_modules/'
  const index = location.lastIndexOf(marker)
  const remainder = index >= 0 ? location.slice(index + marker.length) : location
  const segments = remainder.split('/')
  return segments[0]?.startsWith('@') ? segments.slice(0, 2).join('/') : segments[0]
}

function writeThirdPartySummary(packageJson, commit) {
  const lock = readJson(lockPath)
  const dependencies = new Map()
  for (const [location, metadata] of Object.entries(lock.packages || {})) {
    if (!location || !location.includes('node_modules/') || !metadata?.version) continue
    const installedManifest = path.join(sourceDir, location, 'package.json')
    if (!fs.existsSync(installedManifest)) continue
    const name = packageName(location, metadata)
    if (!name) continue
    const key = `${name}@${metadata.version}`
    dependencies.set(key, String(metadata.license || 'SEE PACKAGE LICENSE'))
  }

  const lines = [
    '# Bundled component notices',
    '',
    `- FlyingMouse Format ${packageJson.version} (${commit})`,
    '- Author: 牢蜂（LaoFeng）',
    '- Upstream: https://github.com/LaoFeng-mouse/flyingmouse-format',
    '- License: see `LICENSE` in this directory.',
    `- Embedded Node runtime: ${process.version} (${process.platform}-${process.arch})`,
    '',
    '## Node production dependencies',
    '',
    'The corresponding package license files are retained inside `node_modules`.',
    '',
    '| Package | Declared license |',
    '| --- | --- |',
    ...[...dependencies.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([name, license]) => `| ${name} | ${license.replaceAll('|', '\\|')} |`),
    ''
  ]
  fs.writeFileSync(path.join(stagedAppDir, 'THIRD_PARTY_LICENSES.md'), lines.join('\n'), 'utf8')
}

function findNodeLicense() {
  const executableDir = path.dirname(process.execPath)
  return [
    path.join(executableDir, 'LICENSE'),
    path.join(executableDir, 'LICENSE.txt'),
    path.join(executableDir, '..', 'LICENSE'),
    path.join(executableDir, '..', 'LICENSE.txt')
  ].find((candidate) => fs.existsSync(candidate))
}

function stageNodeRuntime(packageJson, commit) {
  fs.rmSync(stagedRuntimeDir, { recursive: true, force: true })
  fs.mkdirSync(stagedRuntimeDir, { recursive: true })
  const nodeName = isWindows ? 'node.exe' : 'node'
  const nodeDestination = path.join(stagedRuntimeDir, nodeName)
  fs.copyFileSync(process.execPath, nodeDestination)
  if (!isWindows) fs.chmodSync(nodeDestination, 0o755)

  const license = findNodeLicense()
  const licenseDir = path.join(stagedAppDir, 'licenses')
  fs.mkdirSync(licenseDir, { recursive: true })
  if (license) {
    fs.copyFileSync(license, path.join(licenseDir, 'NODE-LICENSE'))
  } else {
    fs.writeFileSync(
      path.join(licenseDir, 'NODE-LICENSE-NOTICE.txt'),
      `Node.js ${process.version} is distributed under its upstream license.\nhttps://github.com/nodejs/node/blob/${process.version}/LICENSE\n`,
      'utf8'
    )
  }

  fs.writeFileSync(
    path.join(stagedAppDir, 'EMBEDDED_RUNTIME.json'),
    `${JSON.stringify({
      schemaVersion: 1,
      nodeVersion: process.version,
      platform: process.platform,
      arch: process.arch,
      flyingMouseVersion: packageJson.version,
      flyingMouseCommit: commit
    }, null, 2)}\n`,
    'utf8'
  )
}

if (!fs.existsSync(packagePath) || !fs.existsSync(lockPath)) {
  console.log('[FlyingMouse] 初始化上游源码子模块…')
  const result = spawnSync('git', ['submodule', 'update', '--init', '--recursive', 'vendor/flyingmouse-format'], {
    cwd: rootDir,
    stdio: 'inherit'
  })
  if (result.error || result.status !== 0 || !fs.existsSync(packagePath) || !fs.existsSync(lockPath)) {
    fail('无法初始化 vendor/flyingmouse-format，请检查 Git 与网络连接。')
  }
}
if (Number(process.versions.node.split('.')[0]) < 18) fail('内置 FlyingMouse Format 需要 Node.js 18 或更新版本。')

const packageJson = readJson(packagePath)
const fingerprint = runtimeFingerprint()
installProductionDependencies(fingerprint)
stageRuntimeSource(packageJson)
const commit = upstreamCommit()
writeThirdPartySummary(packageJson, commit)
stageNodeRuntime(packageJson, commit)

console.log(`[FlyingMouse] 已准备内置运行时 ${packageJson.version} (${commit.slice(0, 12)}) / ${process.platform}-${process.arch}。`)
