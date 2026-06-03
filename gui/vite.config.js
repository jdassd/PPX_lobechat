import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// Element Plus 按需自动导入
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
// 为「在 <script> 中手动 import 的 Element Plus 组件」（如 ElMessage / ElMessageBox）自动按需导入样式
import ElementPlus from 'unplugin-element-plus/vite'

const guiDir = fileURLToPath(new URL('.', import.meta.url))
const portFilePath = path.resolve(guiDir, '../.ppx-dev-port')

const devPortReporter = () => ({
  name: 'ppx-dev-port-reporter',
  apply: 'serve',
  configureServer(server) {
    const writePort = () => {
      const address = server?.httpServer?.address()
      if (address && typeof address === 'object' && address.port) {
        const payload = {
          port: address.port,
          pid: process.pid,
          time: Date.now()
        }
        try {
          fs.writeFileSync(portFilePath, JSON.stringify(payload), 'utf-8')
        } catch (error) {
          console.warn('[ppx] 写入 dev port 失败:', error.message)
        }
      }
    }

    const cleanup = () => {
      try {
        if (fs.existsSync(portFilePath)) {
          fs.unlinkSync(portFilePath)
        }
      } catch (error) {
        console.warn('[ppx] 清理 dev port 文件失败:', error.message)
      }
    }

    server?.httpServer?.once('listening', writePort)
    server?.httpServer?.once('close', cleanup)
    process.once('exit', cleanup)
    process.once('SIGINT', () => {
      cleanup()
      process.exit(0)
    })
    process.once('SIGTERM', () => {
      cleanup()
      process.exit(0)
    })
  }
})

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // 自动导入 Element Plus 的命令式 API（ElMessage / ElMessageBox / ElLoading / ElNotification 等）
    // importStyle: 'css' 确保这些在 <script> 中使用的组件其样式也会被按需注入，避免弹窗/消息丢样式
    AutoImport({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })]
    }),
    // 自动按需导入模板中使用的 <el-xxx> 组件及其对应样式
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })]
    }),
    // 处理组件文件 <script> 中手动 import 的 Element Plus 组件，自动注入其样式
    // 这样 13 个组件中已有的 `import { ElMessage } from 'element-plus'` 等无需改动，弹窗/消息样式也能正常加载
    ElementPlus({ useSource: false }),
    devPortReporter()
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    sourcemap: false,
    // 调回更合理的块大小警告阈值（kb），按需加载后单块体积明显下降
    chunkSizeWarningLimit: 800,
    // 生产构建使用 esbuild 压缩（Vite 默认，速度快），并移除调试输出
    minify: 'esbuild',
    rollupOptions: {
      output: {
        // 合理分组的分块策略：vue 生态、element-plus、echarts 各自独立，其余三方库归入 vendor
        // 取代「每个 node_modules 包单独成块」的过碎策略
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return
          }
          if (id.includes('/vue') || id.includes('@vue') || id.includes('vue-router') || id.includes('pinia')) {
            return 'vue-vendor'
          }
          if (id.includes('element-plus') || id.includes('@element-plus')) {
            return 'element-plus'
          }
          if (id.includes('echarts') || id.includes('zrender')) {
            return 'echarts'
          }
          return 'vendor'
        },
        // 将不同的文件放在不同的文件下
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/') : []
          const fileName = facadeModuleId[facadeModuleId.length - 2] || '[name]'
          return `js/${fileName}/[name].[hash].js`
        }
      }
    }
  },
  // 生产环境移除 console / debugger
  esbuild: {
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : []
  }
})
