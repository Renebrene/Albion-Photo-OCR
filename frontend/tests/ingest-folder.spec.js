// Проверка папки INGEST: фото + видео, расширения, итоговый баннер, лог
// ошибок, выбор папки на сервере и запуск сканирования.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QSelect, Quasar } from 'quasar'

import IngestFolder from '../src/components/IngestFolder.vue'

// Очистка превью спрашивает подтверждение через Dialog: в тестах плагин не
// регистрируется, поэтому согласие подменяется.
vi.mock('../src/composables/confirmDialog', () => ({
  confirmDialog: vi.fn(async () => true),
}))

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const folderState = {
  configured: '/photos',
  exists: true,
  photos: 2,
  videos: 0,
  bytes: 30,
  photo_bytes: 30,
  video_bytes: 0,
  extensions: { '.jpg': 2 },
  problem_count: 0,
  problems: [],
  preliminary: true,
  truncated: false,
  timed_out: false,
}

const scanWithErrors = {
  ...folderState,
  path: '/photos',
  photos: 3,
  videos: 2,
  media_files: 5,
  bytes: 100,
  photo_bytes: 40,
  video_bytes: 60,
  extensions: { '.jpg': 3, '.mov': 1, '.mp4': 1 },
  problem_count: 1,
  problems: [{ filename: 'empty.mp4', reason: 'файл пуст' }],
}

const healthyInventory = {
  previews: {
    photos: 2,
    files: 4,
    bytes: 2048,
    small: { files: 2, bytes: 512 },
    middle: { files: 2, bytes: 1536 },
  },
  orphans: {
    count: 0,
    bytes: 0,
    purgeable: 0,
    purgeable_bytes: 0,
    reasons: {},
    samples: [],
  },
}

function installFetch({
  scan = scanWithErrors,
  previews = null,
  job = null,
  inventory = healthyInventory,
  purge = { photos: 2, deleted_files: 4, freed_bytes: 300, skipped: 0 },
} = {}) {
  const calls = []

  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url)
    calls.push({
      path,
      method: options.method || 'GET',
      body: options.body ? JSON.parse(options.body) : null,
    })

    if (path.includes('/v1/previews/inventory')) return json(inventory)
    if (path.includes('/v1/previews/orphans/purge')) return json(purge)
    if (path.includes('/v1/previews/backfill')) {
      return json(previews || { selected: 3, queued: 3, already_active: 0 })
    }
    if (path.includes('/v1/jobs/42')) {
      return json(job || { id: 42, status: 'RUNNING', progress: {}, result: null })
    }
    if (path.includes('/v1/ingest/scan')) return json(scan)
    if (path.includes('/v1/ingest/run')) return json({ job_id: 42 })
    if (path.includes('/v1/fingerprints/browse')) {
      return json({
        path: '/photos',
        parent: null,
        dirs: [{ name: 'sub', path: '/photos/sub', photos: 3 }],
        photos: 2,
      })
    }
    if (options.method === 'PUT') return json(folderState)
    return json(folderState)
  })

  return calls
}

function mountFolder() {
  return mount(IngestFolder, {
    attachTo: document.body,
    global: { plugins: [Quasar] },
  })
}

async function clickButton(wrapper, label) {
  const button = wrapper
    .findAll('button')
    .find((item) => item.text().includes(label))

  if (button) {
    await button.trigger('click')
    await flushPromises()
    return
  }

  // Кнопки в q-dialog рендерятся порталом в document.body.
  const domButton = [...document.querySelectorAll('button')].find((item) =>
    (item.textContent || '').includes(label),
  )

  expect(domButton, `кнопка «${label}»`).toBeTruthy()
  domButton.click()
  await flushPromises()
}

beforeEach(() => vi.restoreAllMocks())
afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

