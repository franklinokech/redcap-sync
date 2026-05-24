import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      // @ → src/  so you write @/components/... instead of ../../components/...
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    port: 5173,
    proxy: {
      // Any request to /api/... is forwarded to Django
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        // No rewrite — Django already has /api/ prefix
      },
    },
  },
})