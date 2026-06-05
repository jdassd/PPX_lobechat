// gui/src/utils/textTransforms.js —— 文本工具的纯前端实现
// 哈希演示用 Web Crypto (crypto.subtle.digest); MD5 建议交给后端。

export function encodeDecode(algo, dir, input) {
  const enc = dir === 'enc'
  try {
    if (algo === 'b64') return enc ? btoa(unescape(encodeURIComponent(input))) : decodeURIComponent(escape(atob(input)))
    if (algo === 'url') return enc ? encodeURIComponent(input) : decodeURIComponent(input)
    if (algo === 'html') {
      return enc
        ? input.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
        : input.replace(/&(amp|lt|gt|quot|#39);/g, (m, e) => ({ amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'" }[e]))
    }
  } catch (e) { return '⚠ 处理失败：' + e.message }
  return input
}

export function jsonTool(action, input, indent = 2) {
  try {
    const obj = JSON.parse(input)
    if (action === 'min') return JSON.stringify(obj)
    if (action === 'valid') return '✓ JSON 合法 · ' + (Array.isArray(obj) ? obj.length + ' 项' : Object.keys(obj).length + ' 个键')
    return JSON.stringify(obj, null, indent)
  } catch (e) { return '⚠ JSON 解析失败：' + e.message }
}

export function regexMatch(pattern, flags, input) {
  try {
    const re = new RegExp(pattern || '.', flags || 'g')
    const m = input.match(re) || []
    return m.length ? m.map((x, i) => `[${i + 1}] ${x}`).join('\n') : '（无匹配）'
  } catch (e) { return '⚠ 正则错误：' + e.message }
}

// 真实哈希用 Web Crypto; MD5 浏览器原生不支持, 建议交给后端 api/text.py。
export async function hashText(algo, input, upper = false) {
  const map = { md5: null, sha1: 'SHA-1', sha256: 'SHA-256', sha384: 'SHA-384', sha512: 'SHA-512' }
  if (!map[algo]) return '（MD5 建议由后端计算）'
  const buf = await crypto.subtle.digest(map[algo], new TextEncoder().encode(input))
  const hex = [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')
  return upper ? hex.toUpperCase() : hex
}
