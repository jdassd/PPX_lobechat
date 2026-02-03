<template>
  <el-drawer
    v-model="visibleProxy"
    size="80%"
    append-to-body
    custom-class="excel-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">EXCEL WORKSHOP</p>
          <h3>Excel 宸ュ叿闆?/h3>
          <p class="sub">鏀寔缁撴瀯瀹氫箟銆佹寜鍒楀垎缁勩€佸垎琛ㄥ鍑轰笌 JSON 鍥捐〃</p>
        </div>
      </div>
    </template>
    <div class="excel-tool">
      <el-tabs v-model="activeTab" class="excel-tabs">
        <el-tab-pane label="缁撴瀯瀹氫箟" name="structure">
          <section class="panel">
            <header>
              <h4>閰嶇疆鍥哄畾鏍煎紡</h4>
              <p>瀹氫箟绗竴琛屽瓧娈点€侀€夋嫨宸ヤ綔琛ㄥ苟棰勮鏍蜂緥鏁版嵁</p>
            </header>
            <el-form :model="state.preview" label-width="110px">
              <el-form-item label="婧?Excel">
                <div class="field-row">
                  <el-button type="primary" @click="selectExcel('preview')">閫夋嫨鏂囦欢</el-button>
                  <span v-if="state.preview.file" class="file-chip">{{ state.preview.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item v-if="state.preview.sheets.length" label="宸ヤ綔琛?>
                <el-select v-model="state.preview.sheet" style="width: 220px">
                  <el-option v-for="sheet in state.preview.sheets" :key="sheet" :label="sheet" :value="sheet" />
                </el-select>
              </el-form-item>
              <el-form-item label="鍒嗛殧绗?>
                <el-input
                  v-model="state.preview.delimiter"
                  placeholder="榛樿浣跨敤 |"
                  maxlength="4"
                  style="width: 120px"
                />
              </el-form-item>
              <el-form-item label="缁撴瀯瀹氫箟">
                <el-input
                  v-model="state.preview.schemaText"
                  type="textarea"
                  :rows="2"
                  placeholder="绀轰緥锛氬鍚峾鎵嬫満鍙穦鍦板尯|涓氬姟绫诲瀷"
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="loadPreview">鍒锋柊棰勮</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.preview.schema.length" class="schema-chips">
              <p class="result-title">瀛楁缁撴瀯</p>
              <div class="schema-tags">
                <el-tag
                  v-for="field in state.preview.schema"
                  :key="field"
                  size="large"
                  effect="plain"
                >
                  {{ field }}
                </el-tag>
              </div>
              <p class="schema-note">鎬昏鏁帮細{{ state.preview.rowCount }} 路 褰撳墠宸ヤ綔琛細{{ state.preview.sheet || '榛樿' }}</p>
            </div>
            <div v-if="state.preview.sample.length" class="result-block">
              <p class="result-title">鏍蜂緥鏁版嵁</p>
              <el-table
                :data="state.preview.sample"
                height="260"
                border
                size="small"
                header-cell-class-name="table-header"
              >
                <el-table-column
                  v-for="field in state.preview.schema"
                  :key="field"
                  :prop="field"
                  :label="field"
                  show-overflow-tooltip
                />
              </el-table>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鏁版嵁澶勭悊" name="process">
          <section class="panel">
            <header>
              <h4>鍒嗙粍 / 鎺掑簭 / 瀵煎嚭</h4>
              <p>鎸夌収鎸囧畾鍒楁媶鍒嗗垎琛紝鍙€夊鍑?JSON 渚涘浘琛ㄤ娇鐢?/p>
            </header>
            <el-form :model="state.process" label-width="120px">
              <el-form-item label="鎸夊垪鍒嗙粍">
                <el-select v-model="state.process.groupBy" placeholder="鍙€? clearable style="width: 220px">
                  <el-option
                    v-for="field in schemaFields"
                    :key="field"
                    :label="field"
                    :value="field"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="鎺掑簭瀛楁">
                <div class="field-row">
                  <el-select v-model="state.process.sortBy" placeholder="鍙€? clearable style="width: 220px">
                    <el-option
                      v-for="field in schemaFields"
                      :key="field"
                      :label="field"
                      :value="field"
                    />
                  </el-select>
                  <el-radio-group v-model="state.process.sortOrder" size="small">
                    <el-radio-button label="asc">鍗囧簭</el-radio-button>
                    <el-radio-button label="desc">闄嶅簭</el-radio-button>
                  </el-radio-group>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input
                    v-model="state.process.outputDir"
                    placeholder="鐣欑┖鍒欒嚜鍔ㄥ垱寤?
                    readonly
                  />
                  <el-button @click="selectDir('process')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="瀵煎嚭閫夐」">
                <div class="toggle-row">
                  <el-checkbox v-model="state.process.exportGroups" :disabled="!state.process.groupBy">
                    鍒嗙粍瀵煎嚭 Excel
                  </el-checkbox>
                  <el-checkbox v-model="state.process.exportJson" :disabled="!state.process.groupBy">
                    瀵煎嚭 JSON 鍥捐〃
                  </el-checkbox>
                  <el-checkbox v-model="state.process.exportCombined">
                    鍚堝苟涓昏〃
                  </el-checkbox>
                </div>
              </el-form-item>
            </el-form>

            <div class="subpanel">
              <div class="subpanel-head">
                <div>
                  <h5>闄勫姞鍒嗚〃</h5>
                  <p>鏀寔鍦ㄤ富琛ㄥ墠鎵归噺鍚堝苟澶氫釜鍒嗚〃锛屽啀杩涘叆鍒嗙粍娴佺▼</p>
                </div>
                <div class="field-row">
                  <el-button size="small" @click="selectExcel('processMerge', true)">娣诲姞鍒嗚〃</el-button>
                  <el-button size="small" text type="danger" @click="clearList('processMerge')" :disabled="!state.process.mergeFiles.length">
                    娓呯┖
                  </el-button>
                </div>
              </div>
              <el-table
                v-if="state.process.mergeFiles.length"
                :data="state.process.mergeFiles"
                size="small"
                border
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column prop="filename" label="鏂囦欢鍚? />
                <el-table-column label="宸ヤ綔琛? width="220">
                  <template #default="scope">
                    <el-input
                      v-model="scope.row.sheet"
                      size="small"
                      placeholder="鐣欑┖浣跨敤榛樿宸ヤ綔琛?
                    />
                  </template>
                </el-table-column>
                <el-table-column label="鎿嶄綔" width="80">
                  <template #default="scope">
                    <el-button link type="danger" @click="removeFile('processMerge', scope.$index)">绉婚櫎</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-else description="灏氭湭娣诲姞鍒嗚〃" />
            </div>

            <div class="actions">
              <el-button type="primary" :loading="state.loading" @click="runProcess">鎵ц澶勭悊</el-button>
            </div>

            <div v-if="state.process.summary" class="result-block">
              <p class="result-title">澶勭悊鎽樿</p>
              <el-descriptions :column="2" size="small" border>
                <el-descriptions-item label="鎬昏鏁?>
                  {{ state.process.summary.totalRows }}
                </el-descriptions-item>
                <el-descriptions-item label="鍒嗙粍鍒?>
                  {{ state.process.summary.groupBy || '鏈缃? }}
                </el-descriptions-item>
                <el-descriptions-item label="鎺掑簭鍒?>
                  {{ state.process.summary.sortBy || '鏈缃? }}锛坽{ state.process.summary.sortOrder === 'desc' ? '闄嶅簭' : '鍗囧簭' }}锛?
                </el-descriptions-item>
                <el-descriptions-item label="鍒嗙粍鏁伴噺">
                  {{ state.process.summary.groupCount }}
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="state.process.groups.length" class="group-table">
                <el-table :data="state.process.groups" size="small" border>
                  <el-table-column prop="key" label="鍒嗙粍鍊? />
                  <el-table-column prop="count" label="琛屾暟" width="120" />
                </el-table>
              </div>

              <div class="result-list">
                <template v-if="state.process.groupFiles.length">
                  <p class="result-title">鍒嗙粍鏂囦欢</p>
                  <el-scrollbar max-height="140px">
                    <div class="tag-list">
                      <el-tag
                        v-for="file in state.process.groupFiles"
                        :key="file"
                        type="success"
                        effect="plain"
                        @click="openPath(file)"
                      >
                        {{ file }}
                      </el-tag>
                    </div>
                  </el-scrollbar>
                </template>

                <div class="tag-list">
                  <el-tag
                    v-if="state.process.jsonPath"
                    type="info"
                    effect="plain"
                    @click="openPath(state.process.jsonPath)"
                  >
                    JSON锛歿{ state.process.jsonPath }}
                  </el-tag>
                  <el-tag
                    v-if="state.process.combinedPath"
                    type="warning"
                    effect="plain"
                    @click="openPath(state.process.combinedPath)"
                  >
                    涓昏〃锛歿{ state.process.combinedPath }}
                  </el-tag>
                </div>
              </div>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鍥捐〃鍒朵綔" name="chart">
          <section class="panel">
            <header>
              <h4>Excel 鈫?ECharts</h4>
              <p>鑷姩杞崲涓?JSON 鏁版嵁骞跺疄鏃舵覆鏌撳浘琛?/p>
            </header>
            <el-form :model="state.chart" label-width="120px">
              <el-form-item label="婧?Excel">
                <div class="field-row">
                  <el-button type="primary" @click="selectExcel('chart')">閫夋嫨鏂囦欢</el-button>
                  <span v-if="state.chart.file" class="file-chip">{{ state.chart.file.filename }}</span>
                  <el-tag v-else type="info" effect="plain">灏氭湭閫夋嫨</el-tag>
                </div>
              </el-form-item>
              <el-form-item v-if="state.chart.sheets.length" label="宸ヤ綔琛?>
                <el-select v-model="state.chart.sheet" style="width: 220px">
                  <el-option v-for="sheet in state.chart.sheets" :key="sheet" :label="sheet" :value="sheet" />
                </el-select>
              </el-form-item>
              <el-form-item label="鍒嗛殧绗?>
                <el-input
                  v-model="state.chart.delimiter"
                  placeholder="榛樿浣跨敤 |"
                  maxlength="4"
                  style="width: 120px"
                />
              </el-form-item>
              <el-form-item label="缁撴瀯瀹氫箟">
                <el-input
                  v-model="state.chart.schemaText"
                  type="textarea"
                  :rows="2"
                  placeholder="绀轰緥锛氬湴鍖簗閿€閲弢璐熻矗浜?
                />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="loadChartPreview">鍒锋柊缁撴瀯</el-button>
              </el-form-item>
              <el-form-item label="鍥捐〃绫诲瀷">
                <el-radio-group v-model="state.chart.chartType">
                  <el-radio-button label="bar">鏌辩姸鍥?/el-radio-button>
                  <el-radio-button label="line">鎶樼嚎鍥?/el-radio-button>
                  <el-radio-button label="pie">楗煎浘</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="缁村害鍒?>
                <el-select v-model="state.chart.dimension" placeholder="閫夋嫨鍒嗙被瀛楁" style="width: 220px">
                  <el-option v-for="field in chartFields" :key="field" :label="field" :value="field" />
                </el-select>
              </el-form-item>
              <el-form-item label="鏁板€煎垪">
                <el-select
                  v-model="state.chart.metric"
                  placeholder="閫夋嫨鏁板€煎瓧娈?
                  clearable
                  :disabled="state.chart.aggregate === 'count'"
                  style="width: 220px"
                >
                  <el-option v-for="field in chartFields" :key="field" :label="field" :value="field" />
                </el-select>
              </el-form-item>
              <el-form-item label="缁熻鏂瑰紡">
                <el-select v-model="state.chart.aggregate" style="width: 220px">
                  <el-option label="姹傚拰" value="sum" />
                  <el-option label="鍧囧€? value="avg" />
                  <el-option label="璁℃暟" value="count" />
                </el-select>
              </el-form-item>
            </el-form>

            <div class="actions">
              <el-button type="primary" :loading="state.loading" @click="runChartBuild">鐢熸垚鍥捐〃</el-button>
            </div>

            <div class="format-block">
              <p class="result-title">鏁版嵁鏍煎紡璇存槑</p>
              <div class="format-grid">
                <div class="format-card">
                  <p class="format-title">鍥捐〃鏁版嵁 JSON</p>
                  <pre class="format-code">{{ chartDataSample }}</pre>
                </div>
                <div class="format-card">
                  <p class="format-title">ECharts Option</p>
                  <pre class="format-code">{{ chartOptionSample }}</pre>
                </div>
              </div>
            </div>

            <div v-if="state.chart.data" class="result-block">
              <p class="result-title">鐢熸垚缁撴灉</p>
              <el-descriptions :column="2" size="small" border>
                <el-descriptions-item label="缁村害鍒?>
                  {{ state.chart.data.dimension }}
                </el-descriptions-item>
                <el-descriptions-item label="鏁板€煎垪">
                  {{ state.chart.data.metric || '璁℃暟' }}
                </el-descriptions-item>
                <el-descriptions-item label="缁熻鏂瑰紡">
                  {{ state.chart.data.aggregate }}
                </el-descriptions-item>
                <el-descriptions-item label="鐢熸垚鏃堕棿">
                  {{ state.chart.data.generatedAt }}
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="state.chart.data.rows?.length" class="group-table">
                <el-table :data="state.chart.data.rows" size="small" border>
                  <el-table-column prop="name" label="鍒嗙被" />
                  <el-table-column prop="value" label="鏁板€? width="140" />
                </el-table>
              </div>

              <div class="json-view">
                <div class="json-block">
                  <p class="result-title">鍥捐〃鏁版嵁 JSON</p>
                  <el-input
                    :model-value="state.chart.dataJson"
                    type="textarea"
                    :rows="8"
                    readonly
                  />
                </div>
                <div class="json-block">
                  <p class="result-title">ECharts Option JSON</p>
                  <el-input
                    :model-value="state.chart.optionJson"
                    type="textarea"
                    :rows="8"
                    readonly
                  />
                </div>
              </div>
            </div>

            <div class="chart-preview">
              <p class="result-title">鍥捐〃棰勮</p>
              <div v-show="state.chart.option" ref="chartRef" class="echart-canvas"></div>
              <el-empty v-if="!state.chart.option" description="璇峰厛鐢熸垚鍥捐〃" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鍒嗚〃鍚堝苟" name="merge">
          <section class="panel">
            <header>
              <h4>鐙珛鍚堝苟宸ュ叿</h4>
              <p>灏嗗涓垎琛ㄧ粺涓€瀵煎嚭涓轰竴涓?Excel锛屾柟渚跨敓鎴愪富琛?/p>
            </header>
            <div class="subpanel">
              <div class="subpanel-head">
                <div>
                  <h5>鍒嗚〃鍒楄〃</h5>
                  <p>鏀寔鎵归噺閫夋嫨鎴栧娆℃坊鍔?/p>
                </div>
                <div class="field-row">
                  <el-button size="small" @click="selectExcel('mergeTables', true)">閫夋嫨鏂囦欢</el-button>
                  <el-button
                    size="small"
                    text
                    type="danger"
                    @click="clearList('mergeTables')"
                    :disabled="!state.merge.tables.length"
                  >
                    娓呯┖
                  </el-button>
                </div>
              </div>
              <el-table
                v-if="state.merge.tables.length"
                :data="state.merge.tables"
                size="small"
                border
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column prop="filename" label="鏂囦欢鍚? />
                <el-table-column label="宸ヤ綔琛? width="220">
                  <template #default="scope">
                    <el-input
                      v-model="scope.row.sheet"
                      size="small"
                      placeholder="鐣欑┖浣跨敤榛樿宸ヤ綔琛?
                    />
                  </template>
                </el-table-column>
                <el-table-column label="鎿嶄綔" width="80">
                  <template #default="scope">
                    <el-button link type="danger" @click="removeFile('mergeTables', scope.$index)">绉婚櫎</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-empty v-else description="灏氭湭娣诲姞鍒嗚〃" />
            </div>
            <el-form :model="state.merge" label-width="120px" class="merge-form">
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.merge.outputDir" readonly placeholder="鐣欑┖鑷姩鍒涘缓" />
                  <el-button @click="selectDir('merge')">閫夋嫨鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鏂囦欢鍚?>
                <el-input v-model="state.merge.outputName" placeholder="渚嬪锛氭眹鎬讳富琛?xlsx" />
              </el-form-item>
            </el-form>
            <div class="actions">
              <el-button type="primary" :loading="state.loading" @click="runMergeTables">
                寮€濮嬪悎骞?
              </el-button>
            </div>
            <div v-if="state.merge.result" class="result-block">
              <p class="result-title">杈撳嚭缁撴灉</p>
              <el-tag type="success" effect="plain" @click="openPath(state.merge.result)">
                {{ state.merge.result }}
              </el-tag>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>

      <section class="panel log-panel">
        <header>
          <h4>鎿嶄綔鏃ュ織</h4>
          <p>灞曠ず鏈€杩戠殑鎵ц璁板綍涓庤繑鍥炰俊鎭?/p>
        </header>
        <el-timeline>
          <el-timeline-item
            v-for="item in state.logs"
            :key="item.id"
            :type="item.type"
            :timestamp="item.time"
            placement="top"
          >
            <div class="log-entry">
              <p>{{ item.message }}</p>
              <p class="log-sub">{{ item.action }}</p>
            </div>
          </el-timeline-item>
        </el-timeline>
      </section>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted, onUnmounted, nextTick, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const excelFilter = ['Excel 鏂囦欢 (*.xlsx;*.xlsm;*.xltx;*.xltm)']
const chartDataSample = JSON.stringify(
  {
    dimension: '鍦板尯',
    metric: '閿€閲?,
    aggregate: 'sum',
    rows: [
      { name: '鍗庡寳', value: 120 },
      { name: '鍗庝笢', value: 98 },
      { name: '鍗庡崡', value: 76 }
    ]
  },
  null,
  2
)
const chartOptionSample = JSON.stringify(
  {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['鍗庡寳', '鍗庝笢', '鍗庡崡'] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: [120, 98, 76] }]
  },
  null,
  2
)

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const activeTab = ref('structure')

const state = reactive({
  loading: false,
  preview: {
    file: null,
    sheet: '',
    sheets: [],
    delimiter: '|',
    schemaText: '',
    schema: [],
    sample: [],
    rowCount: 0
  },
  process: {
    groupBy: '',
    sortBy: '',
    sortOrder: 'asc',
    exportGroups: true,
    exportJson: true,
    exportCombined: false,
    outputDir: '',
    summary: null,
    groups: [],
    groupFiles: [],
    jsonPath: '',
    combinedPath: '',
    mergeFiles: []
  },
  chart: {
    file: null,
    sheet: '',
    sheets: [],
    delimiter: '|',
    schemaText: '',
    schema: [],
    chartType: 'bar',
    dimension: '',
    metric: '',
    aggregate: 'sum',
    data: null,
    option: null,
    dataJson: '',
    optionJson: ''
  },
  merge: {
    tables: [],
    outputDir: '',
    outputName: '鍚堝苟涓昏〃.xlsx',
    result: ''
  },
  logs: []
})

const schemaFields = computed(() => state.preview.schema)
const chartFields = computed(() => state.chart.schema)

let suppressSheetReload = false
let suppressChartReload = false

watch(
  () => state.preview.sheet,
  (val, oldVal) => {
    if (suppressSheetReload) return
    if (val === oldVal) return
    if (state.preview.file) {
      loadPreview(true)
    }
  }
)

watch(
  () => state.chart.sheet,
  (val, oldVal) => {
    if (suppressChartReload) return
    if (val === oldVal) return
    if (state.chart.file) {
      loadChartPreview(true)
    }
  }
)

watch(
  () => state.chart.aggregate,
  (val) => {
    if (val === 'count') {
      state.chart.metric = ''
    }
  }
)

watch(
  () => state.chart.schema,
  (schema) => {
    if (!schema.includes(state.chart.dimension)) {
      state.chart.dimension = ''
    }
    if (!schema.includes(state.chart.metric)) {
      state.chart.metric = ''
    }
  },
  { deep: true }
)

const chartRef = ref(null)
const chartInstance = shallowRef(null)

const renderChart = async () => {
  if (!chartRef.value || !state.chart.option) return
  await nextTick()
  if (!chartInstance.value) {
    chartInstance.value = echarts.init(chartRef.value)
  }
  chartInstance.value.setOption(state.chart.option, true)
}

const resizeChart = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

const disposeChart = () => {
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
}

onMounted(() => {
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  disposeChart()
})

watch(
  () => activeTab.value,
  (val) => {
    if (val === 'chart') {
      renderChart()
      nextTick(() => resizeChart())
    }
  }
)

watch(
  () => state.chart.option,
  () => {
    if (activeTab.value === 'chart') {
      renderChart()
    }
  }
)

watch(
  () => props.modelValue,
  (val) => {
    if (!val) {
      disposeChart()
      return
    }
    if (activeTab.value === 'chart') {
      renderChart()
      nextTick(() => resizeChart())
    }
  }
)

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风涓娇鐢?)
    return false
  }
  return true
}

