export const fallbackUnitCatalog = {
  length: {
    label: '长度',
    base: 'm',
    units: {
      mm: { label: '毫米', factor: 0.001 },
      cm: { label: '厘米', factor: 0.01 },
      m: { label: '米', factor: 1 },
      km: { label: '千米', factor: 1000 },
      in: { label: '英寸', factor: 0.0254 },
      ft: { label: '英尺', factor: 0.3048 },
      yd: { label: '码', factor: 0.9144 },
      mi: { label: '英里', factor: 1609.34 }
    }
  },
  weight: {
    label: '重量',
    base: 'g',
    units: {
      mg: { label: '毫克', factor: 0.001 },
      g: { label: '克', factor: 1 },
      kg: { label: '千克', factor: 1000 },
      t: { label: '吨', factor: 1000000 },
      oz: { label: '盎司', factor: 28.3495 },
      lb: { label: '磅', factor: 453.592 },
      st: { label: '英石', factor: 6350.29 }
    }
  },
  temperature: {
    label: '温度',
    base: 'c',
    units: {
      c: { label: '℃' },
      f: { label: '℉' },
      k: { label: 'K' }
    }
  },
  storage: {
    label: '存储容量',
    base: 'b',
    units: {
      b: { label: 'Bytes', factor: 1 },
      kb: { label: 'KB', factor: 1024 },
      mb: { label: 'MB', factor: 1024 ** 2 },
      gb: { label: 'GB', factor: 1024 ** 3 },
      tb: { label: 'TB', factor: 1024 ** 4 }
    }
  }
}
