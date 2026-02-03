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

let replaceRuleSeed = 1

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
  replace: {
    content: '',
    rules: [
      {
        id: replaceRuleSeed,
        search: '',
        replace: '',
        regex: false,
        caseSensitive: true,
        enabled: true,
        limit: 0
      }
    ],
    result: '',
    report: []
  },
  unicode: {
    mode: 'escape',
    content: '',
    codePoints: '',
    result: '',
    preview: []
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
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风浣跨敤')
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
      ElMessage.success(res.msg || '澶勭悊瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶勭悊澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶勭悊澶辫触')
  } finally {
    state.loading = false
  }
}

const runRegex = async () => {
  if (!ensurePyReady()) return
  if (!state.regex.pattern.trim()) {
    ElMessage.warning('璇疯緭鍏ユ鍒欒〃杈惧紡')
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
      ElMessage.success(res.msg || '澶勭悊瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶勭悊澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶勭悊澶辫触')
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
      ElMessage.success(res.msg || '澶勭悊瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶勭悊澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶勭悊澶辫触')
  } finally {
    state.loading = false
  }
}

const runCsvJson = async () => {
  if (!ensurePyReady()) return
  if (!state.csv.file) {
    ElMessage.warning('璇烽€夋嫨鏂囦欢')
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
      ElMessage.success(res.msg || '杞崲瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '杞崲澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '杞崲澶辫触')
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
      ElMessage.success(res.msg || '杞崲鎴愬姛')
    } else {
      ElMessage.error(res?.msg || '杞崲澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '杞崲澶辫触')
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
      ElMessage.success(res.msg || '澶勭悊瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶勭悊澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶勭悊澶辫触')
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
      ElMessage.success(res.msg || '杞崲瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '杞崲澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '杞崲澶辫触')
  } finally {
    state.loading = false
  }
}

const addReplaceRule = () => {
  replaceRuleSeed += 1
  state.replace.rules.push({
    id: replaceRuleSeed,
    search: '',
    replace: '',
    regex: false,
    caseSensitive: true,
    enabled: true,
    limit: 0
  })
}

const removeReplaceRule = (index) => {
  state.replace.rules.splice(index, 1)
  if (!state.replace.rules.length) {
    addReplaceRule()
  }
}

const runReplace = async () => {
  if (!ensurePyReady()) return
  const rules = state.replace.rules.filter((rule) => rule.enabled && rule.search?.trim())
  if (!rules.length) {
    ElMessage.warning('璇疯嚦灏戝惎鐢ㄤ竴鏉¤鍒?)
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.text_batch_replace({
      content: state.replace.content,
      rules
    })
    if (res?.code === 0 || res?.success) {
      state.replace.result = res.result || ''
      state.replace.report = res.report || []
      ElMessage.success(res.msg || '澶勭悊瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶勭悊澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶勭悊澶辫触')
  } finally {
    state.loading = false
  }
}

const runUnicode = async () => {
  if (!ensurePyReady()) return
  state.loading = true
  try {
    const res = await window.pywebview.api.text_unicode_convert({
      mode: state.unicode.mode,
      content: state.unicode.content,
      codePoints: state.unicode.codePoints,
      uppercase: true
    })
    if (res?.code === 0 || res?.success) {
      state.unicode.result = res.result || ''
      state.unicode.preview = res.codepoints || res.preview || []
      ElMessage.success(res.msg || '澶勭悊瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶勭悊澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶勭悊澶辫触')
  } finally {
    state.loading = false
  }
}

const runHash = async () => {
  if (!ensurePyReady()) return
  if (state.hash.sourceType === 'file' && !state.hash.file) {
    ElMessage.warning('璇烽€夋嫨鏂囦欢')
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
      ElMessage.success(res.msg || '璁＄畻瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '璁＄畻澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '璁＄畻澶辫触')
  } finally {
    state.loading = false
  }
}

const selectHashFile = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['鍏ㄩ儴鏂囦欢 (*.*)'])
  if (files?.length) {
    state.hash.file = files[0]
  }
}

const selectCsvFile = async () => {
  if (!ensurePyReady()) return
  const filter = state.csv.direction === 'csv_to_json' ? ['CSV 鏂囦欢 (*.csv)'] : ['JSON 鏂囦欢 (*.json)']
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
          <h3>鏂囨湰涓庢暟鎹鐞?/h3>
          <p class="sub">缂栫爜銆佹鍒欍€丆SV/JSON銆佹帓搴忋€佸搱甯屼竴绔欏畬鎴?/p>
        </div>
      </div>
    </template>
    <div class="text-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="缂栫爜 / 瑙ｇ爜" name="codec">
          <section class="panel">
            <header>
              <h4>甯歌鏂囨湰缂栫爜</h4>
              <p>Base64銆乁RL銆丠TML 涓?UTF-8/GBK 浜掕浆</p>
            </header>
            <el-form :model="state.codec" label-width="120px">
              <el-form-item label="缂栫爜绫诲瀷">
                <el-select v-model="state.codec.codecType" style="width: 200px">
                  <el-option label="Base64" value="base64" />
                  <el-option label="URL" value="url" />
                  <el-option label="HTML" value="html" />
                  <el-option label="瀛楃闆嗚浆鎹? value="charset" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.codec.codecType !== 'charset'" label="鎿嶄綔">
                <el-radio-group v-model="state.codec.operation">
                  <el-radio-button label="encode">缂栫爜</el-radio-button>
                  <el-radio-button label="decode">瑙ｇ爜</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-else label="鏂瑰悜">
                <el-radio-group v-model="state.codec.direction">
                  <el-radio-button label="utf8_to_gbk">UTF-8 鈫?GBK</el-radio-button>
                  <el-radio-button label="gbk_to_utf8">GBK 鈫?UTF-8</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.codec.input"
                type="textarea"
                :rows="8"
                placeholder="鍦ㄦ杈撳叆鍘熸枃鏈?
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runCodec">鎵ц</el-button>
              </div>
              <el-input
                v-model="state.codec.output"
                type="textarea"
                :rows="8"
                placeholder="杈撳嚭缁撴灉"
                readonly
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="姝ｅ垯宸ュ叿" name="regex">
          <section class="panel">
            <header>
              <h4>姝ｅ垯鍖归厤 / 鏇挎崲 / 鎻愬彇</h4>
              <p>鏀寔澶氱 Flag锛屽疄鏃跺洖鏄惧懡涓尯闂?/p>
            </header>
            <el-form :model="state.regex" label-width="120px" class="form-gap">
              <el-form-item label="鎿嶄綔">
                <el-radio-group v-model="state.regex.operation">
                  <el-radio-button label="search">鍖归厤</el-radio-button>
                  <el-radio-button label="replace">鏇挎崲</el-radio-button>
                  <el-radio-button label="extract">鎻愬彇</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="姝ｅ垯琛ㄨ揪寮?>
                <el-input v-model="state.regex.pattern" placeholder="渚嬪锛歕\d{3}-\\d{4}" />
              </el-form-item>
              <el-form-item label="鏍囧織">
                <el-checkbox-group v-model="state.regex.flags">
                  <el-checkbox label="ignorecase">蹇界暐澶у皬鍐?/el-checkbox>
                  <el-checkbox label="multiline">澶氳</el-checkbox>
                  <el-checkbox label="dotall">DotAll</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
              <el-form-item v-if="state.regex.operation === 'replace'" label="鏇挎崲涓?>
                <el-input v-model="state.regex.replacement" placeholder="杈撳叆鏇挎崲鏂囨湰" />
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.regex.content"
                type="textarea"
                :rows="8"
                placeholder="杈撳叆鍘熷鏂囨湰"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runRegex">鎵ц</el-button>
              </div>
              <PreviewPanel title="杈撳嚭 / 鍛戒腑" :content="state.regex.output" />
            </div>
            <el-table
              v-if="state.regex.matches.length && state.regex.operation !== 'replace'"
              :data="state.regex.matches"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column label="鍖归厤鏂囨湰" prop="match" />
              <el-table-column label="寮€濮? prop="start" width="80" />
              <el-table-column label="缁撴潫" prop="end" width="80" />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="JSON 宸ュ叿" name="json">
          <section class="panel">
            <header>
              <h4>JSON 鏍煎紡鍖栥€佸帇缂╀笌鏌ヨ</h4>
              <p>鏀寔 JSONPath 椋庢牸鐨?$ 鑺傜偣鏌ヨ</p>
            </header>
            <el-form :model="state.json" label-width="120px" class="form-gap">
              <el-form-item label="鎿嶄綔">
                <el-select v-model="state.json.operation" style="width: 220px">
                  <el-option label="缇庡寲" value="format" />
                  <el-option label="鍘嬬缉" value="compress" />
                  <el-option label="鏍￠獙" value="validate" />
                  <el-option label="鏌ヨ" value="query" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.json.operation === 'query'" label="璺緞">
                <el-input
                  v-model="state.json.path"
                  placeholder="绀轰緥锛?.items[0].name"
                  clearable
                />
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.json.input"
                type="textarea"
                :rows="10"
                placeholder="绮樿创 JSON 瀛楃涓?
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runJson">鎵ц</el-button>
              </div>
              <PreviewPanel title="杈撳嚭" :content="state.json.output" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="CSV / JSON 杞崲" name="csv">
          <section class="panel">
            <header>
              <h4>缁撴瀯鍖栨暟鎹簰杞?/h4>
              <p>CSV 鈫?JSON锛屾敮鎸佽嚜瀹氫箟鍒嗛殧绗︿笌杈撳嚭鐩綍</p>
            </header>
            <el-form :model="state.csv" label-width="130px" class="form-gap">
              <el-form-item label="鏂瑰悜">
                <el-radio-group v-model="state.csv.direction">
                  <el-radio-button label="csv_to_json">CSV 鈫?JSON</el-radio-button>
                  <el-radio-button label="json_to_csv">JSON 鈫?CSV</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="婧愭枃浠?>
                <div class="field-row">
                  <el-input :model-value="state.csv.file?.path || ''" placeholder="灏氭湭閫夋嫨" readonly />
                  <el-button @click="selectCsvFile">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鍒嗛殧绗?>
                <el-input v-model="state.csv.delimiter" style="width: 120px" />
              </el-form-item>
              <el-form-item label="杈撳嚭鐩綍">
                <div class="field-row">
                  <el-input v-model="state.csv.outputDir" placeholder="鑷姩浣跨敤婧愮洰褰? readonly />
                  <el-button @click="selectCsvOutputDir">鐩綍</el-button>
                </div>
              </el-form-item>
              <el-form-item label="杈撳嚭鍚嶇О">
                <el-input v-model="state.csv.outputName" placeholder="鍙€? />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCsvJson">寮€濮嬭浆鎹?/el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.csv.result"
              type="success"
              :closable="false"
              show-icon
            >
              <template #title>
                宸茶緭鍑猴細<a class="link" @click.prevent="openFile(state.csv.result)">{{ state.csv.result }}</a>
              </template>
            </el-alert>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鏂囨湰杞崲" name="transform">
          <section class="panel">
            <header>
              <h4>澶у皬鍐欎笌鍛藉悕瑙勮寖</h4>
              <p>涓€閿垏鎹?Upper / Lower / Camel / Snake</p>
            </header>
            <el-form :model="state.transform" label-width="120px" class="form-gap">
              <el-form-item label="杞崲绫诲瀷">
                <el-select v-model="state.transform.mode" style="width: 240px">
                  <el-option label="鍏ㄥぇ鍐? value="upper" />
                  <el-option label="鍏ㄥ皬鍐? value="lower" />
                  <el-option label="鏍囬鏍煎紡" value="title" />
                  <el-option label="鍙ラ澶у啓" value="sentence" />
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
                placeholder="杈撳叆鍘熷鏂囨湰"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runTransform">杞崲</el-button>
              </div>
              <PreviewPanel title="缁撴灉" :content="state.transform.output" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鍘婚噸 / 鎺掑簭" name="dedup">
          <section class="panel">
            <header>
              <h4>澶氳鏂囨湰鍘婚噸涓庢帓搴?/h4>
              <p>鑷畾涔夊ぇ灏忓啓鏁忔劅銆佷繚鐣欑┖琛屼互鍙婅瘝棰戠粺璁?/p>
            </header>
            <el-form :model="state.dedup" label-width="130px" class="form-gap">
              <el-form-item label="鎿嶄綔">
                <el-radio-group v-model="state.dedup.operation">
                  <el-radio-button label="deduplicate">鍘婚噸</el-radio-button>
                  <el-radio-button label="sort">鎺掑簭</el-radio-button>
                  <el-radio-button label="frequency">璇嶉</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="鎺掑簭鏂瑰紡" v-if="state.dedup.operation === 'sort'">
                <el-select v-model="state.dedup.sortMethod" style="width: 220px">
                  <el-option label="瀛楀吀搴? value="alpha" />
                  <el-option label="鎸夐暱搴? value="length" />
                </el-select>
              </el-form-item>
              <el-form-item label="閫夐」">
                <el-checkbox v-model="state.dedup.caseSensitive">鍖哄垎澶у皬鍐?/el-checkbox>
                <el-checkbox v-model="state.dedup.trimWhitespace">瑁佸壀绌虹櫧</el-checkbox>
                <el-checkbox v-model="state.dedup.keepEmpty">淇濈暀绌鸿</el-checkbox>
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.dedup.content"
                type="textarea"
                :rows="8"
                placeholder="姣忚涓€涓潯鐩?
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runDedup">鎵ц</el-button>
              </div>
              <PreviewPanel title="杈撳嚭" :content="state.dedup.result" />
            </div>
            <div v-if="state.dedup.stats" class="stats-panel">
              <el-descriptions :column="4" border size="small">
                <el-descriptions-item label="鍘熷琛屾暟">{{ state.dedup.stats.originalCount }}</el-descriptions-item>
                <el-descriptions-item label="鏈夋晥琛屾暟">{{ state.dedup.stats.effectiveCount }}</el-descriptions-item>
                <el-descriptions-item label="鍞竴璁℃暟">{{ state.dedup.stats.uniqueCount }}</el-descriptions-item>
                <el-descriptions-item label="绉婚櫎琛屾暟">{{ state.dedup.stats.removedCount }}</el-descriptions-item>
              </el-descriptions>
            </div>
            <el-table
              v-if="state.dedup.frequency.length"
              :data="state.dedup.frequency"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column label="鏉＄洰" prop="value" />
              <el-table-column label="娆℃暟" prop="count" width="100" />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鎵归噺鏇挎崲" name="replace">
          <section class="panel">
            <header>
              <h4>鎵归噺鏇挎崲瑙勫垯</h4>
              <p>鏀寔鏂囨湰/姝ｅ垯妯″紡銆佸尯鍒嗗ぇ灏忓啓銆佹浛鎹㈡鏁伴檺鍒讹紝闄勬墽琛屾姤鍛?/p>
            </header>
            <div class="rule-toolbar">
              <span>鏇挎崲瑙勫垯</span>
              <el-button size="small" type="primary" text @click="addReplaceRule">鏂板瑙勫垯</el-button>
            </div>
            <div class="rule-list">
              <div v-for="(rule, index) in state.replace.rules" :key="rule.id" class="rule-row">
                <div class="rule-row-line">
                  <el-checkbox v-model="rule.enabled">鍚敤</el-checkbox>
                  <el-checkbox v-model="rule.regex">姝ｅ垯</el-checkbox>
                  <el-checkbox v-model="rule.caseSensitive" :disabled="rule.regex">鍖哄垎澶у皬鍐?/el-checkbox>
                  <el-input-number
                    v-model="rule.limit"
                    :min="0"
                    :max="999"
                    :step="1"
                    size="small"
                    style="width: 120px"
                  />
                  <el-button size="small" text type="danger" @click="removeReplaceRule(index)">绉婚櫎</el-button>
                </div>
                <el-input v-model="rule.search" placeholder="鏌ユ壘鍐呭锛堟敮鎸佹鍒欙級" />
                <el-input v-model="rule.replace" placeholder="鏇挎崲涓猴紙鍙暀绌猴級" />
              </div>
            </div>
            <div class="text-grid">
              <el-input
                v-model="state.replace.content"
                type="textarea"
                :rows="8"
                placeholder="杈撳叆鍘熷鏂囨湰"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runReplace">鎵ц</el-button>
              </div>
              <PreviewPanel title="杈撳嚭" :content="state.replace.result" />
            </div>
            <el-table
              v-if="state.replace.report.length"
              :data="state.replace.report"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column type="index" width="60" label="#" />
              <el-table-column prop="search" label="鏌ユ壘" show-overflow-tooltip />
              <el-table-column prop="replacement" label="鏇挎崲涓? show-overflow-tooltip />
              <el-table-column prop="count" label="褰卞搷鏉℃暟" width="120" />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鏃堕棿鎴宠浆鎹? name="timestamp">
          <section class="panel">
            <header>
              <h4>鏃堕棿鎴?鈫?鏃ユ湡</h4>
              <p>鏀寔绉?姣涓庡鏃跺尯杞崲</p>
            </header>
            <el-form :model="state.timestamp" label-width="120px" class="form-gap">
              <el-form-item label="鏂瑰悜">
                <el-radio-group v-model="state.timestamp.direction">
                  <el-radio-button label="ts_to_date">鏃堕棿鎴?鈫?鏃ユ湡</el-radio-button>
                  <el-radio-button label="date_to_ts">鏃ユ湡 鈫?鏃堕棿鎴?/el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="鍗曚綅" v-if="state.timestamp.direction === 'ts_to_date'">
                <el-radio-group v-model="state.timestamp.unit">
                  <el-radio-button label="s">绉?/el-radio-button>
                  <el-radio-button label="ms">姣</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.timestamp.direction === 'ts_to_date'" label="鏃堕棿鎴?>
                <el-input v-model="state.timestamp.timestamp" placeholder="渚嬪 1700000000 鎴?1700000000000" />
              </el-form-item>
              <el-form-item v-else label="鏃ユ湡鏃堕棿">
                <el-input v-model="state.timestamp.datetime" placeholder="2024-11-01 08:00:00" />
              </el-form-item>
              <el-form-item label="鏃跺尯">
                <el-input v-model="state.timestamp.timezone" placeholder="濡?Asia/Shanghai 鎴?UTC+8" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runTimestamp">杞崲</el-button>
              </el-form-item>
            </el-form>
            <PreviewPanel v-if="state.timestamp.result" title="缁撴灉 JSON" :content="state.timestamp.result" />
          </section>
        </el-tab-pane>

        <el-tab-pane label="Unicode 宸ュ叿" name="unicode">
          <section class="panel">
            <header>
              <h4>Unicode 缂栫爜 / 瑙ｇ爜</h4>
              <p>鍦ㄦ枃鏈笌 \\uXXXX銆佺紪鐮佺偣闂村揩閫熻浆鎹紝鏀寔鎵归噺鍒楄〃</p>
            </header>
            <el-form :model="state.unicode" label-width="120px" class="form-gap">
              <el-form-item label="妯″紡">
                <el-radio-group v-model="state.unicode.mode">
                  <el-radio-button label="escape">鏂囨湰 鈫?\\u</el-radio-button>
                  <el-radio-button label="unescape">\\u 鈫?鏂囨湰</el-radio-button>
                  <el-radio-button label="codepoint">杈撳嚭缂栫爜鐐?/el-radio-button>
                  <el-radio-button label="from_codepoint">缂栫爜鐐?鈫?鏂囨湰</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="state.unicode.mode === 'from_codepoint'" label="缂栫爜鐐瑰垪琛?>
                <el-input
                  v-model="state.unicode.codePoints"
                  type="textarea"
                  :rows="4"
                  placeholder="绀轰緥锛?041 0042 鎴?U+1F600,U+1F64C"
                />
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.unicode.content"
                type="textarea"
                :rows="8"
                placeholder="杈撳叆鏂囨湰鎴栫紪鐮佺偣"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runUnicode">鎵ц</el-button>
              </div>
              <PreviewPanel title="杈撳嚭" :content="state.unicode.result" />
            </div>
            <el-table
              v-if="state.unicode.preview?.length"
              :data="state.unicode.preview"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column prop="char" label="瀛楃" width="120" />
              <el-table-column prop="code" label="Unicode" />
              <el-table-column prop="decimal" label="鍗佽繘鍒? width="120" />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鍝堝笇璁＄畻" name="hash">
          <section class="panel">
            <header>
              <h4>MD5 / SHA 绯诲垪</h4>
              <p>鏀寔瀛楃涓蹭笌鏂囦欢涓ょ鏉ユ簮</p>
            </header>
            <el-form :model="state.hash" label-width="120px" class="form-gap">
              <el-form-item label="杈撳叆绫诲瀷">
                <el-radio-group v-model="state.hash.sourceType">
                  <el-radio-button label="text">鏂囨湰</el-radio-button>
                  <el-radio-button label="file">鏂囦欢</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="绠楁硶">
                <el-select v-model="state.hash.hashType" style="width: 200px">
                  <el-option label="MD5" value="md5" />
                  <el-option label="SHA-1" value="sha1" />
                  <el-option label="SHA-256" value="sha256" />
                  <el-option label="SHA-512" value="sha512" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.hash.sourceType === 'text'" label="鏂囨湰">
                <el-input
                  v-model="state.hash.content"
                  type="textarea"
                  :rows="4"
                  placeholder="杈撳叆瑕佽绠楃殑鏂囨湰"
                />
              </el-form-item>
              <el-form-item v-else label="鏂囦欢">
                <div class="field-row">
                  <el-input :model-value="state.hash.file?.path || ''" placeholder="灏氭湭閫夋嫨" readonly />
                  <el-button @click="selectHashFile">閫夋嫨鏂囦欢</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runHash">寮€濮嬭绠?/el-button>
              </el-form-item>
            </el-form>
            <el-input v-model="state.hash.result" readonly placeholder="鍝堝笇缁撴灉" />
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 浣跨敤鍏ㄥ眬娣辩┖鐜荤拑涓婚鏍峰紡 */

/* 鏂囨湰缃戞牸甯冨眬 */
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

.form-gap {
  margin-top: 12px;
}

.stats-panel {
  margin-top: 16px;
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}

/* 鎵归噺鏇挎崲瑙勫垯 */
.rule-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.rule-row {
  border: 1px dashed var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--ppx-glass-bg);
  transition: all var(--ppx-transition-fast);
}

.rule-row:hover {
  border-color: var(--ppx-glass-border-hover);
}

.rule-row-line {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
</style>

