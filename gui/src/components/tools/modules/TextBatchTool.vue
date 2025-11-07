<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import ToolCard from '../ToolCard.vue'
import { useToolkitStore } from '@/stores/toolkit'

const store = useToolkitStore()

const drawerVisible = computed({
  get: () => store.activeDrawer === 'text',
  set: (val) => {
    if (!val) {
      store.closeDrawer()
    }
  }
})

const stats = computed(() => store.textBatch.stats)
const options = computed(() => store.textBatch.options)
const hasError = computed(() => Boolean(store.textBatch.error))

const setOption = (key, value) => {
  store.updateTextOptions({ [key]: value })
}

const copyOutput = async () => {
  if (!store.textBatch.output) {
    return
  }
  try {
    await navigator.clipboard.writeText(store.textBatch.output)
    ElMessage.success('已复制处理结果')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}
</script>

<template>
  <ToolCard
    title="文本批处理"
    subtitle="格式化 / 正则 / 批量转换"
    badge="自动"
    tone="purple"
  >
    <div class="card-stats">
      <div>
        <p>输入行数</p>
        <strong>{{ stats.lines }}</strong>
      </div>
      <div>
        <p>输出字符</p>
        <strong>{{ stats.chars }}</strong>
      </div>
      <div>
        <p>处理状态</p>
        <span>{{ hasError ? '失败' : '就绪' }}</span>
      </div>
    </div>
    <template #actions>
      <el-button size="small" type="primary" @click="store.processTextBatch">立即处理</el-button>
      <el-button size="small" text @click="store.openDrawer('text')">扩展视图</el-button>
    </template>
  </ToolCard>

  <el-drawer
    title="文本批处理工作台"
    v-model="drawerVisible"
    destroy-on-close
    size="55%"
    @close="store.closeDrawer"
  >
    <el-row :gutter="16">
      <el-col :span="12">
        <h3>输入</h3>
        <el-input
          v-model="store.textBatch.input"
          type="textarea"
          :rows="14"
          placeholder="待处理内容"
        />
      </el-col>
      <el-col :span="12">
        <div class="result-header">
          <h3>输出</h3>
          <el-button size="small" @click="copyOutput">复制</el-button>
        </div>
        <el-input
          :model-value="store.textBatch.output"
          type="textarea"
          :rows="14"
          readonly
        />
      </el-col>
    </el-row>

    <section class="drawer-section mt20">
      <header class="drawer-section__header">
        <h3>操作栈</h3>
        <el-button type="primary" @click="store.processTextBatch">执行</el-button>
      </header>

      <el-row :gutter="16">
        <el-col :span="8">
          <el-switch
            :model-value="options.trimWhitespace"
            active-text="裁剪首尾空格"
            @change="setOption('trimWhitespace', $event)"
          />
          <el-switch
            :model-value="options.removeBlankLines"
            active-text="移除空行"
            @change="setOption('removeBlankLines', $event)"
          />
          <el-switch
            :model-value="options.uniqueLines"
            active-text="去重"
            @change="setOption('uniqueLines', $event)"
          />
          <el-switch
            :model-value="options.sortLines"
            active-text="排序"
            @change="setOption('sortLines', $event)"
          />
        </el-col>
        <el-col :span="8">
          <el-form label-position="top">
            <el-form-item label="大小写">
              <el-select
                :model-value="options.caseStyle"
                @change="setOption('caseStyle', $event)"
              >
                <el-option label="保持原样" value="none" />
                <el-option label="大写" value="upper" />
                <el-option label="小写" value="lower" />
                <el-option label="标题" value="title" />
              </el-select>
            </el-form-item>
            <el-form-item label="格式化">
              <el-select
                :model-value="options.formatter"
                @change="setOption('formatter', $event)"
              >
                <el-option label="关闭" value="none" />
                <el-option label="JSON" value="json" />
                <el-option label="YAML" value="yaml" />
                <el-option label="SQL" value="sql" />
              </el-select>
            </el-form-item>
            <el-form-item label="缩进">
              <el-input-number
                :model-value="options.indent"
                :min="2"
                :max="8"
                @change="setOption('indent', $event)"
              />
            </el-form-item>
          </el-form>
        </el-col>
        <el-col :span="8">
          <el-form label-position="top">
            <el-form-item label="正则表达式">
              <el-input
                :model-value="options.regexPattern"
                placeholder="pattern"
                @input="setOption('regexPattern', $event)"
              />
            </el-form-item>
            <el-form-item label="替换为">
              <el-input
                :model-value="options.regexReplace"
                placeholder="replacement"
                @input="setOption('regexReplace', $event)"
              />
            </el-form-item>
            <el-switch
              :model-value="options.regexEnabled"
              active-text="启用正则替换"
              @change="setOption('regexEnabled', $event)"
            />
          </el-form>
        </el-col>
      </el-row>
      <el-alert
        v-if="hasError"
        type="error"
        :title="store.textBatch.error"
        show-icon
        class="mt10"
      />
    </section>
  </el-drawer>
</template>
