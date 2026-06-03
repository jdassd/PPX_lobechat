<template>
  <section class="panel">
    <header>
      <h4>独立合并工具</h4>
      <p>将多个分表统一导出为一个 Excel，方便生成主表</p>
    </header>
    <div class="subpanel">
      <div class="subpanel-head">
        <div>
          <h5>分表列表</h5>
          <p>支持批量选择或多次添加</p>
        </div>
        <div class="field-row">
          <el-button size="small" @click="selectExcel('mergeTables', true)">选择文件</el-button>
          <el-button
            size="small"
            text
            type="danger"
            @click="clearList('mergeTables')"
            :disabled="!merge.tables.length"
          >
            清空
          </el-button>
        </div>
      </div>
      <el-table
        v-if="merge.tables.length"
        :data="merge.tables"
        size="small"
        border
      >
        <el-table-column type="index" width="50" label="#" />
        <el-table-column prop="filename" label="文件名" />
        <el-table-column label="工作表" width="220">
          <template #default="scope">
            <el-input
              v-model="scope.row.sheet"
              size="small"
              placeholder="留空使用默认工作表"
            />
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
      <el-button type="primary" :loading="loading" @click="runMergeTables">
        开始合并
      </el-button>
    </div>
    <div v-if="merge.result" class="result-block">
      <p class="result-title">输出结果</p>
      <el-tag type="success" effect="plain" @click="openPath(merge.result)">
        {{ merge.result }}
      </el-tag>
    </div>
  </section>
</template>

<script setup>
defineProps({
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
