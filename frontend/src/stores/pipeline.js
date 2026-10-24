// Состояние идущего прогона «Обновление базы» — общее для шапки и грида.
//
// Раньше стадию и число совпадений опрашивал сам грид, поэтому текст был
// виден только на странице фото и показывался внизу, отдельно от кнопки,
// которая этот прогон запускает. Теперь опрос ведёт шапка (App.vue), а
// страница фото только реагирует на изменения: перечитывает грид, когда
// прогон закончился, и не делает второй запрос к тем же endpoint'ам.
import { defineStore } from 'pinia'

import { fetchRunActivity, fetchSortStatus } from '../api/client'

// Интервал опроса. Пайплайн идёт десятками минут, чаще нет смысла.
export const PIPELINE_POLL_MS = 10_000

export const usePipelineStore = defineStore('pipeline', {
  state: () => ({
    available: true,
    active: false,
    label: '',
    matched: null,
    total: null,
    // Растёт на каждом опросе: страницы подписываются на него, чтобы
    // выполнить свою часть синхронизации ровно один раз за тик.
    tick: 0,
    lastTickAt: 0,
    timer: null,
  }),

  getters: {
    // «идёт «Обновление базы» (стадия DINO) · 697 / 935»
    text(state) {
      if (!state.active) return ''

      const parts = []

      if (state.label) parts.push(state.label)

      // Нулевой счётчик не показываем: до HYBRID совпадений ещё нет, и
      // строка «0 / 935» только занимает место в шапке.
      if (state.matched && state.total) {
        parts.push(`${state.matched} / ${state.total}`)
      }

      return parts.join(' · ')
    },
  },

  actions: {
    /**
     * Один опрос. `withMatched` — только для тех, у кого есть jobs:read:
     * у Гостя остаётся общее сообщение о стадии.
     */
    async refresh({ withMatched = true } = {}) {
      try {
        const activity = await fetchRunActivity()

        if (!activity?.active) {
          this.active = false
          this.label = ''
          this.matched = null
          this.total = null
        } else {
          this.active = true
          this.label = activity.message || 'идёт обновление базы'

          if (withMatched) {
            try {
              const status = await fetchSortStatus()
              const stats = status?.current || status?.last?.stats || null
              this.matched = stats?.matched ?? null
              this.total = stats?.total ?? null
            } catch {
              // Сводка вспомогательная: стадия показывается и без неё.
            }
          } else {
            this.matched = null
            this.total = null
          }
        }

        this.available = true
      } catch {
        // Прогона нет или endpoint недоступен — это не ошибка для шапки.
        this.active = false
        this.label = ''
        this.matched = null
        this.total = null
      } finally {
        this.tick += 1
        this.lastTickAt = Date.now()
      }

      return this.active
    },

    start(getOptions) {
      if (this.timer) return

      this.refresh(getOptions?.())
      this.timer = window.setInterval(
        () => void this.refresh(getOptions?.()),
        PIPELINE_POLL_MS,
      )
    },

    stop() {
      if (!this.timer) return

      window.clearInterval(this.timer)
      this.timer = null
    },
  },
})
