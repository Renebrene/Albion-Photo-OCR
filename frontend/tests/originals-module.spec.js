// Component test: панель «Доступность оригиналов» показывает корни, отдельно
// помечает отмонтированный том и говорит, сколько фото из-за него осталось без
// оригинала — именно этот случай (Win10 отключили, корпус лежал на TEST) и был
// поводом для панели. Ответ API подменяется через global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import OriginalsModule from '../src/components/OriginalsModule.vue'

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

function installFetch(body, { status = 200 } = {}) {
  global.fetch = vi.fn(() =>
    Promise.resolve({ ok: status < 400, status, json: async () => body }),
  )
}

async function mountPanel() {
  const wrapper = mount(OriginalsModule, { global: { plugins: [Quasar] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

describe('доступность оригиналов в техническом разделе', () => {
  it('показывает корни, пути и число фото на каждом', async () => {
    installFetch(HEALTH)
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
    installFetch(HEALTH)
    const wrapper = await mountPanel()
    const text = wrapper.text()

    expect(text).toContain('Win10')
    expect(text).toContain('27974 фото')
    expect(text).toContain('оригинал недоступен')
    expect(text).toContain('remap_source_root.py')
  })

  it('про пустой отключённый корень не тревожит', async () => {
    installFetch({
      ...HEALTH,
      roots: [{ path: '/media/alexice/Win10', label: 'Win10', available: false, photos: 0 }],
    })
    const wrapper = await mountPanel()
    const text = wrapper.text()

    // Состояние видно, но совет про перенос путей не показывается: терять нечего.
    expect(text).toContain('не подключён')
    expect(text).not.toContain('remap_source_root.py')
  })

  it('пустой SCENE_ORIGINALS_ROOTS — отдельное сообщение', async () => {
    installFetch({
      configured: false,
      roots: [],
      total_photos: 0,
      outside_roots: 0,
      unavailable_roots: 0,
    })
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('SCENE_ORIGINALS_ROOTS')
    expect(wrapper.find('table').exists()).toBe(false)
  })

  it('ошибка запроса видна, а не проглочена', async () => {
    installFetch({ detail: 'нет связи' }, { status: 503 })
    const wrapper = await mountPanel()

    expect(wrapper.find('.bg-red-1').exists()).toBe(true)
  })
})