const callApi = async (method, payload) => {
  if (!ensurePyReady()) return null
  const api = window.pywebview.api
  if (!api[method]) {
    ElMessage.error('褰撳墠瀹㈡埛绔増鏈己灏?Excel 鑳藉姏')
    return null
  }
  state.loading = true
  try {
    const res = await api[method](payload)
    if (res?.code === 0) {
      ElMessage.success(res.msg || '鎿嶄綔鎴愬姛')
      pushLog('success', res.msg || '鎿嶄綔鎴愬姛', method)
      return res
    }
    const msg = res?.msg || '鎿嶄綔澶辫触'
    ElMessage.error(msg)
    pushLog('warning', msg, method)
    return null
  } catch (error) {
    ElMessage.error(error.message || '鎵ц澶辫触')
    pushLog('danger', error.message || '鎵ц澶辫触', method)
    return null
  } finally {
    state.loading = false
  }
}

const pushLog = (type, message, action) => {
  state.logs.unshift({
    id: Date.now() + Math.random(),
    type,
    message,
    action,
    time: new Date().toLocaleTimeString()
  })
  if (state.logs.length > 6) {
    state.logs.pop()
  }
}

const selectExcel = async (target, multiple = false) => {
  if (!ensurePyReady()) return
  const result = await window.pywebview.api.system_pyCreateFileDialog(excelFilter)
  if (!result || !result.length) return
  if (target === 'preview') {
    state.preview.file = result[0]
    resetPreviewData()
    await loadPreview(true)
    return
  }
  if (target === 'chart') {
    state.chart.file = result[0]
    resetChartData()
    await loadChartPreview(true)
    return
  }
  const files = multiple ? result : [result[0]]
  const mapped = files.map((item) => ({
    ...item,
    sheet: '',
    id: `${item.path}_${Math.random().toString(16).slice(2)}`
  }))
  if (target === 'processMerge') {
    state.process.mergeFiles.push(...mapped)
  } else if (target === 'mergeTables') {
    state.merge.tables.push(...mapped)
  }
}

