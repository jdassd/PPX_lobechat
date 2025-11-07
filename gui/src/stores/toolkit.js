import { defineStore } from 'pinia'
import dayjs from 'dayjs'
import { readStorage, writeStorage } from '@/services/storage'
import {
  fetchSystemMetrics,
  fetchUnitCatalog,
  fetchExchangeRates,
  convertUnits,
  convertCurrency
} from '@/services/toolkitApi'
import { defaultTextOptions, runTextPipeline, createTextStats } from '@/utils/textTransforms'

const STORAGE_KEYS = {
  CLIPBOARD: 'toolkit_clipboard_items',
  TEXT: 'toolkit_text_batch',
  PREF: 'toolkit_preferences',
  CONVERTER: 'toolkit_converter',
  ACTIVITY: 'toolkit_activity_log'
}

const NAV_GROUPS = [
  {
    id: 'efficiency',
    label: '效率',
    icon: 'ele-Timer',
    tools: [
      { id: 'clipboard', label: '多格式剪贴板', badge: 'MVP' },
      { id: 'text', label: '文本批处理', badge: 'MVP' },
      { id: 'pomodoro', label: '计划番茄钟', status: '规划中', disabled: true }
    ]
  },
  {
    id: 'creative',
    label: '创意',
    icon: 'ele-MagicStick',
    tools: [
      { id: 'whiteboard', label: '灵感白板', status: '排期', disabled: true },
      { id: 'capture', label: '截图取色', status: '排期', disabled: true }
    ]
  },
  {
    id: 'system',
    label: '系统',
    icon: 'ele-DataBoard',
    tools: [
      { id: 'system-monitor', label: '系统资源监控', badge: 'MVP' },
      { id: 'file-assist', label: '文件整理助手', status: '排期', disabled: true }
    ]
  },
  {
    id: 'market',
    label: '工具集市',
    icon: 'ele-Grid',
    tools: [
      { id: 'unit', label: '单位 / 汇率换算', badge: 'MVP' },
      { id: 'script', label: '快速脚本', status: '排期', disabled: true }
    ]
  }
]

const MAX_ACTIVITY = 30

