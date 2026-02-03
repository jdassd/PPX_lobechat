<script setup>
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'

import ResultTable from '../shared/ResultTable.vue'

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
  activeTab: 'search',
  search: {
    directory: '',
    keyword: '',
    extensions: '',
    recursive: true,
    minSize: 0,
    maxSize: 0,
    result: []
  },
  analyze: {
    directory: '',
    stats: null
  },
  archive: {
    items: [],
    format: 'zip',
    archiveName: '',
    password: '',
    outputDir: '',
    result: ''
  },
  extract: {
    archiveFile: null,
    targetDir: '',
    password: '',
    files: []
  },
  copy: {
    sourceDir: '',
    targetDir: '',
    keyword: '',
    extensions: '',
    recursive: true,
    conflictPolicy: 'skip',
    result: null
  },
  remove: {
    directory: '',
    keyword: '',
    extensions: '',
    recursive: true,
    deletePolicy: 'recycle',
    dryRun: true,
    preview: [],
    summary: null
  },
  rename: {
    directory: '',
    extensions: '',
    recursive: false,
    rule: 'sequence',
    prefix: 'FILE_',
    start: 1,
    padding: 3,
    search: '',
    pattern: '',
    replace: '',
    template: '{date}_{name}',
    presetTemplate: '',
    conflictPolicy: 'skip',
    dryRun: true,
    result: [],
    skipped: [],
    showHelp: false
  },
  dedup: {
    directory: '',
    extensions: '',
    recursive: true,
    mode: 'content',
    result: [],
    summary: null
  },
  classify: {
    directory: '',
    targetDir: '',
    mode: 'type',
    operation: 'copy',
    recursive: true,
    conflictPolicy: 'rename',
    result: [],
    summary: null,
    categories: []
  },
  compare: {
    fileA: null,
    fileB: null,
    mode: 'auto',
    encoding: 'utf-8',
    ignoreCase: false,
    result: '',
    diffText: '',
    size: null,
    hash: null,
    encodingInfo: null
  }
})

const parseExtensions = (value) =>
  value
    .split(',')
    .map((item) => item.trim().replace('.', ''))
    .filter(Boolean)

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风涓娇鐢?)
    return false
  }
  return true
}

const selectDir = async (target) => {
  if (!ensurePyReady()) return
  const current = state[target].directory || state[target].outputDir || state[target].targetDir || ''
  const dir = await window.pywebview.api.system_pySelectDirDialog(current)
  if (dir) {
    if (state[target].directory !== undefined) state[target].directory = dir
    if (state[target].outputDir !== undefined) state[target].outputDir = dir
    if (state[target].targetDir !== undefined) state[target].targetDir = dir
  }
}

const selectClassifySource = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.classify.directory)
  if (dir) {
    state.classify.directory = dir
  }
}

const selectClassifyTarget = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.classify.targetDir || state.classify.directory)
  if (dir) {
    state.classify.targetDir = dir
  }
}

const selectCompareFile = async (target) => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['鍏ㄩ儴鏂囦欢 (*.*)'])
  if (files?.length) {
    state.compare[target] = files[0]
  }
}

const selectArchiveFile = async () => {
  if (!ensurePyReady()) return
  const res = await window.pywebview.api.system_pyCreateFileDialog(['鍘嬬缉鏂囦欢 (*.zip;*.7z)'])
  if (res?.length) {
    state.extract.archiveFile = res[0]
  }
}

const addArchiveFiles = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['鍏ㄩ儴鏂囦欢 (*.*)'])
  if (files?.length) {
    state.archive.items.push(...files.map((file) => ({ ...file, type: 'file' })))
  }
}

const addArchiveFolder = async () => {
  if (!ensurePyReady()) return
  const dir = await window.pywebview.api.system_pySelectDirDialog(state.archive.outputDir)
  if (dir) {
    state.archive.items.push({ path: dir, filename: dir.split(/[\\/]/).pop(), type: 'folder' })
  }
}

const removeArchiveItem = (index) => {
  state.archive.items.splice(index, 1)
}