const resetPreviewData = () => {
  suppressSheetReload = true
  state.preview.sheet = ''
  suppressSheetReload = false
  state.preview.sheets = []
  state.preview.schema = []
  state.preview.schemaText = ''
  state.preview.sample = []
  state.preview.rowCount = 0
  state.process.groupBy = ''
  state.process.sortBy = ''
  state.process.summary = null
  state.process.groups = []
  state.process.groupFiles = []
  state.process.jsonPath = ''
  state.process.combinedPath = ''
}

const resetChartData = () => {
  suppressChartReload = true
  state.chart.sheet = ''
  suppressChartReload = false
  state.chart.sheets = []
  state.chart.schema = []
  state.chart.schemaText = ''
  state.chart.dimension = ''
  state.chart.metric = ''
  state.chart.data = null
  state.chart.option = null
  state.chart.dataJson = ''
  state.chart.optionJson = ''
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const current =
    target === 'process'
      ? state.process.outputDir
      : state.merge.outputDir
  const dir = await window.pywebview.api.system_pySelectDirDialog(current || '')
  if (!dir) return
  if (target === 'process') {
    state.process.outputDir = dir
  } else {
    state.merge.outputDir = dir
  }
}

const removeFile = (target, index) => {
  if (target === 'processMerge') {
    state.process.mergeFiles.splice(index, 1)
  } else {
    state.merge.tables.splice(index, 1)
  }
}

