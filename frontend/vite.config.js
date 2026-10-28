import { defineConfig } from 'vite'
import fs from 'node:fs'
import path from 'node:path'

import vue from '@vitejs/plugin-vue'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'

// Dev only: forward /api to the FastAPI backend. Override the target with
// VITE_API_TARGET when the backend runs on a non-default host/port.
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:8010'

// Метка сборки — ОДНА на весь билд: она вписывается в бандл (`__APP_BUILD__`)
// и в `dist/build.json`, по которому открытая вкладка понимает, что на сервере
// новая сборка. Раньше метки считались дважды (в начале и в конце сборки), и
// если билд переходил через минуту, они расходились навсегда: подсказка
// «Доступна новая сборка» висела после каждого обновления страницы, хотя
// сборка та же (28.10.2026). Секунды — чтобы две сборки в одну минуту тоже
// различались.
const BUILD_STAMP = new Date().toLocaleString('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

export default defineConfig({
  // Shown in the status bar: lets anyone check at a glance whether the browser
  // is showing a freshly built interface or a cached one.
  define: {
    // Local time of the build machine: the status bar shows it as is.
    __APP_BUILD__: JSON.stringify(BUILD_STAMP),
  },
  plugins: [
    vue({ template: { transformAssetUrls } }),
    quasar(),
    // build.json рядом с index.html: приложение сверяет с ним свою метку и
    // подсказывает обновить страницу, если на сервере уже новая сборка
    // (иначе открытая вкладка молча живёт со старым интерфейсом).
    {
      name: 'scene-build-stamp',
      apply: 'build',
      closeBundle() {
        // Та же метка, что вписана в бандл: сравнение во вкладке идёт
        // строкой, поэтому источник обязан быть один.
        fs.writeFileSync(
          path.resolve(process.cwd(), 'dist/build.json'),
          JSON.stringify({ build: BUILD_STAMP }),
        )
      },
    },
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
