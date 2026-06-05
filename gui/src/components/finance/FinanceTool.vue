<script setup>
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { callApi as pyCall, hasPyApi } from '@/utils/pyapi'
import { toChineseAmount } from '@/utils/amount'

const examples = [
  { label: '1409.50', note: '中间含 0' },
  { label: '6007.14', note: '连续 0' },
  { label: '1680.32', note: '角位有值' },
  { label: '16409.02', note: '角位为 0' },
  { label: '107000.53', note: '万位为 0' }
]

const state = reactive({
  loading: false,
  amount: '',
  result: '',
  normalized: ''
})

const runConvert = async () => {
  if (!state.amount.trim()) {
    ElMessage.warning('请输入金额')
    return
  }
  // 桌面端优先走后端（支持 ￥/RMB/千分位规范化）；非桌面环境用本地 amount.js 兜底，便于浏览器预览。
  if (!hasPyApi()) {
    const num = String(state.amount).replace(/[^\d.-]/g, '')
    state.normalized = num
    state.result = toChineseAmount(num)
    if (!state.result) ElMessage.warning('无法识别金额')
    return
  }
  state.loading = true
  try {
    const {
      ok,
      data: res,
      message
    } = await pyCall('finance_rmb_uppercase', {
      amount: state.amount
    })
    if (ok) {
      state.result = res.result || ''
      state.normalized = res.amount || ''
      ElMessage.success(message || '转换完成')
    } else {
      ElMessage.error(message || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
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
  <div class="tool-scroll">
    <div class="tool-narrow">
      <section class="panel">
        <header>
          <h4>金额输入</h4>
          <p>支持 ￥、RMB、CNY、千分位格式，自动保留两位小数</p>
        </header>
        <el-form label-width="120px">
          <el-form-item label="小写金额">
            <el-input v-model="state.amount" placeholder="如 1680.32 或 ￥1,680.32" clearable />
          </el-form-item>
          <el-form-item>
            <div class="field-row field-wrap">
              <el-button type="primary" :loading="state.loading" @click="runConvert">生成大写</el-button>
              <el-button @click="resetAll">清空</el-button>
            </div>
          </el-form-item>
        </el-form>

        <div class="example-strip">
          <span class="example-title">常见示例</span>
          <div class="example-tags">
            <el-tag v-for="item in examples" :key="item.label" effect="plain" type="info" @click="applyExample(item.label)"> {{ item.label }} · {{ item.note }} </el-tag>
          </div>
        </div>
      </section>

      <section class="panel">
        <header>
          <h4>转换结果</h4>
          <p>默认补全「人民币」前缀，符合银行票据规范</p>
        </header>
        <el-form label-width="120px">
          <el-form-item label="标准金额">
            <el-input v-model="state.normalized" readonly placeholder="自动规范化后金额" />
          </el-form-item>
        </el-form>
        <el-input v-model="state.result" type="textarea" :rows="4" readonly placeholder="生成结果将在此显示" />
      </section>

      <section class="panel">
        <header>
          <h4>规范要点</h4>
          <p>票据填写时常见要求，避免出现空白或误写</p>
        </header>
        <ul class="rule-list">
          <li>金额到元为止，元后需写“整”(或“正”)，角位有值可不写。</li>
          <li>金额前加“人民币”，大写金额需紧挨填写不得留空。</li>
          <li>角位为 0 且分位有值时，元后需补写“零”。</li>
          <li>连续多个 0 仅写一个“零”，避免重复堆叠。</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.tool-scroll {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
}
.tool-narrow {
  max-width: 760px;
  margin: 0 auto;
}
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
  border-color: rgba(var(--accent-rgb), 0.4);
  color: var(--accent);
}
.rule-list {
  margin: 0;
  padding-left: 18px;
  color: var(--ppx-text-secondary);
  line-height: 1.7;
}
</style>