const clearList = (target) => {
  if (target === 'processMerge') {
    state.process.mergeFiles.splice(0, state.process.mergeFiles.length)
  } else {
    state.merge.tables.splice(0, state.merge.tables.length)
  }
}

const openPath = (path) => {
  if (!path || !ensurePyReady()) return
  window.pywebview.api.system_pyOpenFile(path)
}

const loadPreview = async (silent = false) => {
  if (!state.preview.file) {
    if (!silent) {
      ElMessage.warning('璇烽€夋嫨 Excel 鏂囦欢')
    }
    return
  }
  const res = await callApi('excel_preview', {
    filePath: state.preview.file.path,
    sheetName: state.preview.sheet,
    delimiter: state.preview.delimiter || '|',
    schemaText: state.preview.schemaText
  })
  if (!res) return
  state.preview.schema = res.schema || []
  state.preview.delimiter = res.delimiter || state.preview.delimiter || '|'
  state.preview.schemaText = res.schemaText || state.preview.schema.join(state.preview.delimiter || '|')
  state.preview.rowCount = res.rowCount || 0
  state.preview.sample = res.sample || []
  state.preview.sheets = res.sheets || []
  if (!state.preview.sheet && res.sheet) {
    suppressSheetReload = true
    state.preview.sheet = res.sheet
    suppressSheetReload = false
  }
}

