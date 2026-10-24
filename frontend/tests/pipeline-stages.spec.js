// Этапы со счётчиками в шапке: Инспекция → Превью → Сортировка (Дино,
// Гибрид) → Описание → Уточнение. Описание и Уточнение идут своими очередями
// и часто вне прогона, поэтому собираются из /v1/qwen/stats.
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePipelineStore } from '../src/stores/pipeline'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

let activity
let pipeline
let qwenStats

function installFetch() {
  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]

    if (path.endsWith('/v1/runs/activity')) return json(activity)
    if (path.endsWith('/v1/pipeline/current')) return json(pipeline)
    if (path.endsWith('/v1/qwen/stats')) return json(qwenStats)

    return json({ detail: `no route for ${path}` }, 500)
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  activity = { active: null, message: '' }
  pipeline = { run: null }
  qwenStats = { jobs: {}, batch: null, refine: null, processed: 0, remaining: 0 }
  installFetch()
})

describe('строка этапов в шапке', () => {
  it('показывает этап прогона с размером и убирает завершённые', async () => {
    activity = { active: { kind: 'pipeline', run_id: 1, stage: 'PREVIEW' }, message: 'идёт обновление' }
    pipeline = {
      run: {
        run_id: 1,
        status: 'RUNNING',
        stage: 'PREVIEW',
        stages: [
          { stage: 'INGEST', done_count: 300, failed_count: 0, total_count: 300 },
          { stage: 'PREVIEW', done_count: 340, failed_count: 0, total_count: 3000 },
        ],
      },
    }

    const store = usePipelineStore()
    await store.refresh()

    // Инспекция завершена — её в строке нет, место занимает текущий этап.
    expect(store.stageLine).toBe('Превью 340 / 3000')
    expect(store.stageBusy).toBe(true)
  })

  it('держит порядок конвейера, когда Дино и Описание идут параллельно', async () => {
    activity = { active: { kind: 'pipeline', run_id: 1, stage: 'DINO' }, message: 'идёт обновление' }
    pipeline = {
      run: {
        run_id: 1,
        status: 'RUNNING',
        stage: 'DINO',
        stages: [
          { stage: 'DINO', done_count: 13686, failed_count: 2, total_count: 20904 },
        ],
      },
    }
    qwenStats = {
      jobs: { pending: 0, running: 1, paused: 0 },
      batch: { run_id: 7, title: '01.08–31.10', status: 'RUNNING', total: 16597, done: 16594, failed: 2 },
      refine: null,
      processed: 16594,
      remaining: 3,
    }

    const store = usePipelineStore()
    await store.refresh()

    expect(store.stageLine).toBe(
      'Сортировка · Дино 13688 / 20904 (пропущено 2) · Описание 16596 / 16597 (пропущено 2)',
    )
    expect(store.qwenTitle).toBe('01.08–31.10')
  })

  it('показывает Описание и Уточнение, когда прогона нет', async () => {
    qwenStats = {
      jobs: { pending: 4, running: 0, paused: 0 },
      batch: { run_id: 7, title: '', status: 'RUNNING', total: 500, done: 120, failed: 0 },
      refine: { job_id: 9, status: 'RUNNING', done: 40, total: 480 },
      processed: 120,
      remaining: 380,
    }

    const store = usePipelineStore()
    await store.refresh()

    expect(store.active).toBe(false)
    expect(store.stageLine).toBe('Описание 120 / 500 · Уточнение 40 / 480')
    expect(store.stageBusy).toBe(true)
  })

  it('молчит, когда ничего не идёт', async () => {
    const store = usePipelineStore()
    await store.refresh()

    expect(store.stageLine).toBe('')
    expect(store.stageBusy).toBe(false)
  })

  it('без выборки описаний показывает только пройденное число', async () => {
    qwenStats = {
      jobs: { pending: 0, running: 1, paused: 0 },
      batch: null,
      refine: null,
      processed: 16268,
      remaining: 0,
    }

    const store = usePipelineStore()
    await store.refresh()

    // Партии нет (разовая очередь) — размер неизвестен: показываем, сколько
    // фото уже с описанием.
    expect(store.stageLine).toBe('Описание 16268')
  })
})
