// Component test: Settings.vue shows QWEN status and disables retry when
// there are no failed photos. Driven by a stubbed global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QSelect, QToggle, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import Settings from '../src/pages/Settings.vue'
import { useSessionStore } from '../src/stores/session'

// Подтверждения (пауза/зависшие/сброс) в тестах соглашаются сразу.
vi.mock('../src/composables/confirmDialog', () => ({
  confirmDialog: vi.fn(async () => true),
}))

// Quasar's Notify is a plugin singleton; outside a full app it may not be
// installed, so give it a no-op create() for the component to call.
Notify.create = vi.fn()

let stats
let enqueued
let qwenSettings
let updated
let rescanned
let scanned
let historyLog
let previewed
let pausedCalls
let resumedCalls
let stuckCalls
let resetCalls

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    if (method === 'GET' && path === '/api/v1/qwen/settings') {
      return jsonResponse(qwenSettings)
    }

    if (method === 'PUT' && path === '/api/v1/qwen/settings') {
      const body = JSON.parse(options.body)
      updated.push(body)
      // Сервер возвращает сохранённое состояние — как настоящий маршрут.
      qwenSettings = { ...qwenSettings, ...body }
      return jsonResponse(qwenSettings)
    }

    if (method === 'GET' && path === '/api/v1/qwen/models') {
      return jsonResponse({
        current: 'qwen3-vl:4b-instruct',
        provider: 'ollama',
        available: [{ name: 'qwen3-vl:4b-instruct', size: 3_000_000_000 }],
      })
    }

    if (method === 'GET' && path === '/api/v1/qwen/stats') {
      return jsonResponse(stats)
    }

    if (method === 'GET' && path === '/api/v1/qwen/history') {
      return jsonResponse(historyLog)
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen/rescan') {
      rescanned.push(JSON.parse(options.body))
      return jsonResponse({ jobs: 3, skipped: 0, photos: 3, archived: 1, model: 'qwen3-vl:4b-instruct', run_history_id: 7 }, 202)
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen/scan') {
      scanned.push(JSON.parse(options.body))
      return jsonResponse({ photos: 5, jobs: 4, skipped: 1, model: 'qwen3-vl:4b-instruct', run_history_id: 8 }, 202)
    }

    if (method === 'GET' && path === '/api/v1/qwen/addresses') {
      return jsonResponse({
        items: [{ address_id: 196, name: 'Нагибина 19 А', photos: 10 }],
      })
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen/preview') {
      previewed.push(JSON.parse(options.body))
      return jsonResponse({
        photos: 4,
        described: 1,
        missing: 3,
        addresses: 1,
        date_from: '2000-01-01',
        date_to: '2026-11-21',
        date_mode: 'capture',
      })
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen/pause') {
      pausedCalls.push({})
      return jsonResponse({ paused: 2 })
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen/resume') {
      resumedCalls.push({})
      return jsonResponse({ resumed: 3 })
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen/stuck') {
      stuckCalls.push(path)
      return jsonResponse({ cancelled: 2, job_ids: [1, 2], older_than_minutes: 30 })
    }

    if (method === 'POST' && path === '/api/v1/qwen/reset') {
      resetCalls.push(JSON.parse(options.body))
      return jsonResponse({
        deleted: { photo_qwen: 5, photo_qwen_history: 7 },
        cancelled_jobs: 1,
        report: '/tmp/report.json',
      })
    }

    if (method === 'GET' && path === '/api/v1/client-aliases') {
      return jsonResponse({ items: [] })
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen') {
      enqueued.push(JSON.parse(options.body))
      return jsonResponse({ jobs: 2, first_job_id: 1 }, 202)
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })
}

function mountSettings({ role = null } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)

  if (role) {
    const session = useSessionStore()
    session.authEnabled = true
    session.user = { name: 'tester', role }
  } else {
    // Без роли спека проверяет открытый режим (аутентификация выключена).
    useSessionStore().authEnabled = false
  }

  return mount(Settings, { global: { plugins: [Quasar, pinia] } })
}

