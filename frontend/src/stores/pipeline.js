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

import {
  fetchCurrentPipeline,
  fetchQwenStats,
  fetchRunActivity,
} from '../api/client'
import { createPoller } from '../composables/usePoller'

// Интервал опроса. Пайплайн идёт десятками минут, чаще нет смысла.
export const PIPELINE_POLL_MS = 10_000

// Стадии, где число показывает строка в шапке (в кнопке его нет).
export const PROGRESS_STAGES = ['DINO', 'HYBRID']

// Поллер живёт вне состояния стора: его нельзя делать реактивным.
let poller = null

export const usePipelineStore = defineStore('pipeline', {
  state: () => ({
    available: true,
    active: false,
    label: '',
    stage: '',
    done: null,
    total: null,
    // Распознавание (QWEN) идёт своей очередью и часто вне прогона
    // «Обновление базы», поэтому его прогресс показывается отдельно.
    qwen: null,
    // Растёт на каждом опросе: страницы подписываются на него, чтобы
    // выполнить свою часть синхронизации ровно один раз за тик.
    tick: 0,
    lastTickAt: 0,
  }),

  getters: {
    // «Распознавание 12375 / 16597» — обработано / всего в текущей выборке
    // (обычно это дозаполнение за период). Период — в подсказке.
    qwenText(state) {
      const qwen = state.qwen

      if (!qwen) return ''

      const total = qwen.batchTotal

      if (total) {
        return `Распознавание ${qwen.batchDone ?? 0} / ${total}`
      }

      if (!qwen.described) return ''

      return `Распознавание ${qwen.described}`
    },

    // Период выборки — в подсказке к строке.
    qwenTitle(state) {
      return state.qwen?.batchTitle || ''
    },

    qwenBusy(state) {
      return Boolean(state.qwen && (state.qwen.running || state.qwen.pending))
    },

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
        // Распознавание показываем независимо от прогона: своя очередь, свой
        // счётчик. У ролей без jobs:read чисел нет.
        if (withMatched) await this._loadQwen()
        else this.qwen = null

        this.tick += 1
        this.lastTickAt = Date.now()
      }

      return this.active
    },

    async _loadQwen() {
      try {
        const stats = await fetchQwenStats()
        const jobs = stats?.jobs || {}

        const batch = stats?.batch || null

        this.qwen = {
          described: stats?.processed ?? 0,
          remaining: stats?.remaining ?? 0,
          pending: jobs.pending ?? 0,
          running: jobs.running ?? 0,
          paused: jobs.paused ?? 0,
          batchTitle: batch?.title || '',
          batchTotal: batch?.total ?? 0,
          batchDone: batch?.done ?? 0,
          batchFailed: batch?.failed ?? 0,
        }
      } catch {
        // Статистика вспомогательная: без неё шапка просто не показывает QWEN.
        this.qwen = null
      }
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
      if (poller) return

      // Общий поллер: тики не накладываются, скрытая вкладка не опрашивается,
      // после stop ответы в полёте не трогают состояние.
      poller = createPoller(
        () => this.refresh(getOptions?.()),
        { intervalMs: PIPELINE_POLL_MS, immediate: true },
      )
      poller.start()
    },

    stop() {
      if (poller) {
        poller.stop()
        poller = null
      }

      // Состояние тоже сбрасываем: иначе после выхода из аккаунта в шапке
      // остаётся спиннер и текст чужого прогона.
      this._clear()
      this.qwen = null
    },
  },
})