describe('папка INGEST', () => {
  it('показывает статистику справа и баннер с ошибками после проверки', async () => {
    installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Проверить')

    const text = wrapper.text()
    expect(text).toContain('Статистика папки')
    expect(text).toContain('Фото')
    expect(text).toContain('3')
    expect(text).toContain('Видео')
    expect(text).toContain('.mp4: 1')
    expect(text).toContain('ОК, но есть ошибки: 1')
    expect(text).toContain('«Сортировка»')

    // Лог ошибок открывается отдельным окном.
    await clickButton(wrapper, 'Лог ошибок')
    expect(document.body.textContent).toContain('empty.mp4')
    expect(document.body.textContent).toContain('файл пуст')
  })

  it('показывает «Всё ОК», когда ошибок нет', async () => {
    installFetch({ scan: { ...folderState, photos: 5, videos: 1 } })
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Проверить')

    expect(wrapper.text()).toContain('Всё ОК')
    expect(wrapper.text()).toContain('Переходите к этапу «Сортировка»')
  })

  it('сканирование активно сразу после выбора пути', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    const input = wrapper.find('input')
    await input.setValue('/another-folder')
    await flushPromises()

    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run).toBeTruthy()
  })

  it('показывает итог задания: найдено, новых, уже в базе', async () => {
    // «Зарегистрировано 0» без пояснения выглядит как «инспектор не увидел
    // файлы»; итог показывает, что они уже были в базе (владелец, 21.11.2026).
    const calls = installFetch({
      job: {
        id: 42,
        status: 'DONE',
        progress: {},
        result: {
          discovered: 426,
          registered: 0,
          existing: 426,
          counters: { VALID: 426, INVALID: 0, SKIPPED: 0 },
          videos: { registered: 0, existing: 21, removed_missing: 3 },
        },
      },
    })
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Инспектировать')
    await flushPromises()
    await flushPromises()

    expect(calls.some((call) => call.path.includes('/v1/jobs/42'))).toBe(true)

    const text = wrapper.text()
    expect(text).toContain('готово')
    expect(text).toContain('файлов найдено')
    expect(text).toContain('426')
    expect(text).toContain('уже в базе')
    expect(text).toContain('видео уже в базе')
    expect(text).toContain('записей видео без файла удалено')
  })

  it('выбирает папку во встроенном браузере сервера', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Выбрать на сервере')

    expect(document.body.textContent).toContain('/photos/sub')
    expect(calls.some((call) => call.path.includes('/v1/fingerprints/browse'))).toBe(true)

    await clickButton(wrapper, 'Выбрать эту папку')
    expect(
      calls.some(
        (call) => call.path.includes('/v1/ingest/folder') && call.method === 'PUT',
      ),
    ).toBe(true)
  })
})

// ---- глубина сканирования по времени -------------------------------------
// Тот же выбор «Дата» + «Период…», что и в фильтре Грида; без периода
// запрос уходит ровно таким же, как до появления глубины.

function selectByLabel(wrapper, label) {
  return wrapper
    .findAllComponents(QSelect)
    .find((item) => String(item.props('label')) === label)
}

