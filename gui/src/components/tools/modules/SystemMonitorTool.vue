<script setup>
import { computed } from 'vue'
import ToolCard from '../ToolCard.vue'
import { useToolkitStore } from '@/stores/toolkit'
import dayjs from '@/utils/dayjs'

const store = useToolkitStore()

const drawerVisible = computed({
  get: () => store.activeDrawer === 'system-monitor',
  set: (val) => {
    if (!val) {
      store.closeDrawer()
    }
  }
})

const snapshot = computed(() => store.metrics.latest)
const history = computed(() => store.metrics.history)
const alerts = computed(() => snapshot.value?.alerts || [])

const sparklinePoints = (key) => {
  const data = history.value
  if (!data.length) {
    return ''
  }
  const width = 140
  const height = 50
  const step = width / Math.max(1, data.length - 1)
  return data
    .map((entry, index) => {
      const x = index * step
      const value = entry[key] ?? 0
      const y = height - (value / 100) * height
      return `${x},${y}`
    })
    .join(' ')
}
</script>

<template>
  <ToolCard
    title="系统资源监控"
    subtitle="CPU / 内存 / 磁盘"
    badge="实时"
    tone="orange"
  >
    <div class="card-stats">
      <div>
        <p>CPU</p>
        <strong>{{ snapshot?.overview.cpu ?? '--' }}%</strong>
      </div>
      <div>
        <p>内存</p>
        <strong>{{ snapshot?.overview.memory ?? '--' }}%</strong>
      </div>
      <div>
        <p>磁盘</p>
        <strong>{{ snapshot?.overview.disk ?? '--' }}%</strong>
      </div>
    </div>
    <template #actions>
      <el-button size="small" @click="store.pullSystemMetrics">刷新</el-button>
      <el-button size="small" text @click="store.openDrawer('system-monitor')">扩展视图</el-button>
    </template>
  </ToolCard>

  <el-drawer
    title="系统资源监控"
    v-model="drawerVisible"
    destroy-on-close
    size="60%"
    @close="store.closeDrawer"
  >
    <section class="drawer-section">
      <header class="drawer-section__header">
        <h3>实时曲线</h3>
        <small v-if="snapshot">更新于 {{ dayjs(snapshot.timestamp).format('HH:mm:ss') }}</small>
      </header>
      <div class="sparkline-wrapper">
        <div class="sparkline-block">
          <p>CPU</p>
          <svg viewBox="0 0 140 50">
            <polyline :points="sparklinePoints('cpu')" />
          </svg>
        </div>
        <div class="sparkline-block">
          <p>内存</p>
          <svg viewBox="0 0 140 50">
            <polyline :points="sparklinePoints('memory')" />
          </svg>
        </div>
        <div class="sparkline-block">
          <p>磁盘</p>
          <svg viewBox="0 0 140 50">
            <polyline :points="sparklinePoints('disk')" />
          </svg>
        </div>
      </div>
    </section>

    <section class="drawer-section">
      <header class="drawer-section__header">
        <h3>阈值预警</h3>
      </header>
      <div v-if="alerts.length" class="alert-list">
        <el-alert
          v-for="alert in alerts"
          :key="alert.type"
          :title="alert.message"
          :type="alert.level === 'danger' ? 'error' : 'warning'"
          show-icon
        />
      </div>
      <el-empty v-else description="运行稳定" />
    </section>

    <section class="drawer-section metrics-grid">
      <div class="metric-card">
        <h4>CPU 详情</h4>
        <p>核心：{{ snapshot?.cpu.cores || '--' }}</p>
        <p>频率：{{ snapshot?.cpu.frequency?.current?.toFixed?.(0) || snapshot?.cpu.frequency?.current || '-' }} MHz</p>
        <p>负载：{{ snapshot?.cpu.loadAverage?.join(' / ') || '--' }}</p>
      </div>
      <div class="metric-card">
        <h4>内存</h4>
        <p>总量：{{ (snapshot?.memory.total / (1024 ** 3)).toFixed?.(1) || '-' }} GB</p>
        <p>可用：{{ (snapshot?.memory.available / (1024 ** 3)).toFixed?.(1) || '-' }} GB</p>
        <p>Swap：{{ snapshot?.memory.swap.percent ?? 0 }}%</p>
      </div>
      <div class="metric-card">
        <h4>磁盘</h4>
        <p>路径：{{ snapshot?.disk.path || '-' }}</p>
        <p>使用：{{ snapshot?.disk.percent ?? '-' }}%</p>
        <p>剩余：{{ (snapshot?.disk.free / (1024 ** 3)).toFixed?.(1) || '-' }} GB</p>
      </div>
      <div class="metric-card">
        <h4>网络</h4>
        <p>发送：{{ (snapshot?.network.bytesSent / (1024 ** 2)).toFixed?.(1) || '-' }} MB</p>
        <p>接收：{{ (snapshot?.network.bytesRecv / (1024 ** 2)).toFixed?.(1) || '-' }} MB</p>
        <p>进程：{{ snapshot?.process.count || '-' }}</p>
      </div>
    </section>
  </el-drawer>
</template>
