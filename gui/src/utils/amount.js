// gui/src/utils/amount.js —— 数字金额转中文大写(处理万/亿进位与元角分)
export function toChineseAmount(num) {
  if (num === '' || num === null || isNaN(num)) return ''
  let n = Math.abs(Number(num))
  if (n === 0) return '零元整'
  if (n >= 1e15) return '金额过大'
  const dig = ['零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖']
  const unit = ['', '拾', '佰', '仟']
  const big = ['', '万', '亿', '兆']
  const fix = Math.round(n * 100)
  const intPart = Math.floor(fix / 100)
  const jiao = Math.floor((fix % 100) / 10)
  const fen = fix % 10
  let s = ''
  if (intPart > 0) {
    const groups = []
    let x = intPart
    while (x > 0) { groups.push(x % 10000); x = Math.floor(x / 10000) }
    for (let g = groups.length - 1; g >= 0; g--) {
      let gv = groups[g], gs = '', zero = false
      const ds = []
      for (let i = 0; i < 4; i++) { ds.push(gv % 10); gv = Math.floor(gv / 10) }
      for (let i = 3; i >= 0; i--) {
        if (ds[i] === 0) zero = true
        else { if (zero && gs) gs += '零'; zero = false; gs += dig[ds[i]] + unit[i] }
      }
      if (gs) s += gs + big[g]
      else if (s && !s.endsWith('零') && g < groups.length - 1) s += '零'
    }
    s = s.replace(/零+$/, '') + '元'
  }
  if (jiao === 0 && fen === 0) s += '整'
  else {
    if (intPart > 0 && jiao === 0 && fen !== 0) s += '零'
    if (jiao !== 0) s += dig[jiao] + '角'
    if (fen !== 0) s += dig[fen] + '分'
  }
  return s.replace(/^零元/, '') || '零元整'
}
