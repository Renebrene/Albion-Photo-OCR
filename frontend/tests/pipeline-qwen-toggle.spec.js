// Выключатель QWEN в окне «Обновление базы» — та же настройка, что в
// техразделе (владелец, 29.10.2026): один флаг in_pipeline на всю систему,
// иначе выключенное описание запускалось снова вместе с прогоном.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import PipelineUpdateButton from '../src/components/PipelineUpdateButton.vue'

Notify.create = vi.fn()

let calls
let settings

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url).split('?')[0]
    const method = (options.method || 'GET').toUpperCase()

    calls.push({ path, method, body: options.body })

    if (path.endsWith('/v1/pipeline/current')) {
      return json({ run: { run_id: 7, status: 'STOPPED', stage: 'DINO', manifest: {}, stages: [] } })
    }

    if (path.endsWith('/v1/qwen/settings')) {
      if (method === 'PUT') {
        settings = { ...settings, ...JSON.parse(options.body) }
        return json(settings)
      }

      return json(settings)
    }

    if (path.endsWith('/v1/pipeline/start')) return json({ run_id: 8, status: 'RUNNING' })
    if (path.endsWith('/v1/pipeline/7/resume')) return json({ run_id: 7, status: 'RUNNING' })

    return json({})
  })
}

async function openDialog(props = {}) {
  const wrapper = mount(PipelineUpdateButton, {
    global: { plugins: [Quasar] },
    props: { canRun: true, ...props },
    attachTo: document.body,
  })
  await flushPromises()

  const more = wrapper.findAll('button').find((item) => item.html().includes('expand_more'))
  await more.trigger('click')
  await flushPromises()

  return wrapper
}

function bodyButton(label) {
  return Array.from(document.body.querySelectorAll('button')).find((button) =>
    button.textContent.includes(label),
  )
}

function toggle() {
  return document.body.querySelector('.q-toggle')
}

function toggleChecked() {
  return toggle()?.getAttribute('aria-checked') === 'true'
}

function startBody() {
  const call = calls.filter((item) => item.path.endsWith('/v1/pipeline/start')).at(-1)

  return call ? JSON.parse(call.body) : null
}

beforeEach(() => {
  calls = []
  settings = { in_pipeline: true }
  Notify.create = vi.fn()
  installFetch()
})

afterEach(() => {
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('выключатель QWEN в окне запуска', () => {
  it('показывает текущую настройку и уважает её при запуске', async () => {
    settings = { in_pipeline: false }
    const wrapper = await openDialog()

    // Настройка выключена — выключатель в окне тоже.
    expect(toggleChecked()).toBe(false)
    expect(document.body.textContent).toContain('Описание выключено')

    await bodyButton('Начать заново').click()
    await flushPromises()

    expect(startBody().skip_qwen).toBe(true)
    wrapper.unmount()
  })

  it('Администратор меняет общую настройку прямо из окна', async () => {
    settings = { in_pipeline: false }
    const wrapper = await openDialog({ canWriteSettings: true })

    toggle().click()
    await flushPromises()

    // Это тот же флаг, что в техразделе: сохранён на сервере.
    const put = calls.find(
      (item) => item.method === 'PUT' && item.path.endsWith('/v1/qwen/settings'),
    )
    expect(JSON.parse(put.body)).toEqual({ in_pipeline: true })
    expect(toggleChecked()).toBe(true)

    await bodyButton('Начать заново').click()
    await flushPromises()

    expect(startBody().skip_qwen).toBe(false)
    wrapper.unmount()
  })

  it('Менеджер выключает описание только для этого запуска', async () => {
    const wrapper = await openDialog({ canWriteSettings: false })

    toggle().click()
    await flushPromises()

    // Общая настройка не тронута.
    expect(
      calls.some((item) => item.method === 'PUT' && item.path.endsWith('/v1/qwen/settings')),
    ).toBe(false)

    await bodyButton('Начать заново').click()
    await flushPromises()

    expect(startBody().skip_qwen).toBe(true)
    wrapper.unmount()
  })
})

describe('глубина сканирования новых фото', () => {
  it('по умолчанию сканирует неделю', async () => {
    const wrapper = await openDialog()

    expect(document.body.textContent).toContain('Сканировать новые фото за')
    expect(document.body.textContent).toContain('1 неделя')

    await bodyButton('Начать заново').click()
    await flushPromises()

    expect(startBody().scan_days).toBe(7)
    wrapper.unmount()
  })

  it('«Все даты» передаются как отсутствие ограничения', async () => {
    const wrapper = await openDialog()

    // Открываем выпадающий список и выбираем «Все даты».
    document.body.querySelector('.q-select').click()
    await flushPromises()

    const option = Array.from(document.body.querySelectorAll('.q-item')).find(
      (item) => item.textContent.trim() === 'Все даты',
    )

    option.click()
    await flushPromises()

    await bodyButton('Начать заново').click()
    await flushPromises()

    expect(startBody().scan_days).toBe(null)
    wrapper.unmount()
  })
})