beforeEach(() => {
  enqueued = []
  updated = []
  rescanned = []
  scanned = []
  historyLog = { items: [], text: '' }
  previewed = []
  pausedCalls = []
  resumedCalls = []
  stuckCalls = []
  resetCalls = []
  stats = { counts: { DONE: 256 }, failed_photo_ids: [] }
  qwenSettings = {
    provider: 'ollama',
    model: 'qwen3-vl:4b-instruct',
    base_url: '',
    api_key_set: false,
    api_key_hint: null,
    keep_alive: '10m',
    unload_on_idle: true,
    billboard_crop_enabled: true,
    billboard_crop_available: true,
    in_pipeline: true,
    prompt: 'Промпт полного кадра',
    default_prompt: 'Промпт полного кадра',
    crop_prompt: 'Промпт кропа',
    default_crop_prompt: 'Промпт кропа',
  }
  installFetch()
})

afterEach(() => {
  delete global.fetch
})

describe('Settings.vue', () => {
  it('переключает участие QWEN в «Обновлении базы»', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    expect(wrapper.text()).toContain('Запускать QWEN в «Обновлении базы»')

    const toggle = wrapper
      .findAllComponents(QToggle)
      .find((item) => String(item.props('label')).includes('Запускать QWEN'))
    expect(toggle).toBeTruthy()
    expect(toggle.props('modelValue')).toBe(true)

    await toggle.vm.$emit('update:modelValue', false)
    await flushPromises()

    expect(updated).toContainEqual({ in_pipeline: false })
    expect(wrapper.text()).toContain('выключено')
  })

  it('loads and immediately persists the optional billboard crop setting', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    expect(wrapper.text()).toContain('Использовать crop рекламного щита для QWEN')
    const toggle = wrapper.findAllComponents(QToggle)
      .find((item) => String(item.props('label')).includes('рекламного щита'))
    expect(toggle).toBeTruthy()
    expect(toggle.props('modelValue')).toBe(true)
    await toggle.vm.$emit('update:modelValue', false)
    await flushPromises()

    expect(updated).toContainEqual({ billboard_crop_enabled: false })
    expect(qwenSettings.billboard_crop_enabled).toBe(false)
    wrapper.unmount()
  })

  it('saves prompts from the separate fifth-column block', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    expect(wrapper.text()).toContain('Промпты QWEN')

    const areas = wrapper.findAll('textarea')
    expect(areas.length).toBeGreaterThanOrEqual(2)

    // Первое поле — промпт кропа; полный кадр остаётся встроенным.
    await areas[0].setValue('Новый промпт кропа')

    const save = wrapper
      .findAll('button')
      .find((item) => item.text().includes('Сохранить промпты'))

    expect(save).toBeTruthy()
    await save.trigger('click')
    await flushPromises()

    expect(updated).toContainEqual({
      prompt: '',
      crop_prompt: 'Новый промпт кропа',
    })
    wrapper.unmount()
  })

  it('renders the plain-text QWEN history log', async () => {
    historyLog = {
      items: [{ history_id: 1 }],
      text: '2026-10-18 | photo.jpg | модель: old → new | DONE\nклиент: Litres, бренд: Яндекс',
    }

    const wrapper = mountSettings()
    await flushPromises()

    const log = wrapper.find('.qwen-history-text')
    expect(log.exists()).toBe(true)
    expect(log.text()).toContain('клиент: Litres, бренд: Яндекс')
    wrapper.unmount()
  })

  it('запускает перезапись за выбранный период и адреса', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    wrapper.vm.runMode = 'overwrite'
    wrapper.vm.runPeriod = 'custom'
    wrapper.vm.runFrom = '2026-01-01'
    wrapper.vm.runTo = '2026-01-31'
    wrapper.vm.runDateMode = 'capture'
    wrapper.vm.selectedAddresses = [196]
    await flushPromises()

    await wrapper.vm.startQwenRun()
    await flushPromises()

    expect(rescanned).toEqual([{
      date_from: '2026-01-01',
      date_to: '2026-01-31',
      date_mode: 'capture',
      address_ids: [196],
    }])
    expect(scanned).toEqual([])
    wrapper.unmount()
  })

  it('дополняет отсутствующие описания пачкой до 5000', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    wrapper.vm.runMode = 'skip'
    wrapper.vm.runPeriod = 'custom'
    wrapper.vm.runFrom = '2026-02-01'
    wrapper.vm.runTo = '2026-02-28'
    wrapper.vm.runDateMode = 'capture'
    await flushPromises()

    await wrapper.vm.startQwenRun()
    await flushPromises()

    expect(scanned).toEqual([{
      date_from: '2026-02-01',
      date_to: '2026-02-28',
      date_mode: 'capture',
      address_ids: null,
      limit: 5000,
    }])
    expect(rescanned).toEqual([])
    wrapper.unmount()
  })

  it('считает, сколько фото попадёт в запуск', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    expect(previewed.length).toBeGreaterThan(0)
    expect(wrapper.text()).toContain('фото: 4')
    expect(wrapper.text()).toContain('будет дополнено: 3')
    wrapper.unmount()
  })

  it('одна кнопка: пустая очередь — «Запустить описание»', async () => {
    const wrapper = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    const labels = wrapper.findAll('button').map((button) => button.text())

    expect(labels.some((text) => text.includes('Запустить описание'))).toBe(true)
    expect(labels.some((text) => text.includes('Пауза'))).toBe(false)
    wrapper.unmount()
  })

  it('одна кнопка: при активной очереди — «Пауза»', async () => {
    stats = {
      counts: { DONE: 1 },
      queue: { PENDING: 2 },
      failed_photo_ids: [],
      timeline: { paused: false, pending: 2, running: 0, stuck: 0 },
    }

    const wrapper = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    const button = wrapper.findAll('button')
      .find((item) => item.text().includes('Пауза'))
    expect(button).toBeTruthy()
    await button.trigger('click')
    await flushPromises()

    expect(pausedCalls).toHaveLength(1)
    wrapper.unmount()
  })

  it('показывает «Продолжить» на паузе и возвращает очередь', async () => {
    stats = {
      counts: { DONE: 1 },
      failed_photo_ids: [],
      timeline: { paused: true, paused_count: 2, pending: 2, running: 0, stuck: 0 },
    }

    const wrapper = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    const resume = wrapper.findAll('button')
      .find((button) => button.text().includes('Продолжить'))
    expect(resume).toBeTruthy()
    await resume.trigger('click')
    await flushPromises()

    expect(resumedCalls).toHaveLength(1)
    wrapper.unmount()
  })

  it('предлагает снять зависшие задания', async () => {
    stats = {
      counts: { DONE: 1 },
      failed_photo_ids: [],
      timeline: { paused: false, pending: 0, running: 1, stuck: 1 },
    }

    const wrapper = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    const button = wrapper.findAll('button')
      .find((item) => item.text().includes('Снять зависшие'))
    expect(button).toBeTruthy()
    await button.trigger('click')
    await flushPromises()

    expect(stuckCalls).toHaveLength(1)
    wrapper.unmount()
  })

  it('жёсткий сброс доступен только администратору', async () => {
    const manager = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    expect(
      manager.findAll('button').some((item) =>
        item.text().includes('Жёсткий сброс'),
      ),
    ).toBe(false)
    manager.unmount()

    const admin = mountSettings({ role: 'Администратор' })
    await flushPromises()

    const button = admin.findAll('button')
      .find((item) => item.text().includes('Жёсткий сброс'))
    expect(button).toBeTruthy()
    await button.trigger('click')
    await flushPromises()

    expect(resetCalls).toEqual([{ confirm: true }])
    admin.unmount()
  })

  it('renders QWEN status counts', async () => {
    stats = { counts: { DONE: 255, FAILED: 1 }, failed_photo_ids: ['PH_bad'] }

    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('DONE: 255')
    expect(wrapper.text()).toContain('FAILED: 1')
  })

  it('shows the base size, what is left and the last runs', async () => {
    // Плитки «Метаданных QWEN» заменили дублирующую карточку «Статистика
    // описаний» (владелец, 20.11.2026): те же числа, но крупно и один раз.
    stats = {
      photos: 260,
      processed: 250,
      remaining: 10,
      successful: 247,
      done_empty: 3,
      counts: { DONE: 250, FAILED: 3, PENDING: 4 },
      // Очередь считается по заданиям (`queue`), а не по статусам строк:
      // убитый воркер оставляет RUNNING без заданий (29.10.2026).
      queue: { PENDING: 4 },
      runs: [
        { source: 'manual', jobs: 12, last_finished_at: '2026-10-16T09:05:00', failed: 1 },
        { source: 'pipeline', jobs: 260, last_finished_at: '2026-10-15T22:10:00', failed: 0 },
      ],
      failed_photo_ids: [],
    }

    const wrapper = mountSettings()
    await flushPromises()

    const text = wrapper.text()
    // Плитки: непересекающиеся числа базы. 247 описаний + 3 пустых ответа
    // = DONE 250; «без описания» — remaining; очередь и FAILED — отдельно.
    expect(wrapper.vm.qwenMetrics).toEqual([
      { label: 'Фото в базе', value: 260, tone: '' },
      { label: 'С описанием', value: 247, tone: 'positive' },
      { label: 'Пустой ответ', value: 3, tone: '' },
      { label: 'Без описания', value: 10, tone: '' },
      { label: 'В очереди', value: 4, tone: 'info' },
      { label: 'С ошибкой', value: 3, tone: 'negative' },
    ])
    // Полоса покрытия: 250 из 260 = 0.96…
    expect(wrapper.vm.qwenCoverage).toBeCloseTo(250 / 260, 5)
    // Триггеры подписаны по-русски, дата — без «T».
    expect(text).toContain('ручной')
    expect(text).toContain('2026-10-16 09:05')
    expect(text).toContain('внеочередной')
    expect(text).toContain('2026-10-15 22:10')

    // Очередь непустая — карточка сама себя обновляет; размонтирование
    // должно остановить таймер, иначе он переживёт тест.
    expect(text).toContain('обновляется автоматически')
    wrapper.unmount()
  })

  it('shows the saved model and persists a newly chosen one', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('Сохранено: qwen3-vl:4b-instruct')

    const modelSelect = wrapper
      .findAllComponents(QSelect)
      .find((item) => String(item.props('label')).includes('Модель'))

    await modelSelect.vm.$emit('update:model-value', 'ling-3.0-flash-vl')
    await flushPromises()

    // Модель запоминается сразу при выборе, без кнопки «Сохранить».
    expect(updated).toContainEqual({ model: 'ling-3.0-flash-vl' })
    expect(wrapper.text()).toContain('Сохранено: ling-3.0-flash-vl')
  })

  it('keeps the billboard crop setting read-only for a Manager', async () => {
    const wrapper = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    const toggle = wrapper.findAllComponents(QToggle)
      .find((item) => String(item.props('label')).includes('рекламного щита'))
    expect(toggle).toBeTruthy()
    expect(toggle.props('disable')).toBe(true)
    wrapper.unmount()
  })

  it('keeps provider credentials read-only for a Manager', async () => {
    const wrapper = mountSettings({ role: 'Менеджер' })
    await flushPromises()

    expect(wrapper.text()).toContain('только Администратор')
    const providerSelect = wrapper
      .findAllComponents(QSelect)
      .find((item) => String(item.props('label')).includes('Провайдер'))
    expect(providerSelect.props('disable')).toBe(true)

    const save = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Сохранить')
    expect(save).toBeUndefined()

    // Operational unload is still available to the working role.
    expect(wrapper.text()).toContain('Выгрузить из памяти')
  })

  it('не показывает повтор упавших, когда их нет', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    const retry = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Повторить упавшие'))

    expect(retry).toBeUndefined()
  })

  it('warns when the cloud provider is selected', async () => {
    qwenSettings = {
      ...qwenSettings,
      provider: 'openai',
      base_url: 'https://api.example.com/v1',
      api_key_set: true,
      api_key_hint: '…1234',
    }

    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('Облачный провайдер')
  })

  it('saves provider, keep-alive and idle-unload settings', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    const saveBtn = wrapper
      .findAll('button')
      .find((b) => b.text() === 'Сохранить')
    expect(saveBtn).toBeTruthy()

    await saveBtn.trigger('click')
    await flushPromises()

    expect(updated).toHaveLength(1)
    expect(updated[0]).toMatchObject({
      provider: 'ollama',
      keep_alive: '10m',
      unload_on_idle: true,
    })
    // api_key is not sent when untouched.
    expect(updated[0].api_key).toBeUndefined()
  })

  it('enqueues failed photos when retry is clicked', async () => {
    stats = { counts: { FAILED: 2 }, failed_photo_ids: ['PH_a', 'PH_b'] }

    const wrapper = mountSettings()
    await flushPromises()

    const retry = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Повторить упавшие'))
    expect(retry.text()).toContain('(2)')

    await retry.trigger('click')
    await flushPromises()

    expect(enqueued).toEqual([{ photo_ids: null, only_failed: true }])
  })
})
