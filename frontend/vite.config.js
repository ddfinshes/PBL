import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5002',  // 使用 5001 端口避免与 macOS AirPlay 冲突
        changeOrigin: true
      }
    }
  }
})

