<script setup>
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'

import PreviewPanel from '../shared/PreviewPanel.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const state = reactive({
  loading: false,
  activeTab: 'codec',
  codec: {
    codecType: 'base64',
    operation: 'encode',
    direction: 'utf8_to_gbk',
    input: '',
    output: ''
  },
  regex: {
    content: '',
    pattern: '',
    flags: [],
    operation: 'search',
    replacement: '',
    matches: [],
    output: ''
  },
  json: {
    operation: 'format',
    input: '',
    path: '',
    output: ''
  },
  csv: {
    direction: 'csv_to_json',
    file: null,
    delimiter: ',',
    outputDir: '',
    outputName: '',
    result: ''
  },
  transform: {
    mode: 'upper',
    input: '',
    output: ''
  },
  dedup: {
    content: '',
    operation: 'deduplicate',
    sortMethod: 'alpha',
    caseSensitive: true,
    trimWhitespace: true,
    keepEmpty: false,
    result: '',
    stats: null,
    frequency: []
  },
  timestamp: {
    direction: 'ts_to_date',
    timestamp: '',
    datetime: '',
    unit: 's',
    timezone: 'Asia/Shanghai',
    result: ''
  },
  hash: {
    sourceType: 'text',
    hashType: 'md5',
    content: '',
    file: null,
    result: ''
  }
})

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('该功能需在桌面客户端使用')
    return false
  }
  return true
}

const runCodec = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.text_encode_decode({
      codecType: state.codec.codecType,
      operation: state.codec.operation,
      direction: state.codec.direction,
      content: state.codec.input
    })
    if (res?.code === 0) {
      state.codec.output = res.result || ''
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    state.loading = false
  }
}

const runRegex = async () => {
  if (!ensurePyReady()) return
  if (!state.regex.pattern.trim()) {
    ElMessage.warning('请输入正则表达式')
    return
  }
  state.loading = true
  try {
    const payload = {
      content: state.regex.content,
      pattern: state.regex.pattern,
      flags: state.regex.flags,
      operation: state.regex.operation,
      replacement: state.regex.replacement
    }
    const res = await window.pywebview.api.text_regex_match(payload)
    if (res?.code === 0) {
      state.regex.matches = res.matches || []
      state.regex.output = res.result || res.extracted?.join('\n') || ''
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    state.loading = false
  }
}

const runJson = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.text_format_json({
      operation: state.json.operation,
      content: state.json.input,
      path: state.json.path
    })
    if (res?.code === 0) {
      state.json.output = typeof res.result === 'string' ? res.result : JSON.stringify(res.result, null, 2)
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    state.loading = false
  }
}

