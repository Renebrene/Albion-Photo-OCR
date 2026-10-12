import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'

// Dev only: forward /api to the FastAPI backend. Override the target with
// VITE_API_TARGET when the backend runs on a non-default host/port.
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8010'

export default defineConfig({
  plugins: [
    vue({ template: { transformAssetUrls } }),
    quasar(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
