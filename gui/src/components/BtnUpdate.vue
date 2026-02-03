<template>
  <div>
    <el-tooltip content="检测更新" placement="bottom" effect="light">
      <el-button key="plain" size="small" link class="update-btn" @click="onCheckUpdate(false)">
        <span v-show="state.btnLoading" class="update-label">检测更新</span>
        <SvgIcon :name="state.btnLoading ? 'ele-Loading' : 'icon-Update'" :size="16" :class="{ 'is-loading': state.btnLoading }"></SvgIcon>
      </el-button>
    </el-tooltip>

    <el-dialog v-model="state.checkVisible" title="检测更新" top="30vh" draggable destroy-on-close :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false" :center="false" append-to-body>
      <div>
        <SvgIcon v-if="state.code == 1" name="ele-SuccessFilled" :size="18" color="var(--ppx-success)" style="top:4px"></SvgIcon>
        <SvgIcon v-else-if="state.code == 0" name="ele-WarningFilled" :size="18" color="var(--ppx-warning)" style="top:4px"></SvgIcon>
        <SvgIcon v-else-if="state.code == -1" name="ele-CircleCloseFilled" :size="18" color="var(--ppx-danger)" style="top:4px"></SvgIcon>
        {{ state.msg }}
      </div>
      <div v-if="state.code == 0 && state.body != ''" class="update-info">
        <div v-for="item in state.body">{{ item }}</div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-link v-if="state.htmlUrl != ''" class="float-l mt10" type="info" @click="onOpenLink">手动更新</el-link>
          <el-button v-if="state.code == 0" @click="state.checkVisible = false">取消</el-button>
          <el-button type="primary" @click="onConfirm">确认</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog v-model="state.downloadVisible" title="下载更新" align-center draggable destroy-on-close :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false" append-to-body>
      <div>
        <div class="mb6">
          <SvgIcon name="ele-Loading" :size="14" class="is-loading mr2" style="top:2px" color="var(--ppx-neon-blue)"></SvgIcon>
          正在下载更新...
        </div>
        <el-progress :text-inside="true" :stroke-width="25" :percentage="state.downloadPercentage">
          <span>{{ state.downloadSizeShow }}</span>
        </el-progress>
      </div>
      <div v-if="state.htmlUrl != ''" class="tip">
        若网速不理想，请尝试
        <span><el-link type="primary" @click="onOpenLink" class="tip-sd">手动更新</el-link></span>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <!-- <el-link v-if="state.htmlUrl != ''" class="float-l mt10" type="info" @click="onOpenLink">手动更新</el-link> -->
          <el-button @click="onCancel">取消</el-button>
          <el-button type="primary" @click="onBack">后台更新</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { reactive, onMounted } from 'vue'

const state = reactive({
  checkVisible: false,
  btnLoading: false,
  code: 0, // 0=>有新版本; -1=>联网失败; 1=>已经是最新版本
  msg: '',
  htmlUrl: '', // 手动更新网址
  body: [], // 版本介绍
  downloadVisible: false,
  downloadSizeShow: '', // 下载过程中大小数值展示
  downloadPercentage: 0, // 下载过程中大小百分比
  backUpdate: false, // 是否后台更新
  timer: '',
})

onMounted(() => {
  setPy2Js() // 来自py的调用
})

// 监听pywebview是否已经准备好了
window.addEventListener('pywebviewready', async () => {
  onCheckUpdate(true) // 程序第一次打开，自动检测更新
})

const setPy2Js = () => {
  // 来自py的调用
  window['py2js_updateAppProgress'] = (res) => {
    // res 已经是对象，不需要 JSON.parse
    // console.log('js', res)
    state.downloadSizeShow = res['sizeShow']
    state.downloadPercentage = res['percentage']
  }
}

// 检测更新
const onCheckUpdate = (init = false) => {
  if (state.backUpdate) {
    // 从后台更新恢复过来
    state.downloadVisible = true
    state.btnLoading = false
  } else {
    // 第一次打开
    state.btnLoading = true
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.system_checkNewVersion().then((res) => {
        // console.log(init, res)
        // 程序第一次打开，自动检测更新 或 手动点击检测更新
        if (!init || res.code == 0) {
          state.code = res.code
          state.msg = res.msg || '获取更新信息失败'
          if (res.htmlUrl != undefined) {
            state.htmlUrl = res.htmlUrl
          }
          if (res.body != undefined) {
            let body = res.body
            body = body.replaceAll('\r', '')
            state.body = body.split('\n')
          }
          state.checkVisible = true
        }
        state.btnLoading = false
      }).catch((err) => {
        if (!init) {
          state.code = -1
          state.msg = '检查更新出错: ' + err
          state.checkVisible = true
        }
        state.btnLoading = false
      })
    } else {
       state.btnLoading = false
    }
  }
}

// 手动更新
const onOpenLink = () => {
  // console.log(state.htmlUrl)
  window.pywebview.api.system_pyOpenFile(state.htmlUrl)
  state.checkVisible = false
}

// 确认更新 - 检查更新
const onConfirm = () => {
  state.checkVisible = false
  if (state.code == 0) {
    state.downloadVisible = true
    window.pywebview.api.system_downloadNewVersion().then((res) => {
      // console.log('res', res)
      state.downloadVisible = false
      if (res.code == 0) {
        ElMessage.success('下载完成')
        state.btnLoading = false
        window.pywebview.api.system_pyOpenFile(res.downloadPath)
      } else {
        ElMessage.error(res.msg)
      }
    })
  }
}

// 取消更新 - 下载更新
const onCancel = () => {
  state.backUpdate = false
  state.downloadVisible = false
  state.btnLoading = false
  window.pywebview.api.system_cancelDownloadNewVersion()
}

// 后台更新 - 下载更新
const onBack = () => {
  state.backUpdate = true
  state.downloadVisible = false
  state.btnLoading = true
}
</script>

<style scoped>
.update-info {
  margin-left: 20px;
  margin-top: 10px;
  padding: 10px;
  color: var(--ppx-text-muted);
  font-size: 12px;
  overflow: scroll;
  background-color: var(--ppx-glass-bg);
  border: 1px solid var(--ppx-glass-border);
  border-radius: var(--ppx-radius-sm);
  max-height: 50px;
}

.tip {
  margin-top: 10px;
  color: var(--ppx-text-muted);
  font-size: 11px;
}

.tip-sd {
  font-size: 11px;
  top: -1px;
}

.update-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px !important;
  height: 24px !important;
}

.update-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--ppx-text-muted);
  letter-spacing: 0.3px;
  animation: updatePulse 1.2s ease-in-out infinite;
}

@keyframes updatePulse {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 1;
  }
}
</style>
