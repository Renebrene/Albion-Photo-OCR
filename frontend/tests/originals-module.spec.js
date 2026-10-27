// Component test: панель «Доступность оригиналов» показывает корни, отдельно
// помечает отмонтированный том и говорит, сколько фото из-за него осталось без
// оригинала — именно этот случай (Win10 отключили, корпус лежал на TEST) и был
// поводом для панели. Полная проверка ставится заданием: кнопка → POST →
// опрос /v1/jobs/{id} → отчёт. Ответы API подменяются через global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import OriginalsModule from '../src/components/OriginalsModule.vue'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

const HEALTH = {
  configured: true,
  total_photos: 56936,
  outside_roots: 1518,
  unavailable_roots: 1,
  roots: [
    { path: '/media/alexice/Win10', label: 'Win10', available: false, photos: 27974 },
    { path: '/media/alexice/TEST', label: 'TEST', available: true, photos: 27444 },
  ],
}

const REPORT = {
  checked: 56936,
  available: 55418,
  missing: 0,
  outside_roots: 1518,
  root_unavailable: 0,
  generated_at: '2026-10-28T00:10:00+00:00',
  report: '/home/alexice/projects/albion-photobase/data/reports/originals_health_20261028_001000.json',
}

function reply(body, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: async () => body })
}

function installFetch({
  health = HEALTH,
  healthStatus = 200,
  latest = { report: null },
  check = { job_id: 7, started: true },
  job = { status: 'DONE', result: REPORT },
} = {}) {
  const calls = []

  global.fetch = vi.fn((url, options = {}) => {
    const path = new URL(String(url), 'http://localhost').pathname
    const method = (options.method || 'GET').toUpperCase()
    calls.push(`${method} ${path}`)

    if (path.endsWith('/v1/originals/health')) return reply(health, healthStatus)
    if (path.endsWith('/v1/originals/check/latest')) return reply(latest)
    if (path.endsWith('/v1/originals/check') && method === 'POST') return reply(check, 202)
    if (path.includes('/v1/jobs/')) return reply(job)

    return reply({ detail: `no route for ${method} ${path}` }, 404)
  })

  return calls
}

async function mountPanel(role = 'Администратор') {
  const pinia = createPinia()
  setActivePinia(pinia)
  useSessionStore().user = { user_id: 1, name: 'Администратор', role }

  const wrapper = mount(OriginalsModule, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  Notify.create = vi.fn()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('доступность оригиналов в техническом разделе', () => {
  it('показывает корни, пути и число фото на каждом', async () => {
    installFetch()
    const wrapper = await mountPanel()
    const text = wrapper.text()

    expect(text).toContain('Win10')
    expect(text).toContain('/media/alexice/TEST')
    expect(text).toContain('27974')
    expect(text).toContain('подключён')
    expect(text).toContain('не подключён')
    expect(text).toContain('Всего записей: 56936')
    expect(text).toContain('вне разрешённых корней: 1518')
  })

  it('на отключённом томе с фото зовёт смонтировать том или перенести пути', async () => {
    installFetch()
    const wrapper = await mountPanel()
    const text = wrapper.text()

    expect(text).toContain('27974 фото')
    expect(text).toContain('оригинал недоступен')
    expect(text).toContain('remap_source_root.py')
  })

  it('про пустой отключённый корень не тревожит', async () => {
    installFetch({
      health: {
        ...HEALTH,
        roots: [{ path: '/media/alexice/Win10', label: 'Win10', available: false, photos: 0 }],
      },
    })
    const wrapper = await mountPanel()
    const text = wrapper.text()

    expect(text).toContain('не подключён')
    expect(text).not.toContain('remap_source_root.py')
  })

  it('пустой SCENE_ORIGINALS_ROOTS — отдельное сообщение', async () => {
    installFetch({
      health: {
        configured: false,
        roots: [],
        total_photos: 0,
        outside_roots: 0,
        unavailable_roots: 0,
      },
    })
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('SCENE_ORIGINALS_ROOTS')
    expect(wrapper.find('table').exists()).toBe(false)
  })

  it('ошибка запроса видна, а не проглочена', async () => {
    installFetch({ health: { detail: 'нет связи' }, healthStatus: 503 })
    const wrapper = await mountPanel()

    expect(wrapper.find('.bg-red-1').exists()).toBe(true)
  })

  it('без запущенных проверок честно говорит об этом', async () => {
    installFetch()
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('Полная проверка файлов ещё не запускалась')
  })

  it('показывает последний сохранённый отчёт', async () => {
    installFetch({ latest: { report: REPORT } })
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('Последняя полная проверка')
    expect(wrapper.text()).toContain('проверено 56936')
    expect(wrapper.text()).toContain('недоступно 1518')
  })

  it('кнопка ставит задание и показывает его результат', async () => {
    const calls = installFetch()
    const wrapper = await mountPanel()

    const button = wrapper
      .findAll('button')
      .find((element) => element.text().includes('Проверить файлы'))
    await button.trigger('click')
    await flushPromises()
    await flushPromises()

    expect(calls).toContain('POST /api/v1/originals/check')
    expect(calls.some((call) => call.includes('/api/v1/jobs/7'))).toBe(true)
    expect(wrapper.text()).toContain('Последняя полная проверка')
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'positive' }),
    )
  })

  it('если задание не создалось, кнопка не залипает в загрузке', async () => {
    const calls = installFetch({ check: { job_id: null } })
    const wrapper = await mountPanel()

    const button = wrapper
      .findAll('button')
      .find((element) => element.text().includes('Проверить файлы'))

    await button.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Не удалось поставить проверку')

    // Повторный клик снова ставит задание — значит загрузка не осталась навсегда.
    await button.trigger('click')
    await flushPromises()

    expect(
      calls.filter((call) => call === 'POST /api/v1/originals/check'),
    ).toHaveLength(2)
  })

  it('не-администратор кнопку не видит', async () => {
    installFetch()
    const wrapper = await mountPanel('Гость')

    const button = wrapper
      .findAll('button')
      .find((element) => element.text().includes('Проверить файлы'))

    expect(button).toBeUndefined()
  })
})
