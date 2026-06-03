<template>
  <div>
    <div class="overview-header">
      <div class="overview-meta">
        <div class="meta-item">
          <span class="meta-label">系统运行时间</span>
          <strong>{{ status.uptime.text || '未获取' }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">负载情况</span>
          <strong>{{ status.load.label || '未获取' }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">更新时间</span>
          <strong>{{ status.updatedAt || '--' }}</strong>
        </div>
      </div>
      <div class="overview-actions">
        <el-button type="primary" :loading="status.loading" @click="$emit('refresh')">刷新</el-button>
      </div>
    </div>

    <div class="metric-grid">
      <div class="metric-card">
        <div class="metric-title">
          <span>CPU 负载</span>
          <el-tag size="small" effect="plain">{{ status.cpu.cores || 0 }} 核</el-tag>
        </div>
        <el-progress :percentage="status.cpu.percent" :stroke-width="10" />
        <div class="metric-foot">
          <span>频率 {{ status.cpu.freq || '--' }}</span>
          <span>温度 {{ status.cpu.tempLabel || '暂无' }}</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-title">
          <span>内存占用</span>
          <el-tag size="small" effect="plain">{{ status.memory.text || '--' }}</el-tag>
        </div>
        <el-progress :percentage="status.memory.percent" :stroke-width="10" status="warning" />
        <div class="metric-foot">
          <span>已用 {{ status.memory.usedText || '--' }}</span>
          <span>交换区 {{ status.swap.text || '--' }}</span>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-title">
          <span>磁盘占用</span>
          <el-tag size="small" effect="plain">{{ status.disks.length }} 分区</el-tag>
        </div>
        <div class="disk-list">
          <div v-for="disk in status.disks" :key="disk.mount" class="disk-item">
            <div class="disk-row">
              <span class="disk-label">{{ disk.label }}</span>
              <span class="disk-value">{{ disk.usedText }} / {{ disk.totalText }}</span>
            </div>
            <el-progress :percentage="disk.percent" :stroke-width="8" status="success" />
          </div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-title">
          <span>GPU 状态</span>
          <el-tag size="small" effect="plain">{{ status.gpus.length }} 设备</el-tag>
        </div>
        <div v-if="status.gpus.length" class="gpu-list">
          <div v-for="gpu in status.gpus" :key="gpu.name" class="gpu-item">
            <div class="gpu-header">
              <strong>{{ gpu.name }}</strong>
              <span>温度 {{ gpu.temperatureLabel || '暂无' }}</span>
            </div>
            <el-progress :percentage="gpu.utilization" :stroke-width="8" />
            <div class="gpu-foot">
              <span>显存 {{ gpu.memoryUsedText }} / {{ gpu.memoryTotalText }}</span>
              <span>风扇 {{ gpu.fanSpeedLabel || '暂无' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-hint">未检测到 GPU 或驱动未暴露信息</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  status: {
    type: Object,
    required: true
  }
})

defineEmits(['refresh'])
</script>

<style scoped>
.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.overview-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  box-shadow: var(--ppx-shadow-sm);
  backdrop-filter: var(--ppx-blur-sm);
  min-width: 160px;
}

.meta-label {
  font-size: 11px;
  color: var(--ppx-text-secondary);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  background: linear-gradient(180deg, var(--ppx-glass-bg), rgba(255, 255, 255, 0.9));
  border: 1px solid var(--ppx-glass-border);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--ppx-shadow-sm);
}

.metric-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ppx-text-primary);
}

.metric-foot {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}

.disk-list,
.gpu-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.disk-row,
.gpu-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}

.disk-label {
  font-weight: 600;
}

.gpu-foot {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}

.empty-hint {
  font-size: 12px;
  color: var(--ppx-text-secondary);
  margin-top: 8px;
}

@media (max-width: 900px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
