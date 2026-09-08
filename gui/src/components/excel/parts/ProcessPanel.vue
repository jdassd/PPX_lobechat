<template>
  <section class="panel">
    <header>
      <h4>清洗 / 分组 / 排序 / 导出</h4>
      <p>先选择主 Excel，确认工作表和清洗规则，再将完整数据导出为新文件。</p>
    </header>
    <el-form :model="process" label-width="120px">
      <el-form-item label="主 Excel">
        <div class="input-block">
          <div class="field-row"><el-button @click="selectExcel('processInput')">选择 / 接收主 Excel</el-button><el-button v-if="preview.file" text type="danger" @click="clearInput">移除主文件</el-button></div>
          <span v-if="preview.file" class="input-path">{{ preview.file.path }}</span>
          <span v-else class="input-note">可接收上一步结果；接收只替换主文件，不自动执行。</span>
        </div>
      </el-form-item>
      <el-form-item v-if="preview.sheets.length" label="工作表"
        ><el-select v-model="preview.sheet" style="width: 220px"><el-option v-for="sheet in preview.sheets" :key="sheet" :value="sheet" :label="sheet" /></el-select
      ></el-form-item>
      <el-form-item v-if="preview.file && !schemaFields.length"><el-button :loading="loading" @click="loadPreview">重新读取工作表</el-button></el-form-item>
      <slot />
      <el-form-item label="按列分组">
        <el-select v-model="process.groupBy" placeholder="可选" clearable style="width: 220px">
          <el-option v-for="field in schemaFields" :key="field" :label="field" :value="field" />
        </el-select>
      </el-form-item>
      <el-form-item label="排序字段">
        <div class="field-row">
          <el-select v-model="process.sortBy" placeholder="可选" clearable style="width: 220px">
            <el-option v-for="field in schemaFields" :key="field" :label="field" :value="field" />
          </el-select>
          <el-radio-group v-model="process.sortOrder" size="small">
            <el-radio-button label="asc">升序</el-radio-button>
            <el-radio-button label="desc">降序</el-radio-button>
          </el-radio-group>
        </div>
      </el-form-item>
      <el-form-item label="输出目录">
        <div class="field-row">
          <el-input v-model="process.outputDir" placeholder="留空则自动创建" readonly />
          <el-button @click="selectDir('process')">选择目录</el-button>
        </div>
      </el-form-item>
      <el-form-item label="导出选项">
        <div class="toggle-row">
          <el-checkbox v-model="process.exportGroups" :disabled="!process.groupBy"> 分组导出 Excel </el-checkbox>
          <el-checkbox v-model="process.exportJson" :disabled="!process.groupBy"> 导出 JSON 图表 </el-checkbox>
          <el-checkbox v-model="process.exportCombined"> 合并主表 </el-checkbox>
        </div>
      </el-form-item>
    </el-form>

    <el-collapse class="subpanel">
      <el-collapse-item :title="'附加分表（' + process.mergeFiles.length + '）'" name="additional">
        <div class="subpanel-head">
          <div>
            <h5>附加分表</h5>
            <p>支持在主表前批量合并多个分表，再进入分组流程</p>
          </div>
          <div class="field-row">
            <el-button size="small" :disabled="!preview.file" @click="selectExcel('processMerge', true)">添加分表</el-button>
            <el-button size="small" text type="danger" :disabled="!process.mergeFiles.length" @click="clearList('processMerge')"> 清空 </el-button>
          </div>
        </div>
        <el-table v-if="process.mergeFiles.length" :data="process.mergeFiles" size="small" border>
          <el-table-column type="index" width="50" label="#" />
          <el-table-column prop="filename" label="文件名" />
          <el-table-column label="工作表" width="220">
            <template #default="scope">
              <el-input v-model="scope.row.sheet" size="small" placeholder="留空使用默认工作表" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="scope">
              <el-button link type="danger" @click="removeFile('processMerge', scope.$index)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="尚未添加分表" />
      </el-collapse-item>
    </el-collapse>

    <slot name="comparison" />
    <div class="actions">
      <el-button type="primary" :disabled="!preview.file || !schemaFields.length" :loading="loading" @click="runProcess">执行处理</el-button>
    </div>

    <div v-if="process.summary" class="result-block">
      <p class="result-title">处理摘要</p>
      <el-descriptions :column="2" size="small" border>
        <el-descriptions-item v-if="process.summary.sourceRows != null" label="输入总行数">{{ process.summary.sourceRows }}</el-descriptions-item>
        <el-descriptions-item v-if="process.summary.removedDuplicates != null" label="去除重复行">{{ process.summary.removedDuplicates }}</el-descriptions-item>
        <el-descriptions-item label="输出总行数">
          {{ process.summary.totalRows }}
        </el-descriptions-item>
        <el-descriptions-item label="分组列">
          {{ process.summary.groupBy || '未设置' }}
        </el-descriptions-item>
        <el-descriptions-item label="排序列"> {{ process.summary.sortBy || '未设置' }}（{{ process.summary.sortOrder === 'desc' ? '降序' : '升序' }}） </el-descriptions-item>
        <el-descriptions-item label="分组数量">
          {{ process.summary.groupCount }}
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="process.groups.length" class="group-table">
        <el-table :data="process.groups" size="small" border>
          <el-table-column prop="key" label="分组值" />
          <el-table-column prop="count" label="行数" width="120" />
        </el-table>
      </div>

      <div class="result-list">
        <template v-if="process.groupFiles.length">
          <p class="result-title">分组文件</p>
          <el-scrollbar max-height="140px">
            <div class="tag-list">
              <el-button v-for="file in process.groupFiles" :key="file" class="output-path" type="success" text @click="openPath(file)">
                {{ file }}
              </el-button>
            </div>
          </el-scrollbar>
        </template>

        <div class="tag-list">
          <el-button v-if="process.jsonPath" class="output-path" type="primary" text @click="openPath(process.jsonPath)"> JSON：{{ process.jsonPath }} </el-button>
          <el-button v-if="process.combinedPath" class="output-path" type="primary" text @click="openPath(process.combinedPath)"> 主表：{{ process.combinedPath }} </el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  preview: { type: Object, required: true },
  clearInput: { type: Function, required: true },
  loadPreview: { type: Function, required: true },
  // state.process 切片（reactive 引用，v-model 直接修改保持响应式）
  process: {
    type: Object,
    required: true
  },
  // 主文件当前工作表的字段，可在本页直接选择主文件。
  schemaFields: {
    type: Array,
    default: () => []
  },
  // 共享 loading 标志（state.loading）
  loading: {
    type: Boolean,
    default: false
  },
  // 壳提供的共享处理函数（契约与原实现一致）
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
  runProcess: {
    type: Function,
    required: true
  }
})
</script>

<style scoped>
.input-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  width: 100%;
}
.input-path {
  overflow-wrap: anywhere;
  color: var(--ppx-text-primary);
  font-size: 12px;
  line-height: 1.6;
}
.input-note {
  color: var(--ppx-text-muted);
  font-size: 12px;
}
.field-row {
  flex-wrap: wrap;
}
.result-block {
  margin-top: 16px;
}

.result-title {
  margin: 0 0 10px;
  font-weight: 600;
  color: var(--ppx-text-secondary);
}

.toggle-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
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

.group-table {
  margin: 16px 0;
}

.tag-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tag-list .output-path {
  justify-content: flex-start;
  max-width: 100%;
  height: auto;
  min-height: 32px;
  margin-left: 0;
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
</style>