describe('глубина сканирования по времени', () => {
  it('без периода не отправляет границы и не считает split', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body).toEqual({ path: '/photos' })
  })

  it('«Сегодня» отправляет границы по локальной дате', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'today')
    await flushPromises()
    await clickButton(wrapper, 'Инспектировать')

    const today = new Date()
    const pad = (value) => String(value).padStart(2, '0')
    const expected = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body).toEqual({
      path: '/photos',
      date_from: expected,
      date_to: expected,
      date_mode: 'upload',
    })
  })

  it('режим «Дата съёмки» доезжает до сервера', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Дата').vm.$emit('update:model-value', 'capture')
    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'week')
    await flushPromises()
    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body.date_mode).toBe('capture')
    expect(run.body.date_from).toBeTruthy()
  })

  it('«Период…» без дат ничего не ограничивает', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'custom')
    await flushPromises()
    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body).toEqual({ path: '/photos' })
  })

  it('показывает, сколько фото и видео появилось после последней инспекции', async () => {
    installFetch({
      scan: {
        ...scanWithErrors,
        last_inspection_at: '2026-11-21T01:26:00',
        new_photos: 12,
        new_videos: 2,
        new_bytes: 4096,
      },
    })
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Проверить')

    const text = wrapper.text()
    expect(text).toContain('Новых после инспекции')
    expect(text).toContain('21.11 01:26')
    expect(text).toContain('12')
    expect(text).toContain('2')
    expect(
      Notify.create.mock.calls.some((call) =>
        String(call[0]?.message || '').includes('новых после инспекции'),
      ),
    ).toBe(true)
  })

  it('«Проверить» с периодом показывает счёт вне периода', async () => {
    installFetch({
      scan: {
        ...scanWithErrors,
        excluded_by_period: 4,
        in_period: 1,
        period_applied: true,
      },
    })
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'today')
    await flushPromises()
    await clickButton(wrapper, 'Проверить')

    expect(wrapper.text()).toContain('В периоде')
    expect(wrapper.text()).toContain('Вне периода')
    expect(wrapper.text()).toContain('4')
  })
})

// ---- пересоздание превью ---------------------------------------------------

describe('пересоздание превью', () => {
  it('ставит задания и сообщает результат', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Пересоздать превью')

    const call = calls.find((item) => item.path.includes('/v1/previews/backfill'))
    expect(call).toBeTruthy()
    expect(call.method).toBe('POST')
    expect(call.body).toEqual({})
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining('заданий: 3') }),
    )
  })

  it('предупреждает про фото с недоступным оригиналом', async () => {
    installFetch({
      previews: { selected: 2, queued: 2, already_active: 0, originals_missing: 5 },
    })
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Пересоздать превью')

    const notice = Notify.create.mock.calls.at(-1)[0]
    expect(notice.type).toBe('warning')
    expect(notice.message).toContain('Оригинал недоступен у 5 фото')
  })
})

// ---- сводка превью и «сироты» ----------------------------------------------

describe('сводка превью', () => {
  it('показывает число фото и вес файлов', async () => {
    installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Превью: 2 фото')
    expect(text).toContain('2.0 КБ')
    expect(text).toContain('512 Б')
    expect(text).toContain('Превью без оригиналов не найдено')
  })

  it('предлагает очистить превью без оригиналов', async () => {
    const calls = installFetch({
      inventory: {
        previews: healthyInventory.previews,
        orphans: {
          count: 3,
          bytes: 900,
          purgeable: 2,
          purgeable_bytes: 600,
          reasons: { file_missing: 2, directory_missing: 1 },
          samples: [],
        },
      },
      purge: { photos: 2, deleted_files: 4, freed_bytes: 600, skipped: 1 },
    })
    const wrapper = mountFolder()
    await flushPromises()

    expect(wrapper.text()).toContain('Превью без оригиналов: 3')
    expect(wrapper.text()).toContain('Можно удалить 2')

    await clickButton(wrapper, 'Очистить')
    await flushPromises()

    const call = calls.find((item) => item.path.includes('/v1/previews/orphans/purge'))
    expect(call).toBeTruthy()
    expect(call.method).toBe('POST')
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining('Удалено превью: 2') }),
    )
  })

  it('без безопасных случаев кнопку не показывает, а объясняет причину', async () => {
    installFetch({
      inventory: {
        previews: healthyInventory.previews,
        orphans: {
          count: 2,
          bytes: 300,
          purgeable: 0,
          purgeable_bytes: 0,
          reasons: { root_unavailable: 2 },
          samples: [],
        },
      },
    })
    const wrapper = mountFolder()
    await flushPromises()

    expect(wrapper.text()).toContain('Удаление недоступно')
    expect(wrapper.text()).toContain('том не подключён: 2')
    expect(
      wrapper.findAll('button').some((button) => button.text().includes('Очистить')),
    ).toBe(false)
  })
})
