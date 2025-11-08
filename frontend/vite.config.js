import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // 将 /api 请求代理到 Flask 后端
      '/api': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
      }
    }
  }
})