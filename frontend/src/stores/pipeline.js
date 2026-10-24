// Состояние идущего прогона «Обновление базы» — общее для шапки и грида.
//
// Раньше стадию и число совпадений опрашивал сам грид, поэтому текст был
// виден только на странице фото и показывался внизу, отдельно от кнопки,
// которая этот прогон запускает. Теперь опрос ведёт шапка (App.vue), а
// страница фото только реагирует на изменения: перечитывает грид, когда
// прогон закончился, и не делает второй запрос к тем же endpoint'ам.
//
// Число рядом со стадией — прогресс самой стадии («готово / всего») из строк
// прогона, тот же источник, что у кнопки «Обновление базы». Показываем его
// только на DINO/HYBRID: на остальных стадиях счётчик уже стоит в кнопке
// («Превью: 5/10», «Описаний: 5»), и дублировать его в шапке незачем.
import { defineStore } from 'pinia'

import { fetchCurrentPipeline, fetchRunActivity } from '../api/client'

// Интервал опроса. Пайплайн идёт десятками минут, чаще нет смысла.
export const PIPELINE_POLL_MS = 10_000

// Стадии, где число показывает строка в шапке (в кнопке его нет).
export const PROGRESS_STAGES = ['DINO', 'HYBRID']

export const usePipelineStore = defineStore('pipeline', {
  state: () => ({
    available: true,
    active: false,
    label: '',
    stage: '',
    done: null,
    total: null,
    // Растёт на каждом опросе: страницы подписываются на него, чтобы
    // выполнить свою часть синхронизации ровно один раз за тик.
    tick: 0,
    lastTickAt: 0,
    timer: null,
  }),

  getters: {
    // «идёт «Обновление базы» (стадия DINO) · 13686 / 20904»
    //
    // Нулевой счётчик не показываем: «0 / 20904» ничего не сообщает и только
    // занимает место в шапке.
    text(state) {
      if (!state.active) return ''

      const parts = []

      if (state.label) parts.push(state.label)

      if (state.done && state.total && PROGRESS_STAGES.includes(state.stage)) {
        parts.push(`${state.done} / ${state.total}`)
      }

      return parts.join(' · ')
    },
  },

  actions: {
    /**
     * Один опрос. `withMatched` — только для тех, у кого есть jobs:read:
     * у Гостя остаётся общее сообщение о стадии, без чисел.
     */
    async refresh({ withMatched = true } = {}) {
      try {
        const activity = await fetchRunActivity()

        if (!activity?.active) {
          this._clear()
        } else {
          this.active = true
          this.label = activity.message || 'идёт обновление базы'
          this.stage = activity.active?.stage || ''

          if (withMatched) {
            await this._loadProgress()
          } else {
            this.done = null
            this.total = null
          }
        }

        this.available = true
      } catch {
        // Прогона нет или endpoint недоступен — это не ошибка для шапки.
        this._clear()
      } finally {
        this.tick += 1
        this.lastTickAt = Date.now()
      }

      return this.active
    },

    async _loadProgress() {
      try {
        const data = await fetchCurrentPipeline()
        const run = data?.run || null
        const stage = (run?.stages || []).find(
          (item) => item.stage === run?.stage,
        )

        this.done = stage?.done_count ?? null
        this.total = stage?.total_count ?? null
      } catch {
        // Сводка вспомогательная: стадия показывается и без неё.
        this.done = null
        this.total = null
      }
    },

    _clear() {
      this.active = false
      this.label = ''
      this.stage = ''
      this.done = null
      this.total = null
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
