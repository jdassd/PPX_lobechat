<script setup>
import { computed } from 'vue'
import ToolCard from '../ToolCard.vue'
import { useToolkitStore } from '@/stores/toolkit'
import dayjs from '@/utils/dayjs'

const store = useToolkitStore()
const COMMON_CURRENCIES = ['USD', 'CNY', 'EUR', 'JPY', 'GBP', 'HKD', 'AUD', 'CAD', 'SGD']

const drawerVisible = computed({
  get: () => store.activeDrawer === 'unit',
  set: (val) => {
    if (!val) {
      store.closeDrawer()
    }
  }
})

const catalog = computed(() => store.converter.catalog || {})
const categoryOptions = computed(() => Object.entries(catalog.value).map(([key, meta]) => ({ value: key, label: meta.label })))
const unitOptions = computed(() => {
  const category = store.converter.category
  const meta = catalog.value[category]
  if (!meta) {
    return []
  }
  return Object.entries(meta.units).map(([value, detail]) => ({
    value,
    label: `${detail.label} (${value})`
  }))
})

const ratesMeta = computed(() => store.converter.ratesMeta)
const currencyOptions = computed(() => {
  const map = ratesMeta.value?.rates || {}
  const baseList = COMMON_CURRENCIES.filter((code) => code === ratesMeta.value?.base || map[code])
  return baseList.map((code) => ({
    value: code,
    label: `${code} ${map[code] ? `· ${map[code].toFixed ? map[code].toFixed(2) : map[code]}` : ''}`
  }))
})

const handleCategoryChange = (value) => {
  store.converter.category = value
  const options = unitOptions.value
  if (options.length >= 2) {
    store.converter.fromUnit = options[0].value
    store.converter.toUnit = options[1].value
  }
  store.applyUnitConversion()
}

const swapUnits = () => {
  const temp = store.converter.fromUnit
  store.converter.fromUnit = store.converter.toUnit
  store.converter.toUnit = temp
  store.applyUnitConversion()
}
</script>

<template>
  <ToolCard
    title="单位与汇率换算"
    subtitle="长度 / 重量 / 货币"
    badge="实时"
    tone="green"
  >
    <div class="card-stats">
      <div>
        <p>当前类型</p>
        <strong>{{ catalog[store.converter.category]?.label || '加载中' }}</strong>
      </div>
      <div>
        <p>最近结果</p>
        <strong>{{ store.converter.result?.display ?? '--' }}</strong>
      </div>
      <div>
        <p>汇率基准</p>
        <span>{{ ratesMeta?.base || store.converter.currency.base }}</span>
      </div>
    </div>
    <template #actions>
      <el-button size="small" @click="store.applyUnitConversion">换算</el-button>
      <el-button size="small" text @click="store.openDrawer('unit')">扩展视图</el-button>
    </template>
  </ToolCard>

  <el-drawer
    title="单位与汇率换算"
    v-model="drawerVisible"
    destroy-on-close
    size="50%"
    @close="store.closeDrawer"
  >
    <section class="drawer-section">
      <header class="drawer-section__header">
        <h3>常规单位</h3>
        <el-select
          v-model="store.converter.category"
          placeholder="请选择类别"
          style="width: 160px"
          @change="handleCategoryChange"
        >
          <el-option
            v-for="opt in categoryOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </header>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form label-position="top">
            <el-form-item label="源单位">
              <el-select v-model="store.converter.fromUnit">
                <el-option
                  v-for="opt in unitOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="数值">
              <el-input-number v-model="store.converter.baseValue" :min="0" />
            </el-form-item>
          </el-form>
        </el-col>
        <el-col :span="2" class="swap-col">
          <el-button circle icon="ele-Refresh" @click="swapUnits" />
        </el-col>
        <el-col :span="8">
          <el-form label-position="top">
            <el-form-item label="目标单位">
              <el-select v-model="store.converter.toUnit">
                <el-option
                  v-for="opt in unitOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="结果">
              <el-input :model-value="store.converter.result?.display ?? '--'" readonly />
            </el-form-item>
          </el-form>
        </el-col>
        <el-col :span="6" class="favorite-list">
          <p>快捷组合</p>
          <el-tag
            v-for="fav in store.converter.favorites"
            :key="fav.id"
            class="favorite-pill"
            @click="
              () => {
                store.converter.category = fav.category
                store.converter.fromUnit = fav.from
                store.converter.toUnit = fav.to
                if (fav.presetValue) {
                  store.converter.baseValue = fav.presetValue
                }
                store.applyUnitConversion()
              }
            "
          >
            {{ fav.label }}
          </el-tag>
        </el-col>
      </el-row>
      <div class="drawer-actions">
        <el-button @click="store.applyUnitConversion">立即换算</el-button>
      </div>
    </section>

    <section class="drawer-section mt20">
      <header class="drawer-section__header">
        <h3>汇率换算</h3>
        <div>
          <small v-if="ratesMeta">
            {{ dayjs(ratesMeta.fetched_at).format('YYYY/MM/DD HH:mm') }} · {{ ratesMeta.provider }}
          </small>
          <el-button
            size="small"
            type="primary"
            plain
            :loading="store.converter.refreshingRates"
            @click="store.refreshRates(true)"
          >
            刷新
          </el-button>
        </div>
      </header>
      <el-row :gutter="12">
        <el-col :span="6">
          <el-input-number
            v-model="store.converter.currency.amount"
            :min="0"
            label="金额"
          />
        </el-col>
        <el-col :span="6">
          <el-select v-model="store.converter.currency.from" filterable>
            <el-option
              v-for="opt in currencyOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-col>
        <el-col :span="2" class="swap-col">
          <el-button circle icon="ele-Right" @click="
            () => {
              const temp = store.converter.currency.from
              store.converter.currency.from = store.converter.currency.to
              store.converter.currency.to = temp
            }
          " />
        </el-col>
        <el-col :span="6">
          <el-select v-model="store.converter.currency.to" filterable>
            <el-option
              v-for="opt in currencyOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="store.applyCurrencyConversion">换算</el-button>
        </el-col>
      </el-row>
      <div class="currency-result">
        <p>结果</p>
        <strong>{{ store.converter.currency.result?.display ?? '--' }}</strong>
      </div>
    </section>
  </el-drawer>
</template>
