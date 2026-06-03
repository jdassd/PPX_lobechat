<template>
  <section class="panel">
    <header>
      <h4>配置固定格式</h4>
      <p>定义第一行字段、选择工作表并预览样例数据</p>
    </header>
    <el-form :model="preview" label-width="110px">
      <el-form-item label="源 Excel">
        <div class="field-row">
          <el-button type="primary" @click="selectExcel('preview')">选择文件</el-button>
          <span v-if="preview.file" class="file-chip">{{ preview.file.filename }}</span>
          <el-tag v-else type="info" effect="plain">尚未选择</el-tag>
        </div>
      </el-form-item>
      <el-form-item v-if="preview.sheets.length" label="工作表">
        <el-select v-model="preview.sheet" style="width: 220px">
          <el-option v-for="sheet in preview.sheets" :key="sheet" :label="sheet" :value="sheet" />
        </el-select>
      </el-form-item>
      <el-form-item label="分隔符">
        <el-input
          v-model="preview.delimiter"
          placeholder="默认使用 |"
          maxlength="4"
          style="width: 120px"
        />
      </el-form-item>
      <el-form-item label="结构定义">
        <el-input
          v-model="preview.schemaText"
          type="textarea"
          :rows="2"
          placeholder="示例：姓名|手机号|地区|业务类型"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="loadPreview">刷新预览</el-button>
      </el-form-item>
    </el-form>
    <div v-if="preview.schema.length" class="schema-chips">
      <p class="result-title">字段结构</p>
      <div class="schema-tags">
        <el-tag
          v-for="field in preview.schema"
          :key="field"
          size="large"
          effect="plain"
        >
          {{ field }}
        </el-tag>
      </div>
      <p class="schema-note">总行数：{{ preview.rowCount }} · 当前工作表：{{ preview.sheet || '默认' }}</p>
    </div>
    <div v-if="preview.sample.length" class="result-block">
      <p class="result-title">样例数据</p>
      <el-table
        :data="preview.sample"
        height="260"
        border
        size="small"
        header-cell-class-name="table-header"
      >
        <el-table-column
          v-for="field in preview.schema"
          :key="field"
          :prop="field"
          :label="field"
          show-overflow-tooltip
        />
      </el-table>
    </div>
  </section>
</template>

<script setup>
defineProps({
  // state.preview 切片（reactive 引用，子组件内 v-model 直接修改保持响应式）
  preview: {
    type: Object,
    required: true
  },
  // 共享 loading 标志（state.loading）
  loading: {
    type: Boolean,
    default: false
  },
  // 壳提供的文件选择处理（保持原 selectExcel 契约）
  selectExcel: {
    type: Function,
    required: true
  },
  // 壳提供的预览加载处理（保持原 loadPreview 契约）
  loadPreview: {
    type: Function,
    required: true
  }
})
</script>

<style scoped>
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
</style>