const createId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export const useToolkitStore = defineStore('toolkit', {
  state: () => ({
    initialized: false,
    theme: 'light',
    searchKeyword: '',
    navGroups: NAV_GROUPS,
    activeTool: 'clipboard',
    activeDrawer: null,
    cloudSync: {
      status: 'offline',
      updatedAt: null,
      auto: false
    },
    clipboard: {
      items: [],
      filter: 'all',
      search: '',
      activeTag: '',
      maxItems: 80,
      syncing: false,
      lastError: ''
    },
    textBatch: {
      input: '',
      output: '',
      options: defaultTextOptions(),
      error: '',
      stats: createTextStats('')
    },
    converter: {
      catalog: null,
      category: 'length',
      fromUnit: 'cm',
      toUnit: 'm',
      baseValue: 10,
      result: null,
      favorites: [
        { id: 'px-rem', label: 'px → rem', category: 'length', from: 'cm', to: 'm', presetValue: 0.01 },
        { id: 'kg-lb', label: 'kg → lb', category: 'weight', from: 'kg', to: 'lb' }
      ],
      currency: {
        amount: 100,
        from: 'USD',
        to: 'CNY',
        base: 'USD',
        result: null
      },
      ratesMeta: null,
      refreshingRates: false
    },
    metrics: {
      latest: null,
      history: [],
      pollingTimer: null,
      interval: 5000
    },
    activityLog: []
  }),
  getters: {
    clipboardCount: (state) => state.clipboard.items.length,
    favoriteClipboardItems: (state) => state.clipboard.items.filter((item) => item.favorite),
    availableClipboardTags: (state) => {
      return Array.from(
        new Set(
          state.clipboard.items.flatMap((item) => item.tags || [])
        )
      )
    },
    filteredClipboardItems(state) {
      const { filter, activeTag, search } = state.clipboard
      return state.clipboard.items.filter((item) => {
        if (filter === 'favorite' && !item.favorite) {
          return false
        }
        if (filter !== 'all' && filter !== 'favorite' && item.type !== filter) {
          return false
        }
        if (activeTag && !(item.tags || []).includes(activeTag)) {
          return false
        }
        if (search) {
          const keyword = search.toLowerCase()
          return (
            item.summary?.toLowerCase().includes(keyword) ||
            item.content?.toLowerCase().includes(keyword)
          )
        }
        return true
      })
    },
    activityTimeline: (state) => state.activityLog.slice().reverse(),
    searchMatcher: (state) => (keywords = []) => {
      const query = state.searchKeyword.trim().toLowerCase()
      if (!query) {
        return true
      }
      return keywords.some((word) => word.toLowerCase().includes(query))
    }
  },
  actions: {
    async bootstrap() {
      await Promise.all([
        this.loadPreferences(),
        this.loadClipboard(),
        this.loadTextBatch(),
        this.loadConverter(),
        this.loadActivities()
      ])
      await this.loadUnitCatalog()
      await this.refreshRates(false)
      await this.pullSystemMetrics()
      this.startMetricPolling()
      this.initialized = true
    },
    setTheme(theme) {
      this.theme = theme
      this.persistPreferences()
    },
    toggleTheme() {
      this.setTheme(this.theme === 'light' ? 'dark' : 'light')
    },
    setSearchKeyword(keyword) {
      this.searchKeyword = keyword
    },
    setActiveTool(toolId) {
      this.activeTool = toolId
    },
    openDrawer(toolId) {
      this.activeDrawer = toolId
    },
    closeDrawer() {
      this.activeDrawer = null
    },
    addActivity(entry) {
      const payload = {
        id: createId(),
        timestamp: new Date().toISOString(),
        ...entry
      }
      this.activityLog.unshift(payload)
      this.activityLog = this.activityLog.slice(0, MAX_ACTIVITY)
      this.persistActivities()
    },
    async loadPreferences() {
      const data = await readStorage(STORAGE_KEYS.PREF, { theme: 'light', cloudAuto: false })
      if (data?.theme) {
        this.theme = data.theme
      }
      if (typeof data?.cloudAuto === 'boolean') {
        this.cloudSync.auto = data.cloudAuto
      }
    },
    async persistPreferences() {
      await writeStorage(STORAGE_KEYS.PREF, {
        theme: this.theme,
        cloudAuto: this.cloudSync.auto
      })
    },
    async loadClipboard() {
      const data = await readStorage(STORAGE_KEYS.CLIPBOARD, [])
      if (Array.isArray(data)) {
        this.clipboard.items = data.map((item) => ({
          id: item.id || createId(),
          type: item.type || 'text',
          content: item.content || '',
          summary: item.summary || item.content?.slice(0, 60) || '',
          tags: item.tags || [],
          favorite: Boolean(item.favorite),
          createdAt: item.createdAt || new Date().toISOString(),
          metadata: item.metadata || {}
        }))
      }
    },
    async persistClipboard() {
      await writeStorage(STORAGE_KEYS.CLIPBOARD, this.clipboard.items)
    },
    async captureClipboard() {
      if (this.clipboard.syncing) {
        return
      }
      this.clipboard.syncing = true
      try {
        const payload = await this.readClipboardPayload()
        this.prependClipboardItem(payload)
        this.addActivity({ type: 'clipboard', title: '捕获剪贴板', detail: payload.summary })
      } catch (err) {
        this.clipboard.lastError = err.message
      } finally {
        this.clipboard.syncing = false
      }
    },
    async readClipboardPayload() {
      if (navigator.clipboard?.read) {
        const items = await navigator.clipboard.read()
        for (const item of items) {
          if (item.types.includes('image/png')) {
            const blob = await item.getType('image/png')
            const content = await this.blobToDataUrl(blob)
            return {
              type: 'image',
              content,
              summary: 'PNG 图片',
              metadata: { size: blob.size }
            }
          }
          if (item.types.includes('text/plain')) {
            const blob = await item.getType('text/plain')
            const text = await blob.text()
            return this.normalizeTextClip(text)
          }
        }
      }
      if (navigator.clipboard?.readText) {
        const text = await navigator.clipboard.readText()
        return this.normalizeTextClip(text)
      }
      throw new Error('无法访问剪贴板，请在系统设置中授予权限')
    },
    normalizeTextClip(text) {
      const trimmed = text.trim()
      const urlPattern = /https?:\/\/\S+/i
      const isLink = urlPattern.test(trimmed)
      return {
        type: isLink ? 'link' : 'text',
        content: trimmed,
        summary: trimmed.slice(0, 120),
        metadata: {
          length: trimmed.length
        }
      }
    },
    async blobToDataUrl(blob) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result)
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })
    },
    prependClipboardItem(item) {
      const payload = {
        id: createId(),
        favorite: false,
        tags: [],
        createdAt: new Date().toISOString(),
        ...item
      }
      this.clipboard.items.unshift(payload)
      this.clipboard.items = this.clipboard.items.slice(0, this.clipboard.maxItems)
      this.persistClipboard()
    },
    toggleClipboardFavorite(id) {
      this.clipboard.items = this.clipboard.items.map((item) => {
        if (item.id === id) {
          return { ...item, favorite: !item.favorite }
        }
        return item
      })
      this.persistClipboard()
    },
    removeClipboardItem(id) {
      this.clipboard.items = this.clipboard.items.filter((item) => item.id !== id)
      this.persistClipboard()
    },
    setClipboardFilter(filter) {
      this.clipboard.filter = filter
    },
    setClipboardSearch(keyword) {
      this.clipboard.search = keyword
    },
    setClipboardTag(tag) {
      this.clipboard.activeTag = tag
    },
    addClipboardTag(id, tag) {
      if (!tag) {
        return
      }
      this.clipboard.items = this.clipboard.items.map((item) => {
        if (item.id === id) {
          const nextTags = new Set(item.tags || [])
          nextTags.add(tag)
          return { ...item, tags: Array.from(nextTags) }
        }
        return item
      })
      this.persistClipboard()
    },
    removeClipboardTag(id, tag) {
      this.clipboard.items = this.clipboard.items.map((item) => {
        if (item.id === id) {
          return { ...item, tags: (item.tags || []).filter((entry) => entry !== tag) }
        }
        return item
      })
      this.persistClipboard()
    },
    async manualClipboardSave(content, type = 'text') {
      if (!content) {
        return
      }
      const payload = type === 'text' ? this.normalizeTextClip(content) : { type, content, summary: '自定义内容' }
      this.prependClipboardItem(payload)
      this.addActivity({ type: 'clipboard', title: '手动存储', detail: payload.summary })
    },
    async loadTextBatch() {
      const data = await readStorage(STORAGE_KEYS.TEXT, null)
      if (data) {
        this.textBatch.input = data.input || ''
        this.textBatch.output = data.output || ''
        this.textBatch.options = { ...defaultTextOptions(), ...(data.options || {}) }
        this.textBatch.error = data.error || ''
        this.textBatch.stats = createTextStats(this.textBatch.output)
      }
    },
    async persistTextBatch() {
      await writeStorage(STORAGE_KEYS.TEXT, this.textBatch)
    },
    updateTextInput(value) {
      this.textBatch.input = value
    },
    updateTextOptions(options) {
      this.textBatch.options = { ...this.textBatch.options, ...options }
    },
    processTextBatch() {
      const { result, error } = runTextPipeline(this.textBatch.input, this.textBatch.options)
      this.textBatch.output = result
      this.textBatch.error = error
      this.textBatch.stats = createTextStats(result)
      this.persistTextBatch()
      if (!error) {
        this.addActivity({
          type: 'text',
          title: '批处理完成',
          detail: `${this.textBatch.stats.lines} 行 / ${this.textBatch.stats.words} 词`
        })
      }
    },
    async loadConverter() {
      const data = await readStorage(STORAGE_KEYS.CONVERTER, null)
      if (data) {
        this.converter = { ...this.converter, ...data }
      }
    },
    async persistConverter() {
      await writeStorage(STORAGE_KEYS.CONVERTER, this.converter)
    },
    async loadUnitCatalog() {
      this.converter.catalog = await fetchUnitCatalog()
    },
    async applyUnitConversion() {
      try {
        const { category, fromUnit, toUnit, baseValue } = this.converter
        const res = await convertUnits(category, fromUnit, toUnit, Number(baseValue))
        this.converter.result = res
        this.persistConverter()
        this.addActivity({
          type: 'unit',
          title: `${fromUnit} → ${toUnit}`,
          detail: res.display
        })
      } catch (err) {
        console.warn('[toolkit] 单位换算失败 =>', err)
      }
    },
    async refreshRates(force = false) {
      if (this.converter.refreshingRates) {
        return
      }
      this.converter.refreshingRates = true
      try {
        const base = this.converter.currency.base || 'USD'
        const res = await fetchExchangeRates(base, force)
        this.converter.ratesMeta = res
      } finally {
        this.converter.refreshingRates = false
      }
    },
    async applyCurrencyConversion() {
      try {
        const { amount, from, to } = this.converter.currency
        const base = this.converter.ratesMeta?.base || this.converter.currency.base || 'USD'
        const res = await convertCurrency(Number(amount), from, to, base)
        this.converter.currency.result = res
        if (!this.converter.ratesMeta) {
          this.converter.ratesMeta = res.meta
        }
        this.persistConverter()
        this.addActivity({
          type: 'currency',
          title: `${from} → ${to}`,
          detail: res.display
        })
      } catch (err) {
        console.warn('[toolkit] 汇率换算失败 =>', err)
      }
    },
    async pullSystemMetrics() {
      try {
        const res = await fetchSystemMetrics()
        this.metrics.latest = res
        this.metrics.history.push({
          timestamp: res.timestamp,
          cpu: res.overview.cpu,
          memory: res.overview.memory,
          disk: res.overview.disk,
          network: res.network
        })
        this.metrics.history = this.metrics.history.slice(-30)
      } catch (err) {
        console.warn('[toolkit] 获取系统指标失败 =>', err)
      }
    },
    startMetricPolling(interval) {
      if (interval) {
        this.metrics.interval = interval
      }
      const ms = this.metrics.interval
      if (this.metrics.pollingTimer) {
        clearInterval(this.metrics.pollingTimer)
      }
      this.metrics.pollingTimer = setInterval(() => {
        this.pullSystemMetrics()
      }, ms)
    },
    stopMetricPolling() {
      if (this.metrics.pollingTimer) {
        clearInterval(this.metrics.pollingTimer)
        this.metrics.pollingTimer = null
      }
    },
    setMetricInterval(interval) {
      this.startMetricPolling(interval)
    },
    async loadActivities() {
      const data = await readStorage(STORAGE_KEYS.ACTIVITY, [])
      if (Array.isArray(data)) {
        this.activityLog = data
      }
    },
    async persistActivities() {
      await writeStorage(STORAGE_KEYS.ACTIVITY, this.activityLog)
    }
  }
})
