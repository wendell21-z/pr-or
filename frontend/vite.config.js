import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/fact': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/solve': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/solution': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/im': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      '/ws': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      '/jvs-aps': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
