import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'

// Unit tests for the Quasar SPA (client wrapper, Pinia stores, components).
// The Quasar Vite plugin auto-imports components and points "quasar" at the
// client build, so component tests can mount SFCs that use <q-*> tags.
// Run with: bun run test
export default defineConfig({
  plugins: [vue({ template: { transformAssetUrls } }), quasar()],
  test: {
    // Default to node; DOM-based component tests opt into happy-dom per file.
    environment: 'node',
    globals: true,
    include: ['tests/**/*.spec.js'],
  },
})
