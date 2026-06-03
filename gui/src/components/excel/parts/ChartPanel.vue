<template>
  <section class="panel">
    <header>
      <h4>Excel → ECharts</h4>
      <p>自动转换为 JSON 数据并实时渲染图表</p>
    </header>
    <el-form :model="chart" label-width="120px">
      <el-form-item label="源 Excel">
        <div class="field-row">
          <el-button type="primary" @click="selectExcel('chart')">选择文件</el-button>
          <span v-if="chart.file" class="file-chip">{{ chart.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item v-if="chart.sheets.length" label="工作表">
        <el-select v-model="chart.sheet" style="width: 220px">
          <el-option v-for="sheet in chart.sheets" :key="sheet" :label="sheet" :value="sheet" />
        </el-select>
      </el-form-item>
      <el-form-item label="分隔符">
        <el-input
          v-model="chart.delimiter"
          placeholder="默认使用 |"
          maxlength="4"
          style="width: 120px"
        />
      </el-form-item>
      <el-form-item label="结构定义">
        <el-input
          v-model="chart.schemaText"
          type="textarea"
          :rows="2"
          placeholder="示例：地区|销量|负责人"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="loadChartPreview">刷新结构</el-button>
      </el-form-item>
      <el-form-item label="图表类型">
        <el-radio-group v-model="chart.chartType">
          <el-radio-button label="bar">柱状图</el-radio-button>
          <el-radio-button label="line">折线图</el-radio-button>
          <el-radio-button label="pie">饼图</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="维度列">
        <el-select v-model="chart.dimension" placeholder="选择分类字段" style="width: 220px">
          <el-option v-for="field in chartFields" :key="field" :label="field" :value="field" />
        </el-select>
      </el-form-item>
      <el-form-item label="数值列">
        <el-select
          v-model="chart.metric"
          placeholder="选择数值字段"
          clearable
          :disabled="chart.aggregate === 'count'"
          style="width: 220px"
        >
          <el-option v-for="field in chartFields" :key="field" :label="field" :value="field" />
        </el-select>
      </el-form-item>
      <el-form-item label="统计方式">
        <el-select v-model="chart.aggregate" style="width: 220px">
          <el-option label="求和" value="sum" />
          <el-option label="均值" value="avg" />
          <el-option label="计数" value="count" />
        </el-select>
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button type="primary" :loading="loading" @click="runChartBuild">生成图表</el-button>
    </div>

    <div class="format-block">
      <p class="result-title">数据格式说明</p>
      <div class="format-grid">
        <div class="format-card">
          <p class="format-title">图表数据 JSON</p>
          <pre class="format-code">{{ chartDataSample }}</pre>
        </div>
        <div class="format-card">
          <p class="format-title">ECharts Option</p>
          <pre class="format-code">{{ chartOptionSample }}</pre>
        </div>
      </div>
    </div>

    <div v-if="chart.data" class="result-block">
      <p class="result-title">生成结果</p>
      <el-descriptions :column="2" size="small" border>
        <el-descriptions-item label="维度列">
          {{ chart.data.dimension }}
        </el-descriptions-item>
        <el-descriptions-item label="数值列">
          {{ chart.data.metric || '计数' }}
        </el-descriptions-item>
        <el-descriptions-item label="统计方式">
          {{ chart.data.aggregate }}
        </el-descriptions-item>
        <el-descriptions-item label="生成时间">
          {{ chart.data.generatedAt }}
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="chart.data.rows?.length" class="group-table">
        <el-table :data="chart.data.rows" size="small" border>
          <el-table-column prop="name" label="分类" />
          <el-table-column prop="value" label="数值" width="140" />
        </el-table>
      </div>

      <div class="json-view">
        <div class="json-block">
          <p class="result-title">图表数据 JSON</p>
          <el-input
            :model-value="chart.dataJson"
            type="textarea"
            :rows="8"
            readonly
          />
        </div>
        <div class="json-block">
          <p class="result-title">ECharts Option JSON</p>
          <el-input
            :model-value="chart.optionJson"
            type="textarea"
            :rows="8"
            readonly
          />
        </div>
      </div>
    </div>

    <div class="chart-preview">
      <p class="result-title">图表预览</p>
      <div v-show="chart.option" :ref="setChartRef" class="echart-canvas"></div>
      <el-empty v-if="!chart.option" description="请先生成图表" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  // state.chart 切片（reactive 引用，v-model 直接修改保持响应式）
  chart: {
    type: Object,
    required: true
  },
  // chartFields = state.chart.schema
  chartFields: {
    type: Array,
    default: () => []
  },
  // 共享 loading 标志（state.loading）
  loading: {
    type: Boolean,
    default: false
  },
  // 静态格式说明示例（与原常量一致）
  chartDataSample: {
    type: String,
    default: ''
  },
  chartOptionSample: {
    type: String,
    default: ''
  },
  // 壳提供的共享处理函数
  selectExcel: {
    type: Function,
    required: true
  },
  loadChartPreview: {
    type: Function,
    required: true
  },
  runChartBuild: {
    type: Function,
    required: true
  },
  // 将图表画布 DOM 引用回传给壳，由壳管理 echarts 生命周期（保持原逻辑）
  setChartRef: {
    type: Function,
    required: true
  }
})
</script>

<style scoped>
.result-block {
  margin-top: 16px;
}

.result-title {
  margin: 0 0 10px;
  font-weight: 600;
  color: var(--ppx-text-secondary);
}

.actions {
  margin-top: 16px;
}

.group-table {
  margin: 16px 0;
}

.format-block {
  margin-top: 18px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  padding: 12px;
  background: var(--ppx-glass-bg);
}

.format-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.format-card {
  border-radius: var(--ppx-radius-sm);
  background: rgba(9, 11, 20, 0.6);
  padding: 10px;
}

.format-title {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.format-code {
  margin: 0;
  font-family: 'SFMono-Regular', ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
  color: var(--ppx-text-primary);
  white-space: pre-wrap;
}

.json-view {
  margin-top: 16px;
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.json-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chart-preview {
  margin-top: 16px;
}

.echart-canvas {
  width: 100%;
  height: 320px;
  border-radius: var(--ppx-radius-md);
  border: 1px solid var(--ppx-glass-border);
  background: rgba(7, 9, 16, 0.6);
}
</style>
