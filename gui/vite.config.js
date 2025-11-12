import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

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
  plugins: [vue(), devPortReporter()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 1500, // 块大小警告的限制（以 kbs 为单位）
    rollupOptions: {
      output: {
        // 分解块，将大块分解成更小的块
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return id.toString().split('node_modules/')[1].split('/')[0].toString()
          }
        },
        // 将不同的文件放在不同的文件下
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId ? chunkInfo.facadeModuleId.split('/') : []
          const fileName = facadeModuleId[facadeModuleId.length - 2] || '[name]'
          return `js/${fileName}/[name].[hash].js`
        }
      }
    }
  }
})
