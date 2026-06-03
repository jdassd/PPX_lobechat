import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

// 组件库 ElementPlus（按需加载）
// 组件与样式由 vite 中的 unplugin-vue-components / unplugin-auto-import 自动按需导入，
// 因此此处不再 app.use(ElementPlus) 全量注册，也不再引入 element-plus/dist/index.css 全量样式。
// 仅保留暗黑模式所需的 CSS 变量（按需导入不覆盖该文件）。
import 'element-plus/theme-chalk/dark/css-vars.css' // 暗黑模式

// 图标库 ElementPlus
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(`ele-${key}`, component)
}
// 自定义图标库
import SvgIcon from '@/components/SvgIcon/index.vue'
app.component('SvgIcon', SvgIcon)

// 自定义样式
import '@/assets/main.scss'

app.mount('#app')
