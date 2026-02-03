<script setup>
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'

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

const examples = [
  { label: '1409.50', note: '涓棿鍚?0' },
  { label: '6007.14', note: '杩炵画 0' },
  { label: '1680.32', note: '瑙掍綅鏈夊€? },
  { label: '16409.02', note: '瑙掍綅涓?0' },
  { label: '107000.53', note: '涓囦綅涓?0' }
]

const state = reactive({
  loading: false,
  amount: '',
  result: '',
  normalized: ''
})

const ensurePyReady = () => {
  if (!window.pywebview?.api) {
    ElMessage.warning('璇ュ姛鑳介渶鍦ㄦ闈㈠鎴风涓娇鐢?)
    return false
  }
  return true
}

const runConvert = async () => {
  if (!ensurePyReady()) return
  if (!state.amount.trim()) {
    ElMessage.warning('璇疯緭鍏ラ噾棰?)
    return
  }
  state.loading = true
  try {
    const res = await window.pywebview.api.finance_rmb_uppercase({
      amount: state.amount
    })
    if (res?.code === 0) {
      state.result = res.result || ''
      state.normalized = res.amount || ''
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

const applyExample = (value) => {
  state.amount = value
  runConvert()
}

const resetAll = () => {
  state.amount = ''
  state.result = ''
  state.normalized = ''
}
</script>

<template>
  <el-drawer
    v-model="visibleProxy"
    size="60%"
    append-to-body
    custom-class="finance-tool-drawer"
  >
    <template #header>
      <div class="drawer-head">
        <div>
          <p class="eyebrow">FINANCE TOOL</p>
          <h3>浜烘皯甯佸ぇ鍐?/h3>
          <p class="sub">蹇€熺敓鎴愯鑼冪殑绁ㄦ嵁閲戦澶у啓鏍煎紡</p>
        </div>
      </div>
    </template>
    <div class="finance-tool">
      <section class="panel">
        <header>
          <h4>閲戦杈撳叆</h4>
          <p>鏀寔 锟ャ€丷MB銆丆NY銆佸崈鍒嗕綅鏍煎紡锛岃嚜鍔ㄤ繚鐣欎袱浣嶅皬鏁?/p>
        </header>
        <el-form label-width="120px">
          <el-form-item label="灏忓啓閲戦">
            <el-input
              v-model="state.amount"
              placeholder="濡?1680.32 鎴?锟?,680.32"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <div class="field-row field-wrap">
              <el-button type="primary" :loading="state.loading" @click="runConvert">鐢熸垚澶у啓</el-button>
              <el-button @click="resetAll">娓呯┖</el-button>
            </div>
          </el-form-item>
        </el-form>

        <div class="example-strip">
          <span class="example-title">甯歌绀轰緥</span>
          <div class="example-tags">
            <el-tag
              v-for="item in examples"
              :key="item.label"
              effect="plain"
              type="info"
              @click="applyExample(item.label)"
            >
              {{ item.label }} 路 {{ item.note }}
            </el-tag>
          </div>
        </div>
      </section>

      <section class="panel">
        <header>
          <h4>杞崲缁撴灉</h4>
          <p>榛樿琛ュ叏銆屼汉姘戝竵銆嶅墠缂€锛岀鍚堥摱琛岀エ鎹鑼?/p>
        </header>
        <el-form label-width="120px">
          <el-form-item label="鏍囧噯閲戦">
            <el-input v-model="state.normalized" readonly placeholder="鑷姩瑙勮寖鍖栧悗閲戦" />
          </el-form-item>
        </el-form>
        <el-input
          v-model="state.result"
          type="textarea"
          :rows="4"
          readonly
          placeholder="鐢熸垚缁撴灉灏嗗湪姝ゆ樉绀?
        />
      </section>

      <section class="panel">
        <header>
          <h4>瑙勮寖瑕佺偣</h4>
          <p>绁ㄦ嵁濉啓鏃跺父瑙佽姹傦紝閬垮厤鍑虹幇绌虹櫧鎴栬鍐?/p>
        </header>
        <ul class="rule-list">
          <li>閲戦鍒板厓涓烘锛屽厓鍚庨渶鍐欌€滄暣鈥?鎴栤€滄鈥?锛岃浣嶆湁鍊煎彲涓嶅啓銆?/li>
          <li>閲戦鍓嶅姞鈥滀汉姘戝竵鈥濓紝澶у啓閲戦闇€绱ф尐濉啓涓嶅緱鐣欑┖銆?/li>
          <li>瑙掍綅涓?0 涓斿垎浣嶆湁鍊兼椂锛屽厓鍚庨渶琛ュ啓鈥滈浂鈥濄€?/li>
          <li>杩炵画澶氫釜 0 浠呭啓涓€涓€滈浂鈥濓紝閬垮厤閲嶅鍫嗗彔銆?/li>
        </ul>
      </section>
    </div>
  </el-drawer>
</template>

<style scoped>
.example-strip {
  margin-top: 12px;
}

.example-title {
  display: inline-block;
  font-size: 12px;
  color: var(--ppx-text-muted);
  margin-bottom: 8px;
}

.example-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.example-tags .el-tag {
  cursor: pointer;
  transition: all var(--ppx-transition-fast);
}

.example-tags .el-tag:hover {
  border-color: rgba(14, 165, 164, 0.4);
  color: var(--ppx-neon-blue);
}

.rule-list {
  margin: 0;
  padding-left: 18px;
  color: var(--ppx-text-secondary);
  line-height: 1.7;
}
</style>

