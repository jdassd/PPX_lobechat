/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution')

module.exports = {
  root: true,
  // 务实的推荐档：vue3-recommended 提供合理的 Vue3 规范，prettier 关闭与格式化冲突的规则
  extends: ['plugin:vue/vue3-recommended', 'eslint:recommended', '@vue/eslint-config-prettier'],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  globals: {
    // 由 unplugin-auto-import 注入的 Element Plus 命令式 API（避免 no-undef 误报）
    ElMessage: 'readonly',
    ElMessageBox: 'readonly',
    ElNotification: 'readonly',
    ElLoading: 'readonly',
    // Pywebview 注入的全局对象
    pywebview: 'readonly'
  },
  rules: {
    'vue/multi-word-component-names': 'off', // 关闭 eslint 检查组件名是否为多词命名
    'vue/no-v-html': 'off', // 项目内允许使用 v-html
    // 以下规则对存量代码降级为告警，避免一次性引入大量阻断性报错（务实档）
    'no-unused-vars': 'warn',
    'vue/no-unused-vars': 'warn',
    'vue/require-v-for-key': 'warn',
    // 工具面板接收父组件持有的响应式状态对象，允许修改其字段，但仍禁止替换整个 prop。
    'vue/no-mutating-props': ['error', { shallowOnly: true }]
  }
}