const loadChartPreview = async (silent = false) => {
  if (!state.chart.file) {
    if (!silent) {
      ElMessage.warning('璇烽€夋嫨 Excel 鏂囦欢')
    }
    return
  }
  const res = await callApi('excel_preview', {
    filePath: state.chart.file.path,
    sheetName: state.chart.sheet,
    delimiter: state.chart.delimiter || '|',
    schemaText: state.chart.schemaText
  })
  if (!res) return
  state.chart.schema = res.schema || []
  state.chart.delimiter = res.delimiter || state.chart.delimiter || '|'
  state.chart.schemaText = res.schemaText || state.chart.schema.join(state.chart.delimiter || '|')
  state.chart.sheets = res.sheets || []
  if (!state.chart.sheet && res.sheet) {
    suppressChartReload = true
    state.chart.sheet = res.sheet
    suppressChartReload = false
  }
}

const runProcess = async () => {
  if (!state.preview.file) {
    ElMessage.warning('璇峰厛瀹屾垚缁撴瀯瀹氫箟')
    return
  }
  const payload = {
    filePath: state.preview.file.path,
    sheetName: state.preview.sheet,
    delimiter: state.preview.delimiter || '|',
    schemaText: state.preview.schemaText,
    groupBy: state.process.groupBy,
    sortBy: state.process.sortBy,
    sortOrder: state.process.sortOrder,
    outputDir: state.process.outputDir,
    exportGroups: state.process.exportGroups,
    exportJson: state.process.exportJson,
    exportCombined: state.process.exportCombined,
    mergeFiles: state.process.mergeFiles.map((item) => ({
      path: item.path,
      sheet: item.sheet
    }))
  }
  const res = await callApi('excel_process', payload)
  if (!res) return
  state.process.summary = res.summary
  state.process.groups = res.groups || []
  state.process.groupFiles = res.groupFiles || []
  state.process.jsonPath = res.jsonPath || ''
  state.process.combinedPath = res.combinedPath || ''
  if (res.schema) {
    state.preview.schema = res.schema
  }
}

