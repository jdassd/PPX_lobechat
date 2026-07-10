import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 思维导图子应用：构建产物输出到 static/mindmap，
// 由工具箱内嵌的 FastAPI 服务（api/mindmap）托管。
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // 开发调试时代理到内嵌服务的默认端口（api/mindmap/tool.py DEFAULT_PORT）
      '/api': 'http://127.0.0.1:8323',
      '/ws': {
        target: 'ws://127.0.0.1:8323',
        ws: true,
      },
    },
  },
  build: {
    outDir: '../static/mindmap',
    emptyOutDir: true,
  },
})
