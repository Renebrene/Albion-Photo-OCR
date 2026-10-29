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

// Названия этапов в шапке — словами владельца: Инспекция → Превью →
// Сортировка (Дино, Гибрид) → Описание → Уточнение.
export const STAGE_LABELS = {
  INGEST: 'Инспекция',
  PREVIEW: 'Превью',
  DINO: 'Сортировка · Дино',
  HYBRID: 'Сортировка · Гибрид',
  QWEN: 'Описание',
  REFINE: 'Уточнение',
}

// Порядок тот же, что у конвейера: даже если этапы идут параллельно (Дино и
// Описание), строка читается сверху вниз по шагам.
const STAGE_ORDER = ['INGEST', 'PREVIEW', 'DINO', 'HYBRID', 'QWEN', 'REFINE']

// Сколько чисел показывать в строке: «сделано / всего» плюс отдельно
// «пропущено», если часть фото пропущена (битый файл, таймаут модели).
function stageText(entry) {
  const label = STAGE_LABELS[entry.key] || entry.key
  const parts = [label]

  if (entry.total > 0) parts.push(`${entry.processed} / ${entry.total}`)
  else if (entry.processed > 0) parts.push(`${entry.processed}`)

  // Пропущенное — в скобках: разделитель « · » отделяет этапы друг от друга,
  // и без скобок «… 20904 пропущено 2» читалось бы как один счётчик.
  if (entry.skipped > 0) parts.push(`(пропущено ${entry.skipped})`)

  return parts.join(' ')
}

// Поллер живёт вне состояния стора: его нельзя делать реактивным.
let poller = null

export const usePipelineStore = defineStore('pipeline', {
  state: () => ({
    available: true,
    active: false,
    label: '',
    stage: '',
    // Описание (QWEN) идёт своей очередью и часто вне прогона «Обновление
    // базы», поэтому его прогресс показывается отдельно — вместе с
    // «Уточнением», которое идёт хвостом за ним.
    qwen: null,
    // Строки стадий текущего прогона: отсюда берётся «сделано / всего» для
    // Инспекции, Превью и Сортировки.
    stages: [],
    // Растёт на каждом опросе: страницы подписываются на него, чтобы
    // выполнить свою часть синхронизации ровно один раз за тик.
    tick: 0,
    lastTickAt: 0,
  }),

  getters: {
    // Описание (QWEN) идёт своей очередью, поэтому считается отдельно от
    // стадий прогона: «сделано / всего» в текущей выборке, период — в подсказке.
    qwenBusy(state) {
      return Boolean(state.qwen && (state.qwen.running || state.qwen.pending))
    },

    // Период выборки — в подсказке к строке.
    qwenTitle(state) {
      return state.qwen?.batchTitle || ''
    },

    refineBusy(state) {
      return Boolean(state.qwen?.refine)
    },

    // Идёт хоть что-то: прогон, описание или уточнение. По этому признаку
    // шапка показывает мигающую точку, а кнопка — паузу.
    stageBusy(state) {
      return Boolean(state.active || this.qwenBusy || this.refineBusy)
    },

    // Этапы со счётчиками: прогон (Инспекция, Превью, Сортировка), Описание и
    // Уточнение — в одном списке и в порядке конвейера.
    //
    // Число — «обработано / всего», где обработанным считается и пропущенное:
    // битый файл или таймаут модели не должны держать счётчик незавершённым
    // (иначе он застревает, как «16594 / 16597»). Сколько именно пропущено,
    // видно рядом.
    liveStages(state) {
      const entries = []

      for (const row of state.stages || []) {
        // «Описание» показываем из строки прогона только когда прогон стоит
        // именно на этой стадии; в остальное время его счётчик берётся из
        // очереди — иначе числа путаются (владелец, 29.10.2026).
        if (!row?.stage || (row.stage === 'QWEN' && row.stage !== state.stage)) continue

        const done = Number(row.done_count || 0)
        const failed = Number(row.failed_count || 0)
        const total = Number(row.total_count || 0)
        const current = row.stage === state.stage

        // Завершённую стадию не показываем: место в шапке занимает то, что
        // идёт сейчас.
        if (!current && total > 0 && done + failed >= total) continue

        entries.push({
          key: row.stage,
          processed: done + failed,
          total,
          skipped: failed,
        })
      }

      // Описание: счётчик очереди важнее строки прогона — оно часто идёт вне
      // прогона и своей очередью.
      const qwen = state.qwen

      // Описание показываем, пока очередь работает: закончилось всё — строка
      // этапов пропадает, и в шапке остаётся только «База обновлена».
      // Постоянное «Описание 16268» висело бы там вечно и мешало читать
      // состояние («данные о процессах» уходят вместе с процессами).
      if (qwen && this.qwenBusy) {
        entries.push({
          key: 'QWEN',
          // Без выборки (разовая очередь) размер неизвестен: показываем
          // единственное честное число — сколько фото уже с описанием.
          processed: qwen.batchTotal
            ? (qwen.batchDone || 0) + (qwen.batchFailed || 0)
            : qwen.described || 0,
          total: qwen.batchTotal || 0,
          skipped: qwen.batchTotal ? qwen.batchFailed || 0 : 0,
        })
      }

      if (qwen?.refine) {
        entries.push({
          key: 'REFINE',
          processed: qwen.refine.done || 0,
          total: qwen.refine.total || 0,
          skipped: 0,
        })
      }

      return entries.sort(
        (left, right) =>
          STAGE_ORDER.indexOf(left.key) - STAGE_ORDER.indexOf(right.key),
      )
    },

    /**
     * Что идёт прямо сейчас — одна запись для шапки.
     *
     * Владелец (29.10.2026): в шапке нужен только текущий процесс и его
     * статус, а не весь конвейер. Порядок поиска: стадия, на которой стоит
     * прогон; иначе (стадия переключается или прогон не активен) — первый
     * незавершённый этап: это и есть текущая работа.
     */
    currentStage(state) {
      const stages = this.liveStages || []

      if (!stages.length) return null

      return stages.find((entry) => entry.key === state.stage) || stages[0]
    },

    // Строка шапки: «Превью 340 / 3000».
    stageLine(state) {
      const entry = this.currentStage

      return entry ? stageText(entry) : ''
    },

    // Полная картина этапов — для подсказки: она появляется по наведению,
    // поэтому подробности не занимают место в шапке.
    stageDetails(state) {
      return (this.liveStages || []).map(stageText)
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
            this.stages = []
          }
        }

        this.available = true
      } catch {
        // Прогона нет или endpoint недоступен — это не ошибка для шапки.
        this._clear()
      } finally {
        // Описание и Уточнение показываем независимо от прогона: своя
        // очередь, свой счётчик. У ролей без jobs:read чисел нет.
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
          // Активное «Уточнение» (хвост описаний) или null.
          refine: stats?.refine || null,
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

        // Строки всех стадий прогона: из них собирается строка шапки
        // («Превью 340 / 3000»). Раньше брали только текущую стадию, поэтому
        // в шапке не было ни Инспекции, ни Превью.
        this.stages = run?.stages || []

        if (run?.stage) this.stage = run.stage
      } catch {
        // Сводка вспомогательная: стадия показывается и без неё.
        this.stages = []
      }
    },

    _clear() {
      this.active = false
      this.label = ''
      this.stage = ''
      this.stages = []
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
