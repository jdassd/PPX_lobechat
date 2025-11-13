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
  json: {
    operation: 'format',
    input: '',
    path: '',
    output: ''
  },
  transform: {
    mode: 'upper',
    input: '',
    output: ''
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
    ElMessage.warning('该功能需在桌面客户端使用')
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
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
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
      ElMessage.success(res.msg || '处理完成')
    } else {
      ElMessage.error(res?.msg || '处理失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '处理失败')
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
      ElMessage.success(res.msg || '转换成功')
    } else {
      ElMessage.error(res?.msg || '转换失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '转换失败')
  } finally {
    state.loading = false
  }
}

const runHash = async () => {
  if (!ensurePyReady()) return
  if (state.hash.sourceType === 'file' && !state.hash.file) {
    ElMessage.warning('请选择文件')
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
      ElMessage.success(res.msg || '计算完成')
    } else {
      ElMessage.error(res?.msg || '计算失败')
    }
  } catch (error) {
    ElMessage.error(error?.message || '计算失败')
  } finally {
    state.loading = false
  }
}

const selectHashFile = async () => {
  if (!ensurePyReady()) return
  const files = await window.pywebview.api.system_pyCreateFileDialog(['全部文件 (*.*)'])
  if (files?.length) {
    state.hash.file = files[0]
  }
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
          <h3>文本与数据处理</h3>
          <p class="sub">编码、JSON、大小写和哈希处理一站完成</p>
        </div>
        <el-tag type="success">Phase 1</el-tag>
      </div>
    </template>
    <div class="text-tool">
      <el-tabs v-model="state.activeTab">
        <el-tab-pane label="编码 / 解码" name="codec">
          <section class="panel">
            <header>
              <h4>常见文本编码</h4>
              <p>Base64、URL、HTML 与 UTF-8/GBK 互转</p>
            </header>
            <el-form :model="state.codec" label-width="120px">
              <el-form-item label="编码类型">
                <el-select v-model="state.codec.codecType" style="width: 200px">
                  <el-option label="Base64" value="base64" />
                  <el-option label="URL" value="url" />
                  <el-option label="HTML" value="html" />
                  <el-option label="字符集转换" value="charset" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.codec.codecType !== 'charset'" label="操作">
                <el-radio-group v-model="state.codec.operation">
                  <el-radio-button label="encode">编码</el-radio-button>
                  <el-radio-button label="decode">解码</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-else label="方向">
                <el-radio-group v-model="state.codec.direction">
                  <el-radio-button label="utf8_to_gbk">UTF-8 → GBK</el-radio-button>
                  <el-radio-button label="gbk_to_utf8">GBK → UTF-8</el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.codec.input"
                type="textarea"
                :rows="8"
                placeholder="在此输入原文本"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runCodec">执行</el-button>
              </div>
              <el-input
                v-model="state.codec.output"
                type="textarea"
                :rows="8"
                placeholder="输出结果"
                readonly
              />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="JSON 工具" name="json">
          <section class="panel">
            <header>
              <h4>JSON 格式化、压缩与查询</h4>
              <p>支持 JSONPath 风格的 $ 节点查询</p>
            </header>
            <el-form :model="state.json" label-width="120px" class="form-gap">
              <el-form-item label="操作">
                <el-select v-model="state.json.operation" style="width: 220px">
                  <el-option label="美化" value="format" />
                  <el-option label="压缩" value="compress" />
                  <el-option label="校验" value="validate" />
                  <el-option label="查询" value="query" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.json.operation === 'query'" label="路径">
                <el-input
                  v-model="state.json.path"
                  placeholder="示例：$.items[0].name"
                  clearable
                />
              </el-form-item>
            </el-form>
            <div class="text-grid">
              <el-input
                v-model="state.json.input"
                type="textarea"
                :rows="10"
                placeholder="粘贴 JSON 字符串"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runJson">执行</el-button>
              </div>
              <PreviewPanel title="输出" :content="state.json.output" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="文本转换" name="transform">
          <section class="panel">
            <header>
              <h4>大小写与命名规范</h4>
              <p>一键切换 Upper / Lower / Camel / Snake</p>
            </header>
            <el-form :model="state.transform" label-width="120px" class="form-gap">
              <el-form-item label="转换类型">
                <el-select v-model="state.transform.mode" style="width: 240px">
                  <el-option label="全大写" value="upper" />
                  <el-option label="全小写" value="lower" />
                  <el-option label="标题格式" value="title" />
                  <el-option label="句首大写" value="sentence" />
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
                placeholder="输入原始文本"
              />
              <div class="text-grid-actions">
                <el-button type="primary" :loading="state.loading" @click="runTransform">转换</el-button>
              </div>
              <PreviewPanel title="结果" :content="state.transform.output" />
            </div>
          </section>
        </el-tab-pane>

        <el-tab-pane label="哈希计算" name="hash">
          <section class="panel">
            <header>
              <h4>MD5 / SHA 系列</h4>
              <p>支持字符串与文件两种来源</p>
            </header>
            <el-form :model="state.hash" label-width="120px" class="form-gap">
              <el-form-item label="输入类型">
                <el-radio-group v-model="state.hash.sourceType">
                  <el-radio-button label="text">文本</el-radio-button>
                  <el-radio-button label="file">文件</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="算法">
                <el-select v-model="state.hash.hashType" style="width: 200px">
                  <el-option label="MD5" value="md5" />
                  <el-option label="SHA-1" value="sha1" />
                  <el-option label="SHA-256" value="sha256" />
                  <el-option label="SHA-512" value="sha512" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="state.hash.sourceType === 'text'" label="文本">
                <el-input
                  v-model="state.hash.content"
                  type="textarea"
                  :rows="4"
                  placeholder="输入要计算的文本"
                />
              </el-form-item>
              <el-form-item v-else label="文件">
                <div class="field-row">
                  <el-input :model-value="state.hash.file?.path || ''" placeholder="尚未选择" readonly />
                  <el-button @click="selectHashFile">选择文件</el-button>
                </div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="state.loading" @click="runHash">开始计算</el-button>
              </el-form-item>
            </el-form>
            <el-input v-model="state.hash.result" readonly placeholder="哈希结果" />
          </section>
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  color: #8d90a2;
  letter-spacing: 2px;
}

.panel {
  background: #fff;
  border: 1px solid #e9edf5;
  border-radius: 18px;
  padding: 20px;
  margin-bottom: 24px;
}

.panel header h4 {
  margin: 0;
}

.panel header p {
  margin: 6px 0 0;
  color: #7a829d;
  font-size: 13px;
}

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

.field-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.form-gap {
  margin-top: 12px;
}
</style>
