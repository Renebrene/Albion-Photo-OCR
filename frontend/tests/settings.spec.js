// Component test: Settings.vue shows QWEN status and disables retry when
// there are no failed photos. Driven by a stubbed global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QSelect, QToggle, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import Settings from '../src/pages/Settings.vue'
import { useSessionStore } from '../src/stores/session'

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
  }

  return mount(Settings, { global: { plugins: [Quasar, pinia] } })
}

beforeEach(() => {
  enqueued = []
  updated = []
  rescanned = []
  scanned = []
  historyLog = { items: [], text: '' }
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

  it('confirms a destructive QWEN rescan for an explicit period', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    const openButton = wrapper.findAll('button')
      .find((button) => button.text().includes('Пересканировать'))
    expect(openButton).toBeTruthy()
    await openButton.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('ДЕСТРУКТИВНО')
    wrapper.vm.rescanFrom = '2026-01-01'
    wrapper.vm.rescanTo = '2026-01-31'
    wrapper.vm.rescanDateMode = 'capture'
    await flushPromises()
    await wrapper.vm.runRescan()
    await flushPromises()

    expect(rescanned).toEqual([{
      date_from: '2026-01-01',
      date_to: '2026-01-31',
      date_mode: 'capture',
    }])
    expect(scanned).toEqual([])
    wrapper.unmount()
  })

  it('enqueues a non-destructive catch-up for a period', async () => {
    const wrapper = mountSettings({ role: 'Администратор' })
    await flushPromises()

    const openButton = wrapper.findAll('button')
      .find((button) => button.text().includes('Дозаполнить за период'))
    expect(openButton).toBeTruthy()
    await openButton.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('только фото без успешного описания')
    wrapper.vm.rescanFrom = '2026-02-01'
    wrapper.vm.rescanTo = '2026-02-28'
    wrapper.vm.rescanDateMode = 'capture'
    await flushPromises()
    await wrapper.vm.runRescan()
    await flushPromises()

    expect(scanned).toEqual([{
      date_from: '2026-02-01',
      date_to: '2026-02-28',
      date_mode: 'capture',
    }])
    expect(rescanned).toEqual([])
    wrapper.unmount()
  })

  it('renders QWEN status counts', async () => {
    stats = { counts: { DONE: 255, FAILED: 1 }, failed_photo_ids: ['PH_bad'] }

    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('DONE: 255')
    expect(wrapper.text()).toContain('FAILED: 1')
  })

  it('shows the base size, what is left and the last runs', async () => {
    stats = {
      photos: 260,
      processed: 250,
      remaining: 10,
      counts: { DONE: 250, FAILED: 3, PENDING: 4 },
      runs: [
        { source: 'manual', jobs: 12, last_finished_at: '2026-10-16T09:05:00', failed: 1 },
        { source: 'pipeline', jobs: 260, last_finished_at: '2026-10-15T22:10:00', failed: 0 },
      ],
      failed_photo_ids: [],
    }

    const wrapper = mountSettings()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('ВСЕГО ФОТО: 260')
    expect(text).toContain('РАСПОЗНАНО: 250')
    expect(text).toContain('осталось 10')
    expect(text).toContain('В ОЧЕРЕДИ: 4')
    // Триггеры подписаны по-русски, дата — без «T».
    expect(text).toContain('ручной: 2026-10-16 09:05')
    expect(text).toContain('внеочередной: 2026-10-15 22:10')

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

  it('disables retry when there are no failed photos', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    const retry = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Повторить для упавших'))

    expect(retry).toBeTruthy()
    expect(retry.attributes('disabled')).toBeDefined()
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
      .find((b) => b.text().includes('Повторить для упавших'))
    expect(retry.text()).toContain('(2)')

    await retry.trigger('click')
    await flushPromises()

    expect(enqueued).toEqual([{ photo_ids: null, only_failed: true }])
  })
})