const runChartBuild = async () => {
  if (!state.chart.file) {
    ElMessage.warning('璇峰厛閫夋嫨 Excel 鏂囦欢')
    return
  }
  if (!state.chart.dimension) {
    ElMessage.warning('璇烽€夋嫨缁村害鍒?)
    return
  }
  if (state.chart.aggregate !== 'count' && !state.chart.metric) {
    ElMessage.warning('璇烽€夋嫨鏁板€煎垪')
    return
  }
  const payload = {
    filePath: state.chart.file.path,
    sheetName: state.chart.sheet,
    delimiter: state.chart.delimiter || '|',
    schemaText: state.chart.schemaText,
    chartType: state.chart.chartType,
    dimension: state.chart.dimension,
    metric: state.chart.metric,
    aggregate: state.chart.aggregate
  }
  const res = await callApi('excel_chart_build', payload)
  if (!res) return
  state.chart.data = res.data || null
  state.chart.option = res.option || null
  state.chart.dataJson = res.data ? JSON.stringify(res.data, null, 2) : ''
  state.chart.optionJson = res.option ? JSON.stringify(res.option, null, 2) : ''
  renderChart()
}

const runMergeTables = async () => {
  if (!state.merge.tables.length) {
    ElMessage.warning('璇峰厛閫夋嫨闇€瑕佸悎骞剁殑鍒嗚〃')
    return
  }
  const res = await callApi('excel_merge_tables', {
    tables: state.merge.tables.map((item) => ({
      path: item.path,
      sheet: item.sheet
    })),
    schemaText: state.preview.schemaText,
    delimiter: state.preview.delimiter || '|',
    outputDir: state.merge.outputDir,
    outputName: state.merge.outputName
  })
  if (!res) return
  state.merge.result = res.output
}
</script>

<style scoped>
/* 浣跨敤鍏ㄥ眬娣辩┖鐜荤拑涓婚鏍峰紡 */

/* 缁撴瀯鏍囩 */
.schema-chips {
  margin-top: 10px;
}

.schema-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.schema-note {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.result-block {
  margin-top: 16px;
}

.result-title {
  margin: 0 0 10px;
  font-weight: 600;
  color: var(--ppx-text-secondary);
}

.toggle-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

/* 瀛愰潰鏉?*/
.subpanel {
  margin-top: 18px;
  border: 1px dashed var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  padding: 12px;
  background: var(--ppx-glass-bg);
}

.subpanel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.subpanel-head h5 {
  margin: 0;
  font-size: 15px;
  color: var(--ppx-text-primary);
}

.subpanel-head p {
  margin: 6px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
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

.tag-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tag-list .el-tag {
  cursor: pointer;
}

.merge-form {
  margin-top: 18px;
}

/* 鏃ュ織闈㈡澘 */
.log-panel header {
  margin-bottom: 10px;
}

.log-panel header h4 {
  margin: 0;
  color: var(--ppx-text-primary);
}

.log-panel header p {
  margin: 6px 0 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}

.log-entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-sub {
  margin: 0;
  color: var(--ppx-text-muted);
  font-size: 12px;
}
</style>

