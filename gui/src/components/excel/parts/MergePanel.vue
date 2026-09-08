<template>
  <section class="panel">
    <header>
      <h4>合并为单个 Excel</h4>
      <p>按第一份分表的字段合并全部数据；表头、公式与去空格规则应用于每份输入。展开文件可设置字段映射。</p>
    </header>
    <div class="subpanel">
      <div class="subpanel-head">
        <div>
          <h5>分表列表</h5>
          <p>支持批量选择或多次添加</p>
        </div>
        <div class="field-row">
          <el-button size="small" @click="selectExcel('mergeTables', true)">选择文件</el-button>
          <el-button size="small" text type="danger" :disabled="!merge.tables.length" @click="clearList('mergeTables')"> 清空 </el-button>
        </div>
      </div>
      <el-table v-if="merge.tables.length" :data="merge.tables" size="small" border>
        <el-table-column type="expand">
          <template #default="scope">
            <el-form inline style="padding: 16px">
              <el-form-item v-for="column in merge.tables[0]?.columns || []" :key="column" :label="'目标字段：' + column">
                <el-select :model-value="scope.row.fieldMapping[column] || column" @update:model-value="scope.row.fieldMapping[column] = $event"><el-option v-for="source in scope.row.columns" :key="source" :value="source" :label="source" /></el-select>
              </el-form-item>
            </el-form>
          </template>
        </el-table-column>
        <el-table-column type="index" width="50" label="#" />
        <el-table-column prop="path" label="文件（展开设置字段映射）" min-width="220" show-overflow-tooltip />
        <el-table-column label="工作表" width="220">
          <template #default="scope">
            <el-input v-model="scope.row.sheet" size="small" placeholder="留空使用默认工作表" @change="loadTableColumns(scope.row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="scope">
            <el-button link type="danger" @click="removeFile('mergeTables', scope.$index)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="尚未添加分表" />
    </div>
    <el-form :model="merge" label-width="120px" class="merge-form">
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="merge.outputDir" readonly placeholder="留空自动创建" />
          <el-button @click="selectDir('merge')">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="输出文件名">
        <el-input v-model="merge.outputName" placeholder="例如：汇总主表.xlsx" />
      </el-form-item>
    </el-form>
    <div class="actions">
      <el-button type="primary" :disabled="!merge.tables.length" :loading="loading" @click="runMergeTables"> 开始合并 </el-button>
    </div>
    <div v-if="merge.result" class="result-block">
      <p class="result-title">输出结果</p>
      <el-button class="output-path" type="primary" text @click="openPath(merge.result)">
        {{ merge.result }}
      </el-button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  loadTableColumns: { type: Function, required: true },
  // state.merge 切片（reactive 引用，v-model 直接修改保持响应式）
  merge: {
    type: Object,
    required: true
  },
  // 共享 loading 标志（state.loading）
  loading: {
    type: Boolean,
    default: false
  },
  // 壳提供的共享处理函数
  selectExcel: {
    type: Function,
    required: true
  },
  selectDir: {
    type: Function,
    required: true
  },
  removeFile: {
    type: Function,
    required: true
  },
  clearList: {
    type: Function,
    required: true
  },
  openPath: {
    type: Function,
    required: true
  },
  runMergeTables: {
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

.output-path {
  justify-content: flex-start;
  max-width: 100%;
  height: auto;
  min-height: 32px;
  padding: 8px 10px;
  text-align: left;
  white-space: normal;
}
.output-path :deep(span) {
  min-width: 0;
  overflow-wrap: anywhere;
  white-space: normal;
  line-height: 1.6;
}

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

.merge-form {
  margin-top: 18px;
}
</style>
