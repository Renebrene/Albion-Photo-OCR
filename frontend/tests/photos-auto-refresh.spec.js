// Грид показывает только распознанные фото, поэтому во время HYBRID он должен
// перечитываться сам, когда меняется размер выборки. Стадию и число
// совпадений опрашивает шапка (stores/pipeline.js) — здесь проверяется,
// что тик этого опроса доходит до грида.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import { usePipelineStore } from '../src/stores/pipeline'

Notify.create = vi.fn()

let photoTotal = 2
// Этапы со счётчиками в шапке: «готово / всего» берётся из строк стадии
// (/v1/pipeline/current). Проверяем и её, и нулевой случай.
let stageDone = 3
let stageTotal = 10

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const photo = {
  photo_id: 'PH_' + 'a'.repeat(24),
  filename: 'photo.jpg',
  width: 100,
  height: 100,
  container_format: 'JPEG',
  address: '78_v33',
  simple_address: 'Комарова 13',
  client: 'Клиент А',
  brand: 'Бренд Б',
  source_directory: 'test',
  taken_at: '2025-07-17 11:43:19',
  size_bytes: 4194304,
}

function installFetch() {
  global.fetch = vi.fn(async (url) => {
    const parsed = new URL(String(url), 'http://localhost')
    const path = parsed.pathname

    if (path.endsWith('/v1/photos')) {
      // Дешёвая проверка размера выборки запрашивает одну строку.
      if (parsed.searchParams.get('limit') === '1') {
        return json({ items: [], next_cursor: null, total: photoTotal })
      }

      return json({ items: [photo], next_cursor: null, total: photoTotal })
    }

    if (path.endsWith('/v1/runs/activity')) {
      return json({
        active: { kind: 'pipeline', run_id: 1, stage: 'HYBRID' },
        message: 'идёт «Обновление базы» (стадия HYBRID)',
      })
    }

    if (path.endsWith('/v1/pipeline/current')) {
      return json({
        run: {
          run_id: 1,
          status: 'RUNNING',
          stage: 'HYBRID',
          stages: [
            { stage: 'DINO', done_count: 10, failed_count: 0, total_count: 10 },
            {
              stage: 'HYBRID',
              done_count: stageDone,
              failed_count: 0,
              total_count: stageTotal,
            },
          ],
        },
      })
    }

    if (path.endsWith('/v1/qwen/settings')) return json({ models: {} })

    return json({ items: [] })
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  photoTotal = 2
  stageDone = 3
  stageTotal = 10
  Notify.create = vi.fn()
  setActivePinia(createPinia())
  installFetch()
})

afterEach(() => {
  vi.useRealTimers()
  delete global.fetch
  vi.restoreAllMocks()
})

// QPage рендерится только внутри QLayout/QPageContainer — оборачиваем так же,
// как App.vue. Render-функция: runtime-компилятор шаблонов в тестах не подключён.
const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

async function mountGrid() {
  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(Host, {
    global: { plugins: [Quasar, pinia] },
  })
  await flushPromises()

  // Тот же тик, что делает шапка по таймеру.
  const pipeline = usePipelineStore(pinia)

  return {
    wrapper,
    async tick() {
      await pipeline.refresh()
      await flushPromises()
    },
    pipeline,
  }
}

describe('грид следит за HYBRID', () => {
  it('перечитывает выборку и сообщает о новых распознанных фото', async () => {
    const { wrapper, tick } = await mountGrid()

    expect(wrapper.text()).toContain('За период 2 фото')

    // HYBRID доработал ещё одно фото: размер выборки вырос.
    photoTotal = 3
    await tick()

    expect(wrapper.text()).toContain('За период 3 фото')
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Распознано новых фото: +1' }),
    )
    wrapper.unmount()
  })

  it('не перечитывает грид, пока открыт просмотрщик', async () => {
    const { wrapper, tick } = await mountGrid()

    await wrapper.find('.photo-card .auth-image-root').trigger('click')
    await flushPromises()

    // HYBRID доработал фото, но просмотрщик открыт: страницы не сбрасываем.
    photoTotal = 3
    await tick()

    expect(wrapper.text()).toContain('За период 2 фото')
    expect(Notify.create).not.toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Распознано новых фото: +1' }),
    )
    wrapper.unmount()
  })

  it('стадия и число совпадений собираются общим store для шапки', async () => {
    const { wrapper, tick, pipeline } = await mountGrid()

    await tick()

    expect(pipeline.active).toBe(true)
    expect(pipeline.stageLine).toContain('Сортировка · Гибрид')
    expect(pipeline.stageLine).toContain('3 / 10')

    // В гриде этой строки больше нет: её место — шапка рядом с кнопкой.
    expect(wrapper.text()).not.toContain('3 / 10')
    wrapper.unmount()
  })

  it('стадия с нулевым прогрессом показывает свой размер', async () => {
    const { tick, pipeline } = await mountGrid()

    stageDone = 0
    stageTotal = 20904
    await tick()

    expect(pipeline.active).toBe(true)
    // Ноль в начале стадии — не «нет данных»: он говорит, какой этап идёт и
    // сколько в нём всего. Раньше строка показывала «Совпадений: 0» без
    // размера, и это выглядело как пустой счётчик.
    expect(pipeline.stageLine).toContain('Сортировка · Гибрид 0 / 20904')
  })
})