const runCsvJson = async () => {
  if (!ensurePyReady()) return
  if (!state.csv.file) {
    ElMessage.warning('请选择文件')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.text_convert_csv_json({
      direction: state.csv.direction,
      file: state.csv.file,
      delimiter: state.csv.delimiter,
      outputDir: state.csv.outputDir,
      outputName: state.csv.outputName
    })
    if (res?.code === 0) {
      state.csv.result = res.file || ''
      ElMessage.success(res.msg || '转换完成')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const runTransform = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.text_case_transform({
      mode: state.transform.mode,
      content: state.transform.input
    })
    if (res?.code === 0) {
      state.transform.output = res.result || ''
      ElMessage.success(res.msg || '转换成功')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const runDedup = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.text_deduplicate_sort({
      content: state.dedup.content,
      operation: state.dedup.operation,
      sortMethod: state.dedup.sortMethod,
      caseSensitive: state.dedup.caseSensitive,
      trimWhitespace: state.dedup.trimWhitespace,
      keepEmpty: state.dedup.keepEmpty
    })
    if (res?.code === 0) {
      state.dedup.result = res.result || ''
      state.dedup.stats = res.stats || null
      state.dedup.frequency = res.frequency || []
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
  } finally {
    state.loading = false
  }
}

const runTimestamp = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const payload = {
      direction: state.timestamp.direction,
      timezone: state.timestamp.timezone,
      unit: state.timestamp.unit
    }
    if (state.timestamp.direction === 'ts_to_date') {
      payload.timestamp = state.timestamp.timestamp
    } else {
      payload.datetime = state.timestamp.datetime
    }
    const res = await window.pywebview.api.text_timestamp_convert(payload)
    if (res?.code === 0) {
      state.timestamp.result = JSON.stringify(res, null, 2)
      ElMessage.success(res.msg || '转换完成')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const runHash = async () => {
  if (!ensurePyReady()) return
  if (state.hash.sourceType === 'file' && !state.hash.file) {
    ElMessage.warning('请选择文件')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.text_hash_calculate({
      sourceType: state.hash.sourceType,
      hashType: state.hash.hashType,
      content: state.hash.content,
      file: state.hash.file
    })
    if (res?.code === 0) {
      state.hash.result = res.result || ''
      ElMessage.success(res.msg || '计算完成')
    } else {
      ElMessage.error(res?.msg || '计算失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '计算失败')
  } finally {
    state.loading = false
  }
}

const selectHashFile = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['全部文件 (*.*)'])
  if (files?.length) {
    state.hash.file = files[0]
  }
}

const selectCsvFile = async () => {
  if (!ensurePyReady()) return
  const filter = state.csv.direction === 'csv_to_json' ? ['CSV 文件 (*.csv)'] : ['JSON 文件 (*.json)']
  const files = await window.pywebview.api.system_pyCreateFileDialog(filter)
  if (files?.length) {
    state.csv.file = files[0]
  }
}

const selectCsvOutputDir = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.csv.outputDir)
  if (dir) {
    state.csv.outputDir = dir
  }
}

const openFile = (path) => {
  if (!ensurePyReady() || !path) return
  window.pywebview.api.system_pyOpenFile(path)
}
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="70%"
    append-to-body
    custom-class="text-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">TEXT SUITE</p>
          <h3>文本与数据处理</h3>
          <p class="sub">编码、正则、CSV/JSON、排序、哈希一站完成</p>
        </div>
        <el-tag type="warning">Phase 2</el-tag>
      </div>
    </template>
    <div class="text-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="编码 / 解码" name="codec">
          <section class="panel">
            <header>
              <h4>常见文本编码</h4>
              <p>Base64、URL、HTML 与 UTF-8/GBK 互转</p>
            </header>
            <el-form :model="state.codec" label-width="120px">
              <el-form-item label="编码类型">
                <el-select v-model="state.codec.codecType" style="width: 200px">
                  <el-option label="Base64" value="base64" />
                  <el-option label="URL" value="url" />
                  <el-option label="HTML" value="html" />
                  <el-option label="字符集转换" value="charset" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.codec.codecType !== 'charset'" label="操作">
                <el-radio-group v-model="state.codec.operation">
                  <el-radio-button label="encode">编码</el-radio-button>
                  <el-radio-button label="decode">解码</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-else label="方向">
                <el-radio-group v-model="state.codec.direction">
                  <el-radio-button label="utf8_to_gbk">UTF-8 → GBK</el-radio-button>
                  <el-radio-button label="gbk_to_utf8">GBK → UTF-8</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.codec.input"
                type="textarea"
                :rows="8"
                placeholder="在此输入原文本"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runCodec">执行</el-button>
              </div>
              <el-input
                v-model="state.codec.output"
                type="textarea"
                :rows="8"
                placeholder="输出结果"
                readonly
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="正则工具" name="regex">
          <section class="panel">
            <header>
              <h4>正则匹配 / 替换 / 提取</h4>
              <p>支持多种 Flag，实时回显命中区间</p>
            </header>
            <el-form :model="state.regex" label-width="120px" class="form-gap">
              <el-form-item label="操作">
                <el-radio-group v-model="state.regex.operation">
                  <el-radio-button label="search">匹配</el-radio-button>
                  <el-radio-button label="replace">替换</el-radio-button>
                  <el-radio-button label="extract">提取</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="正则表达式">
                <el-input v-model="state.regex.pattern" placeholder="例如：\\d{3}-\\d{4}" />
              </el-form-item>
              <el-form-item label="标志">
                <el-checkbox-group v-model="state.regex.flags">
                  <el-checkbox label="ignorecase">忽略大小写</el-checkbox>
                  <el-checkbox label="multiline">多行</el-checkbox>
                  <el-checkbox label="dotall">DotAll</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item v-if="state.regex.operation === 'replace'" label="替换为">
                <el-input v-model="state.regex.replacement" placeholder="输入替换文本" />
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.regex.content"
                type="textarea"
                :rows="8"
                placeholder="输入原始文本"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runRegex">执行</el-button>
              </div>
              <PreviewPanel title="输出 / 命中" :content="state.regex.output" />
            </div>
            <el-table
              v-if="state.regex.matches.length && state.regex.operation !== 'replace'"
              :data="state.regex.matches"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column label="匹配文本" prop="match" />
              <el-table-column label="开始" prop="start" width="80" />
              <el-table-column label="结束" prop="end" width="80" />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="JSON 工具" name="json">
          <section class="panel">
            <header>
              <h4>JSON 格式化、压缩与查询</h4>
              <p>支持 JSONPath 风格的 $ 节点查询</p>
            </header>
            <el-form :model="state.json" label-width="120px" class="form-gap">
              <el-form-item label="操作">
                <el-select v-model="state.json.operation" style="width: 220px">
                  <el-option label="美化" value="format" />
                  <el-option label="压缩" value="compress" />
                  <el-option label="校验" value="validate" />
                  <el-option label="查询" value="query" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.json.operation === 'query'" label="路径">
                <el-input
                  v-model="state.json.path"
                  placeholder="示例：$.items[0].name"
                  clearable
                />
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.json.input"
                type="textarea"
                :rows="10"
                placeholder="粘贴 JSON 字符串"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runJson">执行</el-button>
              </div>
              <PreviewPanel title="输出" :content="state.json.output" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="CSV / JSON 转换" name="csv">
          <section class="panel">
            <header>
              <h4>结构化数据互转</h4>
              <p>CSV ↔ JSON，支持自定义分隔符与输出目录</p>
            </header>
            <el-form :model="state.csv" label-width="130px" class="form-gap">
              <el-form-item label="方向">
                <el-radio-group v-model="state.csv.direction">
                  <el-radio-button label="csv_to_json">CSV → JSON</el-radio-button>
                  <el-radio-button label="json_to_csv">JSON → CSV</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="源文件">
                <div class="field-row">
                  <el-input :model-value="state.csv.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectCsvFile">选择</el-button>
                </div>
              </el-form-item>
              <el-form-item label="分隔符">
                <el-input v-model="state.csv.delimiter" style="width: 120px" />
              </el-form-item>
              <el-form-item label="输出目录">
                <div class="field-row">
                  <el-input v-model="state.csv.outputDir" placeholder="自动使用源目录" readonly />
                  <el-button @click="selectCsvOutputDir">目录</el-button>
                </div>
              </el-form-item>
              <el-form-item label="输出名称">
                <el-input v-model="state.csv.outputName" placeholder="可选" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCsvJson">开始转换</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.csv.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                已输出：<a class="link" @click.prevent="openFile(state.csv.result)">{{ state.csv.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="文本转换" name="transform">
          <section class="panel">
            <header>
              <h4>大小写与命名规范</h4>
              <p>一键切换 Upper / Lower / Camel / Snake</p>
            </header>
            <el-form :model="state.transform" label-width="120px" class="form-gap">
              <el-form-item label="转换类型">
                <el-select v-model="state.transform.mode" style="width: 240px">
                  <el-option label="全大写" value="upper" />
                  <el-option label="全小写" value="lower" />
                  <el-option label="标题格式" value="title" />
                  <el-option label="句首大写" value="sentence" />
                  <el-option label="camelCase" value="camel" />
                  <el-option label="PascalCase" value="pascal" />
                  <el-option label="snake_case" value="snake" />
                  <el-option label="kebab-case" value="kebab" />
                </el-select>
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.transform.input"
                type="textarea"
                :rows="6"
                placeholder="输入原始文本"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runTransform">转换</el-button>
              </div>
              <PreviewPanel title="结果" :content="state.transform.output" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="去重 / 排序" name="dedup">
          <section class="panel">
            <header>
              <h4>多行文本去重与排序</h4>
              <p>自定义大小写敏感、保留空行以及词频统计</p>
            </header>
            <el-form :model="state.dedup" label-width="130px" class="form-gap">
              <el-form-item label="操作">
                <el-radio-group v-model="state.dedup.operation">
                  <el-radio-button label="deduplicate">去重</el-radio-button>
                  <el-radio-button label="sort">排序</el-radio-button>
                  <el-radio-button label="frequency">词频</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="排序方式" v-if="state.dedup.operation === 'sort'">
                <el-select v-model="state.dedup.sortMethod" style="width: 220px">
                  <el-option label="字典序" value="alpha" />
                  <el-option label="按长度" value="length" />
                </el-select>
              </el-form-item>
              <el-form-item label="选项">
                <el-checkbox v-model="state.dedup.caseSensitive">区分大小写</el-checkbox>
                <el-checkbox v-model="state.dedup.trimWhitespace">裁剪空白</el-checkbox>
                <el-checkbox v-model="state.dedup.keepEmpty">保留空行</el-checkbox>
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.dedup.content"
                type="textarea"
                :rows="8"
                placeholder="每行一个条目"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runDedup">执行</el-button>
              </div>
              <PreviewPanel title="输出" :content="state.dedup.result" />
            </div>
            <div v-if="state.dedup.stats" class="stats-panel">
              <el-descriptions :column="4" border size="small">
                <el-descriptions-item label="原始行数">{{ state.dedup.stats.originalCount }}</el-descriptions-item>
                <el-descriptions-item label="有效行数">{{ state.dedup.stats.effectiveCount }}</el-descriptions-item>
                <el-descriptions-item label="唯一计数">{{ state.dedup.stats.uniqueCount }}</el-descriptions-item>
                <el-descriptions-item label="移除行数">{{ state.dedup.stats.removedCount }}</el-descriptions-item>
              </el-descriptions>
            </div>
            <el-table
              v-if="state.dedup.frequency.length"
              :data="state.dedup.frequency"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column label="条目" prop="value" />
              <el-table-column label="次数" prop="count" width="100" />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="时间戳转换" name="timestamp">
          <section class="panel">
            <header>
              <h4>时间戳 ↔ 日期</h4>
              <p>支持秒/毫秒与多时区转换</p>
            </header>
            <el-form :model="state.timestamp" label-width="120px" class="form-gap">
              <el-form-item label="方向">
                <el-radio-group v-model="state.timestamp.direction">
                  <el-radio-button label="ts_to_date">时间戳 → 日期</el-radio-button>
                  <el-radio-button label="date_to_ts">日期 → 时间戳</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="单位" v-if="state.timestamp.direction === 'ts_to_date'">
                <el-radio-group v-model="state.timestamp.unit">
                  <el-radio-button label="s">秒</el-radio-button>
                  <el-radio-button label="ms">毫秒</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.timestamp.direction === 'ts_to_date'" label="时间戳">
                <el-input v-model="state.timestamp.timestamp" placeholder="例如 1700000000 或 1700000000000" />
              </el-form-item>
              <el-form-item v-else label="日期时间">
                <el-input v-model="state.timestamp.datetime" placeholder="2024-11-01 08:00:00" />
              </el-form-item>
              <el-form-item label="时区">
                <el-input v-model="state.timestamp.timezone" placeholder="如 Asia/Shanghai 或 UTC+8" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runTimestamp">转换</el-button>
              </el-form-item>
            </el-form>
            <PreviewPanel v-if="state.timestamp.result" title="结果 JSON" :content="state.timestamp.result" />
          </section>
        </el-tab-pane>

        <el-tab-pane label="哈希计算" name="hash">
          <section class="panel">
            <header>
              <h4>MD5 / SHA 系列</h4>
              <p>支持字符串与文件两种来源</p>
            </header>
            <el-form :model="state.hash" label-width="120px" class="form-gap">
              <el-form-item label="输入类型">
                <el-radio-group v-model="state.hash.sourceType">
                  <el-radio-button label="text">文本</el-radio-button>
                  <el-radio-button label="file">文件</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="算法">
                <el-select v-model="state.hash.hashType" style="width: 200px">
                  <el-option label="MD5" value="md5" />
                  <el-option label="SHA-1" value="sha1" />
                  <el-option label="SHA-256" value="sha256" />
                  <el-option label="SHA-512" value="sha512" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.hash.sourceType === 'text'" label="文本">
                <el-input
                  v-model="state.hash.content"
                  type="textarea"
                  :rows="4"
                  placeholder="输入要计算的文本"
                />
              </el-form-item>
              <el-form-item v-else label="文件">
                <div class="field-row">
                  <el-input :model-value="state.hash.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectHashFile">选择文件</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runHash">开始计算</el-button>
              </el-form-item>
            </el-form>
            <el-input v-model="state.hash.result" readonly placeholder="哈希结果" />
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  color: #8d90a2;
  letter-spacing: 2px;
}

.panel {
  background: #fff;
  border: 1px solid #e9edf5;
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 24px;
}

.panel header h4 {
  margin: 0;
}

.panel header p {
  margin: 6px 0 0;
  color: #7a829d;
  font-size: 13px;
}

.text-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px minmax(0, 1fr);
  gap: 16px;
}

.text-grid-actions {
  display: flex;
  align-items: center;
  justify-content: center;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.form-gap {
  margin-top: 12px;
}

.stats-panel {
  margin-top: 16px;
}

.link {
  color: #2f73ff;
}
</style>