const runSearch = async () => {
  if (!ensurePyReady()) return
  if (!state.search.directory) {
    ElMessage.warning('璇烽€夋嫨鐩綍')
    return
  }
  state.loading = true
  try {
    const extensions = state.search.extensions
      .split(',')
      .map((item) => item.trim().replace('.', ''))
      .filter(Boolean)
    const res = await window.pywebview.api.file_search({
      directory: state.search.directory,
      keyword: state.search.keyword,
      extensions,
      recursive: state.search.recursive,
      minSize: state.search.minSize,
      maxSize: state.search.maxSize
    })
    if (res?.code === 0) {
      state.search.result = res.items || []
      ElMessage.success(res.msg || '鎼滅储瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鎼滅储澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鎼滅储澶辫触')
  } finally {
    state.loading = false
  }
}

const runAnalyze = async () => {
  if (!ensurePyReady()) return
  if (!state.analyze.directory) {
    ElMessage.warning('璇烽€夋嫨鐩綍')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_directory_analyze({
      directory: state.analyze.directory
    })
    if (res?.code === 0) {
      state.analyze.stats = res.stats
      ElMessage.success(res.msg || '鍒嗘瀽瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鍒嗘瀽澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍒嗘瀽澶辫触')
  } finally {
    state.loading = false
  }
}

const runCompress = async () => {
  if (!ensurePyReady()) return
  if (!state.archive.items.length) {
    ElMessage.warning('璇峰厛娣诲姞鏂囦欢鎴栨枃浠跺す')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_compress({
      items: state.archive.items.map((item) => item.path || item),
      format: state.archive.format,
      archiveName: state.archive.archiveName,
      outputDir: state.archive.outputDir,
      password: state.archive.password
    })
    if (res?.code === 0) {
      state.archive.result = res.file || ''
      ElMessage.success(res.msg || '鍘嬬缉瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鍘嬬缉澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍘嬬缉澶辫触')
  } finally {
    state.loading = false
  }
}

const runExtract = async () => {
  if (!ensurePyReady()) return
  if (!state.extract.archiveFile) {
    ElMessage.warning('璇烽€夋嫨鍘嬬缉鍖?)
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_decompress({
      archiveFile: state.extract.archiveFile.path || state.extract.archiveFile,
      targetDir: state.extract.targetDir,
      password: state.extract.password
    })
    if (res?.code === 0) {
      state.extract.files = res.files || []
      state.extract.targetDir = res.outputDir || state.extract.targetDir
      ElMessage.success(res.msg || '瑙ｅ帇瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '瑙ｅ帇澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '瑙ｅ帇澶辫触')
  } finally {
    state.loading = false
  }
}

const openPath = (path) => {
  if (!ensurePyReady() || !path) return
  window.pywebview.api.system_pyOpenFile(path)
}

const chooseDir = async (current = '') => {
  if (!ensurePyReady()) return null
  return window.pywebview.api.system_pySelectDirDialog(current)
}

const selectCopySource = async () => {
  const dir = await chooseDir(state.copy.sourceDir)
  if (dir) state.copy.sourceDir = dir
}

const selectCopyTarget = async () => {
  const dir = await chooseDir(state.copy.targetDir)
  if (dir) state.copy.targetDir = dir
}

const selectRemoveDir = async () => {
  const dir = await chooseDir(state.remove.directory)
  if (dir) state.remove.directory = dir
}

const selectRenameDir = async () => {
  const dir = await chooseDir(state.rename.directory)
  if (dir) state.rename.directory = dir
}

const selectDedupDir = async () => {
  const dir = await chooseDir(state.dedup.directory)
  if (dir) state.dedup.directory = dir
}

const runCopy = async () => {
  if (!ensurePyReady()) return
  if (!state.copy.sourceDir || !state.copy.targetDir) {
    ElMessage.warning('璇烽€夋嫨婧愮洰褰曞拰鐩爣鐩綍')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_batch_copy({
      sourceDir: state.copy.sourceDir,
      targetDir: state.copy.targetDir,
      keyword: state.copy.keyword,
      extensions: parseExtensions(state.copy.extensions || ''),
      recursive: state.copy.recursive,
      conflictPolicy: state.copy.conflictPolicy
    })
    if (res?.code === 0) {
      state.copy.result = res
      ElMessage.success(res.msg || '澶嶅埗瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '澶嶅埗澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '澶嶅埗澶辫触')
  } finally {
    state.loading = false
  }
}

const runDelete = async () => {
  if (!ensurePyReady()) return
  if (!state.remove.directory) {
    ElMessage.warning('璇烽€夋嫨鐩綍')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_batch_delete({
      directory: state.remove.directory,
      keyword: state.remove.keyword,
      extensions: parseExtensions(state.remove.extensions || ''),
      recursive: state.remove.recursive,
      deletePolicy: state.remove.deletePolicy,
      dryRun: state.remove.dryRun
    })
    if (res?.code === 0) {
      state.remove.preview = res.preview || []
      state.remove.summary = res
      ElMessage.success(res.msg || (state.remove.dryRun ? '棰勮瀹屾垚' : '鍒犻櫎瀹屾垚'))
    } else {
      ElMessage.error(res?.msg || '鍒犻櫎澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍒犻櫎澶辫触')
  } finally {
    state.loading = false
  }
}

// 棰勭疆妯℃澘閫夐」
const presetTemplates = [
  { label: '鏃ユ湡 + 搴忓彿', value: '{date}_{index:3}' },
  { label: '鏃ユ湡 + 鍘熷悕', value: '{date}_{name}' },
  { label: '鍘熷悕 + 澶囦唤鍚庣紑', value: '{name}_backup' },
  { label: '绾簭鍙?, value: 'IMG_{index:4}' },
  { label: '骞存湀鏃ユ椂鍒嗙', value: '{datetime}_{index}' },
  { label: '骞?鏈?鍘熷悕', value: '{year}{month}_{name}' }
]

// 鍙橀噺璇存槑
const templateVariables = [
  { var: '{name}', desc: '鍘熸枃浠跺悕锛堜笉鍚墿灞曞悕锛? },
  { var: '{ext}', desc: '鎵╁睍鍚嶏紙濡?.jpg锛? },
  { var: '{index}', desc: '搴忓彿锛堣嚜鍔ㄨˉ闆讹級' },
  { var: '{index:4}', desc: '鎸囧畾4浣嶅簭鍙? },
  { var: '{date}', desc: '鏃ユ湡 (YYYYMMDD)' },
  { var: '{time}', desc: '鏃堕棿 (HHMMSS)' },
  { var: '{datetime}', desc: '鏃ユ湡鏃堕棿' },
  { var: '{year}', desc: '骞翠唤' },
  { var: '{month}', desc: '鏈堜唤' },
  { var: '{day}', desc: '鏃? }
]

// 姝ｅ垯琛ㄨ揪寮忕ず渚?
const regexExamples = [
  { target: '鍒犻櫎绌烘牸', pattern: '\\s+', replace: '_', desc: '绌烘牸 鈫?涓嬪垝绾? },
  { target: '鍒犻櫎鎷彿鍐呭', pattern: '\\([^)]*\\)', replace: '', desc: '绉婚櫎 (xxx)' },
  { target: '鍒犻櫎寮€澶存暟瀛?, pattern: '^\\d+[._-]?', replace: '', desc: '绉婚櫎寮€澶?01-' },
  { target: '浠呬繚鐣欏瓧姣嶆暟瀛?, pattern: '[^a-zA-Z0-9]', replace: '_', desc: '鍏朵粬瀛楃鍙樹笅鍒掔嚎' }
]

const applyPreset = (value) => {
  if (value) {
    state.rename.template = value
  }
}

const applyRegexExample = (example) => {
  state.rename.pattern = example.pattern
  state.rename.replace = example.replace
}

const buildRenameParams = () => {
  if (state.rename.rule === 'sequence') {
    return {
      prefix: state.rename.prefix,
      start: state.rename.start,
      padding: state.rename.padding
    }
  }
  if (state.rename.rule === 'timestamp') {
    return {
      start: state.rename.start,
      padding: state.rename.padding
    }
  }
  if (state.rename.rule === 'replace') {
    return {
      search: state.rename.search,
      replace: state.rename.replace
    }
  }
  if (state.rename.rule === 'template') {
    return {
      template: state.rename.template,
      start: state.rename.start,
      padding: state.rename.padding
    }
  }
  return {
    pattern: state.rename.pattern,
    replace: state.rename.replace
  }
}

const runRename = async () => {
  if (!ensurePyReady()) return
  if (!state.rename.directory) {
    ElMessage.warning('璇烽€夋嫨鐩綍')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_batch_rename({
      directory: state.rename.directory,
      extensions: parseExtensions(state.rename.extensions || ''),
      recursive: state.rename.recursive,
      rule: state.rename.rule,
      ruleParams: buildRenameParams(),
      conflictPolicy: state.rename.conflictPolicy,
      dryRun: state.rename.dryRun
    })
    if (res?.code === 0) {
      state.rename.result = res.renamed || []
      state.rename.skipped = res.skipped || []
      ElMessage.success(res.msg || (state.rename.dryRun ? '棰勮瀹屾垚' : '閲嶅懡鍚嶅畬鎴?))
    } else {
      ElMessage.error(res?.msg || '閲嶅懡鍚嶅け璐?)
    }
  } catch (error) {
    ElMessage.error(error?.message || '閲嶅懡鍚嶅け璐?)
  } finally {
    state.loading = false
  }
}

const runDedup = async () => {
  if (!ensurePyReady()) return
  if (!state.dedup.directory) {
    ElMessage.warning('璇烽€夋嫨鐩綍')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_deduplicate({
      directory: state.dedup.directory,
      mode: state.dedup.mode,
      extensions: parseExtensions(state.dedup.extensions || ''),
      recursive: state.dedup.recursive
    })
    if (res?.code === 0) {
      state.dedup.result = res.groups || []
      state.dedup.summary = res
      ElMessage.success(res.msg || '鎵弿瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鎵弿澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鎵弿澶辫触')
  } finally {
    state.loading = false
  }
}

const runClassify = async () => {
  if (!ensurePyReady()) return
  if (!state.classify.directory) {
    ElMessage.warning('璇烽€夋嫨婧愮洰褰?)
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_auto_classify({
      directory: state.classify.directory,
      targetDir: state.classify.targetDir,
      mode: state.classify.mode,
      operation: state.classify.operation,
      recursive: state.classify.recursive,
      conflictPolicy: state.classify.conflictPolicy
    })
    if (res?.code === 0) {
      state.classify.summary = res.summary
      state.classify.result = res.operations || []
      state.classify.categories = res.categories || []
      if (res.outputDir) {
        state.classify.targetDir = res.outputDir
      }
      ElMessage.success(res.msg || '鍒嗙被瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '鍒嗙被澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '鍒嗙被澶辫触')
  } finally {
    state.loading = false
  }
}

const runCompare = async () => {
  if (!ensurePyReady()) return
  if (!state.compare.fileA || !state.compare.fileB) {
    ElMessage.warning('璇峰厛閫夋嫨涓や釜鏂囦欢')
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.file_compare({
      fileA: state.compare.fileA.path,
      fileB: state.compare.fileB.path,
      mode: state.compare.mode,
      encoding: state.compare.encoding,
      ignoreCase: state.compare.ignoreCase
    })
    if (res?.code === 0) {
      state.compare.result = res.equal ? '涓や釜鏂囦欢鍐呭涓€鑷? : '妫€娴嬪埌宸紓'
      state.compare.diffText = (res.diff || []).join('\n')
      state.compare.hash = res.hash || null
      state.compare.size = res.size || null
      state.compare.encodingInfo = res.encoding || null
      ElMessage.success(res.msg || '瀵规瘮瀹屾垚')
    } else {
      ElMessage.error(res?.msg || '瀵规瘮澶辫触')
    }
  } catch (error) {
    ElMessage.error(error?.message || '瀵规瘮澶辫触')
  } finally {
    state.loading = false
  }
}
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="78%"
    append-to-body
    custom-class="file-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">FILE TOOLKIT</p>
          <h3>鏂囦欢绠＄悊宸ュ叿</h3>
          <p class="sub">鎼滅储銆佺洰褰曞垎鏋愪笌鍘嬬缉瑙ｅ帇</p>
        </div>
      </div>
    </template>
    <div class="file-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="鏂囦欢鎼滅储" name="search">
          <section class="panel">
            <header>
              <h4>蹇€熸煡鎵剧洰褰曞唴鏂囦欢</h4>
              <p>鏀寔鎵╁睍鍚嶇瓫閫夈€佸ぇ灏忚寖鍥翠笌閫掑綊鎼滅储</p>
            </header>
            <el-form :model="state.search" label-width="120px">
              <el-form-item label="鐩綍">
                <div class="field-row">
                  <el-input v-model="state.search.directory" placeholder="閫夋嫨瑕佹悳绱㈢殑鐩綍" readonly />
                  <el-button @click="selectDir('search')">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鍏抽敭瀛?>
                <el-input v-model="state.search.keyword" placeholder="鏀寔妯＄硦鍖归厤" clearable />
              </el-form-item>
              <el-form-item label="鎵╁睍鍚?>
                <el-input
                  v-model="state.search.extensions"
                  placeholder="浠ラ€楀彿鍒嗛殧锛屽锛歱df,jpg,docx"
                />
              </el-form-item>
              <el-form-item label="澶у皬 (B)">
                <div class="field-row">
                  <el-input-number v-model="state.search.minSize" :min="0" />
                  <span>~</span>
                  <el-input-number v-model="state.search.maxSize" :min="0" />
                </div>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.search.recursive">鍖呭惈瀛愮洰褰?/el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runSearch">寮€濮嬫悳绱?/el-button>
              </el-form-item>
            </el-form>
            <ResultTable
              v-if="state.search.result.length"
              title="鎼滅储缁撴灉"
              :description="`鍏?${state.search.result.length} 鏉"
              :items="state.search.result"
              :columns="[
                { label: '鏂囦欢鍚?, prop: 'name', width: 200 },
                { label: '璺緞', prop: 'path' },
                { label: '澶у皬', prop: 'sizeText', width: 120 }
              ]"
            >
              <template #actions>
                <el-button text type="primary" @click="openPath(state.search.directory)">
                  鎵撳紑鐩綍
                </el-button>
              </template>
            </ResultTable>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鑷姩鍒嗙被" name="classify">
          <section class="panel">
            <header>
              <h4>鎸夌被鍨?/ 澶у皬 / 鏃ユ湡鏁寸悊</h4>
              <p>灏嗙洰褰曚腑鐨勬枃浠舵壒閲忓鍒?绉诲姩鍒板垎绫诲瓙鐩綍</p>
            </header>
            <el-form :model="state.classify" label-width="130px" class="form-gap">
              <el-form-item label="婧愮洰褰?>
                <div class="field-row">
                  <el-input v-model="state.classify.directory" placeholder="閫夋嫨寰呮暣鐞嗙洰褰? readonly />
                  <el-button @click="selectClassifySource">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鐩爣鐩綍">
                <div class="field-row">
                  <el-input
                    v-model="state.classify.targetDir"
                    placeholder="鐣欑┖鍒欏湪婧愮洰褰曞垱寤?_classified"
                    readonly
                  />
                  <el-button @click="selectClassifyTarget">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鍒嗙被妯″紡">
                <el-radio-group v-model="state.classify.mode">
                  <el-radio-button label="type">鎸夋枃浠剁被鍨?/el-radio-button>
                  <el-radio-button label="size">鎸夊ぇ灏忓尯闂?/el-radio-button>
                  <el-radio-button label="date">鎸夋棩鏈燂紙骞存湀锛?/el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="鎿嶄綔鏂瑰紡">
                <el-radio-group v-model="state.classify.operation">
                  <el-radio-button label="copy">澶嶅埗</el-radio-button>
                  <el-radio-button label="move">绉诲姩</el-radio-button>
                </el-radio-group>
                <el-checkbox v-model="state.classify.recursive" style="margin-left: 12px">
                  鍖呭惈瀛愮洰褰?
                </el-checkbox>
              </el-form-item>
              <el-form-item label="鍐茬獊绛栫暐">
                <el-select v-model="state.classify.conflictPolicy" style="width: 200px">
                  <el-option label="閲嶅懡鍚? value="rename" />
                  <el-option label="瑕嗙洊" value="overwrite" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runClassify">鎵ц鍒嗙被</el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.classify.summary" class="stats-panel">
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item label="鍖归厤鏂囦欢">
                  {{ state.classify.summary.matched }}
                </el-descriptions-item>
                <el-descriptions-item label="宸插鐞?>
                  {{ state.classify.summary.processed }}
                </el-descriptions-item>
                <el-descriptions-item label="鎬诲ぇ灏?>
                  {{ state.classify.summary.totalSize }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
            <el-table
              v-if="state.classify.categories.length"
              :data="state.classify.categories"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column prop="label" label="鍒嗙被" />
              <el-table-column prop="count" label="鏁伴噺" width="140" />
            </el-table>
            <el-table
              v-if="state.classify.result.length"
              :data="state.classify.result.slice(0, 60)"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column prop="category" label="鍒嗙被" width="140" />
              <el-table-column prop="from" label="婧愭枃浠? show-overflow-tooltip />
              <el-table-column prop="to" label="鐩爣鍦板潃" show-overflow-tooltip />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鎵归噺澶嶅埗" name="copy">
          <section class="panel">
            <header>
              <h4>鎸夎鍒欏鍒舵枃浠?/h4>
              <p>鎸夊叧閿瓧 / 鎵╁睍鍚嶇瓫閫夛紝鑷姩澶嶅埗鍒扮洰鏍囩洰褰?/p>
            </header>
            <el-form :model="state.copy" label-width="120px">
              <el-form-item label="婧愮洰褰?>
                <div class="field-row">
                  <el-input v-model="state.copy.sourceDir" placeholder="閫夋嫨婧愮洰褰? readonly />
                  <el-button @click="selectCopySource">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鐩爣鐩綍">
                <div class="field-row">
                  <el-input v-model="state.copy.targetDir" placeholder="閫夋嫨鐩爣鐩綍" readonly />
                  <el-button @click="selectCopyTarget">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鍏抽敭瀛?>
                <el-input v-model="state.copy.keyword" placeholder="鍙€? />
              </el-form-item>
              <el-form-item label="鎵╁睍鍚?>
                <el-input v-model="state.copy.extensions" placeholder="渚嬪锛歱df,jpg" />
              </el-form-item>
              <el-form-item label="閫夐」">
                <el-checkbox v-model="state.copy.recursive">鍖呭惈瀛愮洰褰?/el-checkbox>
                <el-select v-model="state.copy.conflictPolicy" style="width: 200px">
                  <el-option label="鍐茬獊璺宠繃" value="skip" />
                  <el-option label="瑕嗙洊鍚屽悕鏂囦欢" value="overwrite" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCopy">寮€濮嬪鍒?/el-button>
              </el-form-item>
            </el-form>
            <el-descriptions
              v-if="state.copy.result"
              :column="3"
              border
              size="small"
            >
              <el-descriptions-item label="宸插鍒?>{{ state.copy.result.copied }}</el-descriptions-item>
              <el-descriptions-item label="璺宠繃">{{ state.copy.result.skipped }}</el-descriptions-item>
              <el-descriptions-item label="鎬诲ぇ灏?>{{ state.copy.result.sizeText }}</el-descriptions-item>
            </el-descriptions>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鎵归噺鍒犻櫎" name="delete">
          <section class="panel">
            <header>
              <h4>鎸夋潯浠跺垹闄ゆ枃浠?/h4>
              <p>鏀寔鍏堥瑙堬紝鍐嶆墽琛屾案涔呭垹闄ゆ垨绉诲姩鍒板洖鏀剁珯</p>
            </header>
            <el-form :model="state.remove" label-width="120px">
              <el-form-item label="鐩綍">
                <div class="field-row">
                  <el-input v-model="state.remove.directory" placeholder="閫夋嫨鐩綍" readonly />
                  <el-button @click="selectRemoveDir">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鍏抽敭瀛?>
                <el-input v-model="state.remove.keyword" placeholder="鍙€? />
              </el-form-item>
              <el-form-item label="鎵╁睍鍚?>
                <el-input v-model="state.remove.extensions" placeholder="濡傦細log,tmp" />
              </el-form-item>
              <el-form-item label="閫夐」">
                <el-checkbox v-model="state.remove.recursive">鍖呭惈瀛愮洰褰?/el-checkbox>
                <el-radio-group v-model="state.remove.deletePolicy">
                  <el-radio-button label="recycle">绉诲姩鍒板洖鏀剁珯</el-radio-button>
                  <el-radio-button label="permanent">姘镐箙鍒犻櫎</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="棰勮妯″紡">
                <el-switch v-model="state.remove.dryRun" active-text="浠呴瑙? inactive-text="鐩存帴鍒犻櫎" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runDelete">
                  {{ state.remove.dryRun ? '棰勮鍒犻櫎鍒楄〃' : '绔嬪嵆鍒犻櫎' }}
                </el-button>
              </el-form-item>
            </el-form>
            <el-table
              v-if="state.remove.preview.length"
              :data="state.remove.preview"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-table-column label="寰呭垹闄ゆ枃浠?>
                <template #default="scope">
                  <a class="link" @click.prevent="openPath(scope.row)">{{ scope.row }}</a>
                </template>
              </el-table-column>
            </el-table>
            <el-descriptions
              v-if="state.remove.summary && !state.remove.dryRun"
              :column="2"
              border
              size="small"
              style="margin-top: 16px"
            >
              <el-descriptions-item label="鍒犻櫎鏁伴噺">{{ state.remove.summary.deleted }}</el-descriptions-item>
              <el-descriptions-item label="閲婃斁绌洪棿">{{ state.remove.summary.sizeText }}</el-descriptions-item>
            </el-descriptions>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鎵归噺鏀瑰悕" name="rename">
          <section class="panel">
            <header>
              <h4>閲嶅懡鍚嶈鍒?/h4>
              <p>鏀寔搴忓彿銆佹椂闂存埑銆佹浛鎹€佹鍒欒〃杈惧紡鎴栬嚜瀹氫箟妯℃澘</p>
            </header>
            <el-form :model="state.rename" label-width="120px">
              <el-form-item label="鐩綍">
                <div class="field-row">
                  <el-input v-model="state.rename.directory" placeholder="閫夋嫨鐩綍" readonly />
                  <el-button @click="selectRenameDir">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鎵╁睍鍚?>
                <el-input v-model="state.rename.extensions" placeholder="鍙€夛紝濡傦細jpg,png" />
              </el-form-item>
              <el-form-item label="閫夐」">
                <el-checkbox v-model="state.rename.recursive">鍖呭惈瀛愮洰褰?/el-checkbox>
                <el-switch v-model="state.rename.dryRun" active-text="浠呴瑙? inactive-text="绔嬪嵆鏀瑰悕" />
              </el-form-item>
              <el-form-item label="鍐茬獊绛栫暐">
                <el-select v-model="state.rename.conflictPolicy" style="width: 200px">
                  <el-option label="璺宠繃宸叉湁鏂囦欢" value="skip" />
                  <el-option label="鐩存帴瑕嗙洊" value="overwrite" />
                </el-select>
              </el-form-item>
              <el-form-item label="瑙勫垯">
                <el-radio-group v-model="state.rename.rule">
                  <el-radio-button label="sequence">搴忓彿</el-radio-button>
                  <el-radio-button label="timestamp">鏃堕棿鎴?/el-radio-button>
                  <el-radio-button label="replace">鏇挎崲</el-radio-button>
                  <el-radio-button label="template">妯℃澘</el-radio-button>
                  <el-radio-button label="regex">姝ｅ垯</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <!-- 搴忓彿妯″紡 -->
              <div v-if="state.rename.rule === 'sequence'" class="field-row">
                <el-form-item label="鍓嶇紑">
                  <el-input v-model="state.rename.prefix" placeholder="濡?IMG_" />
                </el-form-item>
                <el-form-item label="璧峰鍊?>
                  <el-input-number v-model="state.rename.start" :min="1" />
                </el-form-item>
                <el-form-item label="浣嶆暟">
                  <el-input-number v-model="state.rename.padding" :min="1" :max="6" />
                </el-form-item>
              </div>

              <!-- 鏃堕棿鎴虫ā寮?-->
              <div v-else-if="state.rename.rule === 'timestamp'" class="field-row">
                <el-form-item label="璧峰鍊?>
                  <el-input-number v-model="state.rename.start" :min="1" />
                </el-form-item>
                <el-form-item label="浣嶆暟">
                  <el-input-number v-model="state.rename.padding" :min="1" :max="6" />
                </el-form-item>
              </div>

              <!-- 妯℃澘妯″紡 -->
              <div v-else-if="state.rename.rule === 'template'" class="rename-template-section">
                <el-form-item label="棰勭疆妯℃澘">
                  <el-select
                    v-model="state.rename.presetTemplate"
                    placeholder="閫夋嫨甯哥敤妯℃澘"
                    style="width: 220px"
                    clearable
                    @change="applyPreset"
                  >
                    <el-option
                      v-for="item in presetTemplates"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="鑷畾涔夋ā鏉?>
                  <div class="field-row">
                    <el-input
                      v-model="state.rename.template"
                      placeholder="濡?{date}_{name}"
                      style="flex: 1"
                    />
                    <el-popover placement="right" :width="320" trigger="hover">
                      <template #reference>
                        <el-button type="info" text>鍙橀噺璇存槑</el-button>
                      </template>
                      <div class="var-help">
                        <p class="var-help-title">鍙敤鍙橀噺锛?/p>
                        <el-table :data="templateVariables" size="small" border>
                          <el-table-column prop="var" label="鍙橀噺" width="100" />
                          <el-table-column prop="desc" label="璇存槑" />
                        </el-table>
                        <p class="var-help-example">绀轰緥锛歿date}_{name} 鈫?20260104_photo.jpg</p>
                      </div>
                    </el-popover>
                  </div>
                </el-form-item>
                <el-form-item label="璧峰搴忓彿">
                  <el-input-number v-model="state.rename.start" :min="1" />
                </el-form-item>
              </div>

              <!-- 姝ｅ垯妯″紡 -->
              <div v-else-if="state.rename.rule === 'regex'" class="rename-regex-section">
                <el-form-item label="姝ｅ垯琛ㄨ揪寮?>
                  <div class="field-row">
                    <el-input
                      v-model="state.rename.pattern"
                      placeholder="濡?\s+ 鍖归厤绌烘牸"
                      style="flex: 1"
                    />
                    <el-popover placement="right" :width="400" trigger="hover">
                      <template #reference>
                        <el-button type="info" text>甯哥敤绀轰緥</el-button>
                      </template>
                      <div class="regex-help">
                        <p class="regex-help-title">甯哥敤姝ｅ垯琛ㄨ揪寮忕ず渚嬶紙鐐瑰嚮鍙簲鐢級锛?/p>
                        <el-table :data="regexExamples" size="small" border>
                          <el-table-column prop="target" label="鐩爣" width="100" />
                          <el-table-column prop="pattern" label="鍖归厤" width="120" />
                          <el-table-column prop="desc" label="鏁堟灉" />
                          <el-table-column label="鎿嶄綔" width="70">
                            <template #default="scope">
                              <el-button size="small" text type="primary" @click="applyRegexExample(scope.row)">
                                搴旂敤
                              </el-button>
                            </template>
                          </el-table-column>
                        </el-table>
                      </div>
                    </el-popover>
                  </div>
                </el-form-item>
                <el-form-item label="鏇挎崲涓?>
                  <el-input v-model="state.rename.replace" placeholder="鏇挎崲鍐呭锛岀暀绌鸿〃绀哄垹闄ゅ尮閰嶉儴鍒? />
                </el-form-item>
              </div>

              <!-- 绠€鍗曟浛鎹㈡ā寮?-->
              <div v-else-if="state.rename.rule === 'replace'" class="field-row">
                <el-form-item label="鏌ユ壘鏂囨湰">
                  <el-input v-model="state.rename.search" placeholder="瑕佹浛鎹㈢殑鏂囨湰" />
                </el-form-item>
                <el-form-item label="鏇挎崲涓?>
                  <el-input v-model="state.rename.replace" placeholder="鏇挎崲鍐呭" />
                </el-form-item>
              </div>

              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runRename">
                  {{ state.rename.dryRun ? '棰勮缁撴灉' : '鎵ц鏀瑰悕' }}
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 浣跨敤璇存槑 -->
            <el-collapse v-model="state.rename.showHelp" class="rename-help-collapse">
              <el-collapse-item title="馃摉 浣跨敤璇存槑" name="help">
                <div class="rename-help-content">
                  <h5>瑙勫垯璇存槑</h5>
                  <ul>
                    <li><strong>搴忓彿</strong>锛氭寜搴忓彿閲嶅懡鍚嶏紝濡?FILE_001銆丗ILE_002</li>
                    <li><strong>鏃堕棿鎴?/strong>锛氫娇鐢ㄥ綋鍓嶆椂闂村懡鍚?/li>
                    <li><strong>鏇挎崲</strong>锛氱畝鍗曟枃鏈浛鎹紝鏃犻渶姝ｅ垯鐭ヨ瘑</li>
                    <li><strong>妯℃澘</strong>锛氫娇鐢ㄥ彉閲忕粍鍚堣嚜瀹氫箟鏍煎紡锛屾帹鑽愭柊鎵嬩娇鐢?/li>
                    <li><strong>姝ｅ垯</strong>锛氶珮绾фā寮忥紝鏀寔姝ｅ垯琛ㄨ揪寮忓尮閰?/li>
                  </ul>
                  <h5>鎿嶄綔寤鸿</h5>
                  <ul>
                    <li>棣栨鎿嶄綔璇峰厛寮€鍚€屼粎棰勮銆嶆ā寮忥紝纭鏃犺鍚庡啀鎵ц</li>
                    <li>涓嶇啛鎮夋鍒欙紵璇曡瘯銆屾ā鏉裤€嶆ā寮忥紝閫夋嫨棰勭疆妯℃澘鎴栦娇鐢ㄥ彉閲?/li>
                  </ul>
                </div>
              </el-collapse-item>
            </el-collapse>

            <el-table
              v-if="state.rename.result.length"
              :data="state.rename.result"
              border
              size="small"
              style="margin-top: 12px"
            >
              <el-table-column label="鍘熸枃浠? prop="from" show-overflow-tooltip />
              <el-table-column label="鏂版枃浠? prop="to" show-overflow-tooltip />
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鏂囦欢鍘婚噸" name="dedup">
          <section class="panel">
            <header>
              <h4>閲嶅鏂囦欢妫€娴?/h4>
              <p>鎸夊唴瀹规垨鏂囦欢鍚嶆壂鎻忛噸澶嶉」锛屽睍绀哄彲閲婃斁绌洪棿</p>
            </header>
            <el-form :model="state.dedup" label-width="120px">
              <el-form-item label="鐩綍">
                <div class="field-row">
                  <el-input v-model="state.dedup.directory" placeholder="閫夋嫨鐩綍" readonly />
                  <el-button @click="selectDedupDir">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鎵╁睍鍚?>
                <el-input v-model="state.dedup.extensions" placeholder="鍙€夛紝濡傦細zip,iso" />
              </el-form-item>
              <el-form-item label="妯″紡">
                <el-radio-group v-model="state.dedup.mode">
                  <el-radio-button label="content">鎸夊唴瀹?(鍝堝笇)</el-radio-button>
                  <el-radio-button label="name">鎸夋枃浠跺悕</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item>
                <el-checkbox v-model="state.dedup.recursive">鍖呭惈瀛愮洰褰?/el-checkbox>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runDedup">寮€濮嬫壂鎻?/el-button>
              </el-form-item>
            </el-form>
            <el-descriptions
              v-if="state.dedup.summary"
              :column="2"
              border
              size="small"
            >
              <el-descriptions-item label="閲嶅鍒嗙粍">{{ state.dedup.summary.totalGroups }}</el-descriptions-item>
              <el-descriptions-item label="鍙噴鏀剧┖闂?>{{ state.dedup.summary.spaceSaved }}</el-descriptions-item>
            </el-descriptions>
            <el-table
              v-if="state.dedup.result.length"
              :data="state.dedup.result"
              border
              size="small"
              style="margin-top: 12px"
            >
              <el-table-column label="閲嶅鏂囦欢">
                <template #default="scope">
                  <ul class="dedup-list">
                    <li v-for="file in scope.row.files" :key="file">
                      <a class="link" @click.prevent="openPath(file)">{{ file }}</a>
                    </li>
                  </ul>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鐩綍鍒嗘瀽" name="analyze">
          <section class="panel">
            <header>
              <h4>缁熻鐩綍缁撴瀯</h4>
              <p>灞曠ず鏂囦欢鏁伴噺銆佺┖闂村崰鐢ㄤ笌鎵╁睍鍚?Top N</p>
            </header>
            <el-form :model="state.analyze" label-width="120px">
              <el-form-item label="鐩綍">
                <div class="field-row">
                  <el-input v-model="state.analyze.directory" placeholder="閫夋嫨鐩綍" readonly />
                  <el-button @click="selectDir('analyze')">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runAnalyze">寮€濮嬪垎鏋?/el-button>
              </el-form-item>
            </el-form>
            <div v-if="state.analyze.stats" class="stats-panel">
              <el-descriptions :column="3" border size="small">
                <el-descriptions-item label="鎬诲ぇ灏?>
                  {{ state.analyze.stats.totalSize }}
                </el-descriptions-item>
                <el-descriptions-item label="鏂囦欢鏁?>
                  {{ state.analyze.stats.fileCount }}
                </el-descriptions-item>
                <el-descriptions-item label="瀛愮洰褰曟暟">
                  {{ state.analyze.stats.dirCount }}
                </el-descriptions-item>
              </el-descriptions>
              <div class="stat-cols">
                <div>
                  <h5>鐑棬鎵╁睍鍚?/h5>
                  <ul>
                    <li v-for="item in state.analyze.stats.topExtensions" :key="item.ext">
                      {{ item.ext }} 路 {{ item.count }}
                    </li>
                  </ul>
                </div>
                <div>
                  <h5>鏈€澶ф枃浠?/h5>
                  <ul>
                    <li v-for="item in state.analyze.stats.largestFiles" :key="item.path">
                      <span>{{ item.name }}</span>
                      <span>{{ item.size }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="鏂囦欢瀵规瘮" name="compare">
          <section class="panel">
            <header>
              <h4>鏂囨湰 / 浜岃繘鍒跺姣?/h4>
              <p>蹇€熺‘璁や袱涓枃浠舵槸鍚︿竴鑷达紝骞剁粰鍑哄樊寮?diff</p>
            </header>
            <el-form :model="state.compare" label-width="120px" class="form-gap">
              <el-form-item label="鏂囦欢 A">
                <div class="field-row">
                  <el-input :model-value="state.compare.fileA?.path || ''" placeholder="灏氭湭閫夋嫨" readonly />
                  <el-button @click="selectCompareFile('fileA')">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="鏂囦欢 B">
                <div class="field-row">
                  <el-input :model-value="state.compare.fileB?.path || ''" placeholder="灏氭湭閫夋嫨" readonly />
                  <el-button @click="selectCompareFile('fileB')">閫夋嫨</el-button>
                </div>
              </el-form-item>
              <el-form-item label="妯″紡">
                <el-radio-group v-model="state.compare.mode">
                  <el-radio-button label="auto">鑷姩</el-radio-button>
                  <el-radio-button label="text">鏂囨湰</el-radio-button>
                  <el-radio-button label="binary">浜岃繘鍒?/el-radio-button>
                </el-radio-group>
                <el-checkbox v-model="state.compare.ignoreCase" style="margin-left: 12px">蹇界暐澶у皬鍐?/el-checkbox>
              </el-form-item>
              <el-form-item v-if="state.compare.mode !== 'binary'" label="棣栭€夌紪鐮?>
                <el-input v-model="state.compare.encoding" placeholder="榛樿 UTF-8" style="width: 220px" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runCompare">鎵ц瀵规瘮</el-button>
              </el-form-item>
            </el-form>
            <el-alert
              v-if="state.compare.result"
              :type="state.compare.diffText ? 'warning' : 'success'"
              :closable="false"
              show-icon
            >
              <template #title>{{ state.compare.result }}</template>
            </el-alert>
            <el-descriptions
              v-if="state.compare.hash || state.compare.size"
              :column="2"
              border
              size="small"
              style="margin-top: 12px"
            >
              <el-descriptions-item label="鏂囦欢 A 澶у皬">
                {{ state.compare.size?.leftText || state.compare.size?.left || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="鏂囦欢 B 澶у皬">
                {{ state.compare.size?.rightText || state.compare.size?.right || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="鏂囦欢 A 鍝堝笇">
                {{ state.compare.hash?.left || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="鏂囦欢 B 鍝堝笇">
                {{ state.compare.hash?.right || '-' }}
              </el-descriptions-item>
            </el-descriptions>
            <el-input
              v-if="state.compare.diffText"
              v-model="state.compare.diffText"
              type="textarea"
              :rows="12"
              readonly
              style="margin-top: 16px"
            />
          </section>
        </el-tab-pane>

        <el-tab-pane label="鍘嬬缉 / 瑙ｅ帇" name="archive">
          <section class="panel">
            <header>
              <h4>鎵归噺鍘嬬缉 ZIP/7Z锛屾垨瑙ｅ帇鏂囦欢</h4>
            </header>
            <div class="archive-grid">
              <div class="archive-card">
                <h5>鍘嬬缉鎵撳寘</h5>
                <div class="field-row">
                  <el-button size="small" @click="addArchiveFiles">娣诲姞鏂囦欢</el-button>
                  <el-button size="small" @click="addArchiveFolder">娣诲姞鏂囦欢澶?/el-button>
                </div>
                <el-table
                  v-if="state.archive.items.length"
                  :data="state.archive.items"
                  size="small"
                  border
                  style="margin-top: 10px"
                >
                  <el-table-column type="index" width="50" label="#" />
                  <el-table-column prop="filename" label="鍚嶇О" />
                  <el-table-column label="绫诲瀷" width="100">
                    <template #default="scope">
                      <el-tag size="small" effect="plain">{{ scope.row.type === 'folder' ? '鏂囦欢澶? : '鏂囦欢' }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="鎿嶄綔" width="80">
                    <template #default="scope">
                      <el-button link type="danger" @click="removeArchiveItem(scope.$index)">绉婚櫎</el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty v-else description="灏氭湭娣诲姞" />
                <el-form :model="state.archive" label-width="100px" style="margin-top: 12px">
                  <el-form-item label="鏍煎紡">
                    <el-radio-group v-model="state.archive.format">
                      <el-radio-button label="zip">ZIP</el-radio-button>
                      <el-radio-button label="7z">7Z</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                  <el-form-item label="鏂囦欢鍚?>
                    <el-input v-model="state.archive.archiveName" placeholder="鍙€夛紝濡?work_backup" />
                  </el-form-item>
                  <el-form-item label="杈撳嚭鐩綍">
                    <div class="field-row">
                      <el-input v-model="state.archive.outputDir" placeholder="鐣欑┖浣跨敤婧愮洰褰? readonly />
                      <el-button @click="selectDir('archive')">鐩綍</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item label="瀵嗙爜" v-if="state.archive.format === '7z'">
                    <el-input v-model="state.archive.password" placeholder="鍙€? />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="state.loading" @click="runCompress">寮€濮嬪帇缂?/el-button>
                  </el-form-item>
                </el-form>
                <el-alert
                  v-if="state.archive.result"
                  type="success"
                  :closable="false"
                  show-icon
                >
                  <template #title>
                    宸茬敓鎴愶細
                    <a class="link" @click.prevent="openPath(state.archive.result)">{{ state.archive.result }}</a>
                  </template>
                </el-alert>
              </div>

              <div class="archive-card">
                <h5>瑙ｅ帇缂?/h5>
                <el-form :model="state.extract" label-width="100px">
                  <el-form-item label="鍘嬬缉鍖?>
                    <div class="field-row">
                      <el-input :model-value="state.extract.archiveFile?.path || ''" placeholder="閫夋嫨 ZIP/7Z" readonly />
                      <el-button @click="selectArchiveFile">閫夋嫨</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item label="杈撳嚭鐩綍">
                    <div class="field-row">
                      <el-input v-model="state.extract.targetDir" placeholder="鑷姩鍒涘缓" readonly />
                      <el-button @click="selectDir('extract')">鐩綍</el-button>
                    </div>
                  </el-form-item>
                  <el-form-item label="瀵嗙爜">
                    <el-input v-model="state.extract.password" placeholder="濡傛枃浠跺甫瀵嗙爜" />
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" :loading="state.loading" @click="runExtract">寮€濮嬭В鍘?/el-button>
                  </el-form-item>
                </el-form>
                <ResultTable
                  v-if="state.extract.files.length"
                  title="閮ㄥ垎瑙ｅ帇鏂囦欢"
                  :items="state.extract.files.map((path) => ({ path }))"
                  :columns="[{ label: '鏂囦欢璺緞', prop: 'path' }]"
                  :max-height="200"
                />
              </div>
            </div>
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
/* 浣跨敤鍏ㄥ眬娣辩┖鐜荤拑涓婚鏍峰紡 */

.stats-panel {
  margin-top: 18px;
}

.stat-cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 16px;
}

.stat-cols h5 {
  margin: 0 0 8px;
  color: var(--ppx-text-primary);
}

.stat-cols ul {
  margin: 0;
  padding-left: 16px;
  color: var(--ppx-text-secondary);
}

/* 鍘嬬缉/瑙ｅ帇缃戞牸 */
.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.archive-card {
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  padding: 16px;
  background: var(--ppx-glass-bg);
  transition: all var(--ppx-transition-fast);
}

.archive-card:hover {
  border-color: var(--ppx-glass-border-hover);
}

.archive-card h5 {
  margin: 0 0 12px;
  color: var(--ppx-text-primary);
}

.link {
  color: var(--ppx-neon-blue);
  cursor: pointer;
}

.dedup-list {
  list-style: none;
  padding-left: 0;
  margin: 0;
}

.dedup-list li {
  margin-bottom: 4px;
}

.form-gap {
  margin-top: 12px;
}

/* 閲嶅懡鍚嶆ā鍧楁牱寮?*/
.rename-template-section,
.rename-regex-section {
  margin-bottom: 12px;
}

.var-help,
.regex-help {
  font-size: 13px;
}

.var-help-title,
.regex-help-title {
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--ppx-text-primary);
}

.var-help-example {
  margin: 8px 0 0;
  padding: 6px 10px;
  background: var(--ppx-glass-bg);
  border-radius: var(--ppx-radius-sm);
  color: var(--ppx-text-secondary);
  font-size: 12px;
}

.rename-help-collapse {
  margin-top: 16px;
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-md);
  overflow: hidden;
}

.rename-help-content {
  font-size: 13px;
  color: var(--ppx-text-secondary);
}

.rename-help-content h5 {
  font-size: 14px;
  margin: 0 0 8px;
  color: var(--ppx-text-primary);
}

.rename-help-content h5:not(:first-child) {
  margin-top: 16px;
}

.rename-help-content ul {
  margin: 0;
  padding-left: 18px;
}

.rename-help-content li {
  margin-bottom: 4px;
}

.rename-help-content strong {
  color: var(--ppx-neon-blue);
}
</style>

