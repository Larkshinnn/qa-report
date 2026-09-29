import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  worker: { format: 'es' },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true } },
  },
  test: { environment: 'jsdom', clearMocks: true, setupFiles: ['./src/test-setup.ts'] },
})
