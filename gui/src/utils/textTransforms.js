import yaml from 'js-yaml'
import { format as formatSql } from 'sql-formatter'

export const defaultTextOptions = () => ({
  trimWhitespace: true,
  removeBlankLines: true,
  uniqueLines: false,
  sortLines: false,
  caseStyle: 'none', // none | upper | lower | title
  regexEnabled: false,
  regexPattern: '',
  regexFlags: 'g',
  regexReplace: '',
  formatter: 'none', // none | json | yaml | sql
  indent: 2
})

export const runTextPipeline = (input = '', options = {}) => {
  const safeOptions = { ...defaultTextOptions(), ...options }
  try {
    let working = typeof input === 'string' ? input : String(input ?? '')

    if (safeOptions.trimWhitespace) {
      working = working.trim()
    }

    let lines = working.split(/\r?\n/)
    if (safeOptions.removeBlankLines) {
      lines = lines.filter((line) => line.trim().length)
    }
    if (safeOptions.uniqueLines) {
      const seen = new Set()
      lines = lines.filter((line) => {
        const signature = line.trim()
        if (seen.has(signature)) {
          return false
        }
        seen.add(signature)
        return true
      })
    }
    if (safeOptions.sortLines) {
      lines = [...lines].sort((a, b) => a.localeCompare(b))
    }
    working = lines.join('\n')

    if (safeOptions.regexEnabled && safeOptions.regexPattern) {
      const flags = safeOptions.regexFlags || 'g'
      const regex = new RegExp(safeOptions.regexPattern, flags)
      working = working.replace(regex, safeOptions.regexReplace ?? '')
    }

    if (safeOptions.caseStyle === 'upper') {
      working = working.toUpperCase()
    } else if (safeOptions.caseStyle === 'lower') {
      working = working.toLowerCase()
    } else if (safeOptions.caseStyle === 'title') {
      working = working.replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    }

    if (safeOptions.formatter === 'json') {
      const parsed = JSON.parse(working)
      working = JSON.stringify(parsed, null, safeOptions.indent)
    } else if (safeOptions.formatter === 'yaml') {
      const parsed = tryParseLooseData(working)
      working = yaml.dump(parsed, { indent: safeOptions.indent })
    } else if (safeOptions.formatter === 'sql') {
      working = formatSql(working, { language: 'sql' })
    }

    return { result: working, error: '' }
  } catch (err) {
    return { result: '', error: err.message || '处理失败' }
  }
}

export const createTextStats = (text = '') => {
  const lines = text ? text.split(/\r?\n/) : []
  const words = text ? text.trim().split(/\s+/).filter(Boolean) : []
  return {
    lines: lines.length,
    words: words.length,
    chars: text.length
  }
}

const tryParseLooseData = (value) => {
  try {
    return JSON.parse(value)
  } catch (_) {
    return yaml.load(value)
  }
}
