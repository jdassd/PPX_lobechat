'use strict'

const fs = require('fs')
const path = require('path')
const root = path.resolve(__dirname, '../..')
const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'))
const acceptance = JSON.parse(fs.readFileSync(path.join(root, 'docs/refactor-acceptance.json'), 'utf8'))
const tag = process.env.GITHUB_REF_NAME || ''
if (/^[vV]?\d+\.\d+\.\d+-/.test(tag)) {
  console.log('预发布构建：完整版本验收门槛仍保留在 docs/refactor-acceptance.json。')
  process.exit(0)
}
const failures = []
if (acceptance.version !== pkg.version) failures.push('验收记录版本与 package.json 不一致')
if (tag && tag.replace(/^[vV]/, '') !== pkg.version) failures.push('正式版本标签与 package.json 不一致')
if (failures.length) {
  console.error(failures.join('\n'))
  process.exit(1)
}
for (const phase of [1, 2, 3, 4, 5, 6]) {
  const record = acceptance.phases[String(phase)]
  if (record?.status !== 'passed' || !record.evidence) failures.push(`阶段 ${phase} 缺少通过记录及证据`)
}
for (const platform of ['windows', 'macos', 'linux']) {
  for (const scenario of ['install', 'firstLaunch', 'coreProcessing', 'upgrade', 'restore', 'exit', 'optionalDependencies']) {
    const record = acceptance.platforms[platform]?.[scenario]
    if (record?.status !== 'passed' || !record.evidence) failures.push(`${platform}/${scenario} 尚未通过验收`)
  }
}
if (failures.length) {
  const release = acceptance.release
  if (release?.tag === tag && tag === `v${pkg.version}` && release.allowPendingAcceptance === true && release.reason) {
    console.warn(`按明确发布决定继续 ${tag}：${release.reason}\n尚待验收：\n${failures.join('\n')}`)
    process.exit(0)
  }
  console.error('完整重构版本尚不能发布：\n' + failures.map(item => `- ${item}`).join('\n'))
  process.exit(1)
}
console.log(`PPX ${pkg.version} 的六阶段与三平台发布验收全部通过。`)
