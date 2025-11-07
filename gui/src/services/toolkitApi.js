import { callBridge, hasNativeBridge } from './nativeBridge'
import { fallbackUnitCatalog } from '@/constants/unitCatalog'

const DEFAULT_RATES = {
  base: 'USD',
  fetched_at: new Date().toISOString(),
  provider: 'mock',
  rates: {
    USD: 1,
    CNY: 7.1,
    EUR: 0.92,
    JPY: 150.12,
    GBP: 0.79
  },
  stale: true
}

export const fetchUnitCatalog = async () => {
  if (hasNativeBridge()) {
    try {
      return await callBridge('toolkit_get_unit_catalog')
    } catch (err) {
      console.warn('[toolkit] unit catalog fallback =>', err)
    }
  }
  return fallbackUnitCatalog
}

export const convertUnits = async (category, fromUnit, toUnit, value) => {
  if (hasNativeBridge()) {
    try {
      return await callBridge('toolkit_convert_units', category, fromUnit, toUnit, value)
    } catch (err) {
      console.warn('[toolkit] remote convert fail =>', err)
    }
  }
  return convertUnitsLocally(category, fromUnit, toUnit, value)
}

export const fetchExchangeRates = async (base = 'USD', forceRefresh = false) => {
  if (hasNativeBridge()) {
    try {
      return await callBridge('toolkit_get_exchange_rates', base, forceRefresh)
    } catch (err) {
      console.warn('[toolkit] rate fetch fail =>', err)
    }
  }
  return DEFAULT_RATES
}

export const convertCurrency = async (amount, source, target, base = 'USD') => {
  if (hasNativeBridge()) {
    try {
      return await callBridge('toolkit_convert_currency', amount, source, target, base, false)
    } catch (err) {
      console.warn('[toolkit] currency convert fail =>', err)
    }
  }
  const rates = DEFAULT_RATES.rates
  const from = rates[source]
  const to = rates[target]
  if (!from || !to) {
    throw new Error('不支持该货币')
  }
  const baseValue = amount / from
  const result = baseValue * to
  return {
    value: result,
    display: Number(result.toFixed(4)),
    meta: DEFAULT_RATES
  }
}

export const fetchSystemMetrics = async () => {
  if (hasNativeBridge()) {
    try {
      return await callBridge('toolkit_get_system_metrics')
    } catch (err) {
      console.warn('[toolkit] metrics fallback =>', err)
    }
  }
  return buildMockMetrics()
}

const convertUnitsLocally = (category, fromUnit, toUnit, value) => {
  const catalog = fallbackUnitCatalog
  category = (category || '').toLowerCase()
  if (category === 'temperature') {
    return {
      value: convertTemp(fromUnit, toUnit, value),
      display: Number(convertTemp(fromUnit, toUnit, value).toFixed(4))
    }
  }
  const definition = catalog[category]
  if (!definition) {
    throw new Error('未知单位')
  }
  const table = definition.units
  const source = table[fromUnit]
  const target = table[toUnit]
  if (!source || !target) {
    throw new Error('未找到单位')
  }
  const baseValue = value * source.factor
  const result = baseValue / target.factor
  return { value: result, display: Number(result.toFixed(4)) }
}

const convertTemp = (fromUnit, toUnit, value) => {
  const f = fromUnit.toLowerCase()
  const t = toUnit.toLowerCase()
  let celsius = value
  if (f === 'f') {
    celsius = (value - 32) * 5 / 9
  } else if (f === 'k') {
    celsius = value - 273.15
  }
  if (t === 'c') {
    return celsius
  }
  if (t === 'f') {
    return (celsius * 9 / 5) + 32
  }
  if (t === 'k') {
    return celsius + 273.15
  }
  return value
}

const buildMockMetrics = () => {
  const cpu = randomPercent(62, 12)
  const memory = randomPercent(70, 6)
  const disk = randomPercent(55, 4)
  return {
    timestamp: new Date().toISOString(),
    overview: { cpu, memory, disk },
    alerts: [],
    cpu: {
      percent: cpu,
      perCore: Array.from({ length: 8 }).map(() => randomPercent(cpu, 10)),
      cores: 8,
      frequency: { current: 3450 },
      loadAverage: [1.1, 1.5, 1.9]
    },
    memory: {
      percent: memory,
      used: 12 * 1024 * 1024 * 1024,
      available: 4 * 1024 * 1024 * 1024,
      total: 16 * 1024 * 1024 * 1024,
      swap: { percent: 20, used: 1 * 1024 * 1024 * 1024, total: 8 * 1024 * 1024 * 1024 }
    },
    disk: {
      percent: disk,
      used: 400 * 1024 * 1024 * 1024,
      free: 120 * 1024 * 1024 * 1024,
      total: 512 * 1024 * 1024 * 1024,
      path: '/'
    },
    network: {
      bytesSent: Math.floor(Math.random() * 1e9),
      bytesRecv: Math.floor(Math.random() * 1e9),
      packetsSent: Math.floor(Math.random() * 1e6),
      packetsRecv: Math.floor(Math.random() * 1e6)
    },
    gpu: null,
    process: { count: 120 },
    thresholds: { cpu: 85, memory: 85, disk: 90 }
  }
}

const randomPercent = (base, variance) => {
  const value = base + (Math.random() - 0.5) * variance * 2
  return Number(Math.min(99, Math.max(1, value)).toFixed(2))
}
