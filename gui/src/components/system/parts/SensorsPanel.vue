<template>
  <div class="sensor-grid">
    <div class="sensor-panel">
      <div class="sensor-title">温度</div>
      <el-table :data="status.sensors.temperatures" size="small" border>
        <el-table-column prop="name" label="部件" min-width="120" />
        <el-table-column prop="label" label="传感器" min-width="140" />
        <el-table-column prop="value" label="当前" width="110">
          <template #default="{ row }">
            {{ row.value }}°C
          </template>
        </el-table-column>
        <el-table-column prop="high" label="上限" width="110">
          <template #default="{ row }">
            {{ row.high ?? '-' }}
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!status.sensors.temperatures.length" class="empty-hint">当前系统未提供温度传感器数据</div>
    </div>

    <div class="sensor-panel">
      <div class="sensor-title">风扇转速</div>
      <el-table :data="status.sensors.fans" size="small" border>
        <el-table-column prop="name" label="部件" min-width="120" />
        <el-table-column prop="label" label="传感器" min-width="140" />
        <el-table-column prop="value" label="RPM" width="120" />
      </el-table>
      <div v-if="!status.sensors.fans.length" class="empty-hint">当前系统未提供风扇转速数据</div>
    </div>

    <div class="sensor-panel">
      <div class="sensor-title">电压</div>
      <el-table :data="status.sensors.voltages" size="small" border>
        <el-table-column prop="name" label="部件" min-width="120" />
        <el-table-column prop="label" label="传感器" min-width="140" />
        <el-table-column prop="value" label="电压" width="120">
          <template #default="{ row }">
            {{ row.value }} V
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!status.sensors.voltages.length" class="empty-hint">当前系统未提供电压数据</div>
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
</script>

<style scoped>
.sensor-grid {
  display: grid;
  gap: 16px;
}

.sensor-panel {
  background: var(--ppx-bg-surface);
  border: 1px solid var(--ppx-glass-border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--ppx-shadow-sm);
}

.sensor-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  margin-bottom: 10px;
}

.empty-hint {
  font-size: 12px;
  color: var(--ppx-text-secondary);
  margin-top: 8px;
}
</style>
