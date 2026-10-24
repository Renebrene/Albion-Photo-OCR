// AuthImage: строковый ratio ("16/9") должен нормализоваться в число, иначе
// Quasar q-img получает NaN и контейнер картинки схлопывается в нулевую высоту
// (постер загружается, но не виден).
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import AuthImage from '../src/components/AuthImage.vue'
import { clearImageCache } from '../src/api/client'

async function mountImage(ratio) {
  global.fetch = vi.fn(async () => ({ ok: false, status: 404, blob: async () => new Blob() }))
  const wrapper = mount(AuthImage, {
    props: { url: '/api/v1/videos/VI_x/poster', ratio },
    global: { plugins: [Quasar] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('AuthImage ratio', () => {
  it('не пропускает NaN для строки "16/9"', async () => {
    const wrapper = await mountImage('16/9')

    // Число или дробь — не важно; важно, что q-img не получает NaN и
    // контейнер картинки не схлопывается.
    expect(wrapper.html()).not.toContain('NaN')
  })

  it('принимает числовой ratio', async () => {
    const wrapper = await mountImage(1.5)
    expect(wrapper.html()).not.toContain('NaN')
  })

  it('игнорирует некорректный ratio', async () => {
    const wrapper = await mountImage('ab/cd')
    expect(wrapper.html()).not.toContain('NaN')
  })
})

describe('AuthImage object URL lifetime', () => {
  it('удерживает blob URL после размонтирования и не качает повторно', async () => {
    // Раньше blob освобождался сразу, и прокрутка вниз-вверх заново качала
    // превью. Теперь он остаётся в небольшом кэше: возврат — без сети.
    clearImageCache()

    const create = vi.fn(() => 'blob:preview')
    const revoke = vi.fn()
    global.URL.createObjectURL = create
    global.URL.revokeObjectURL = revoke
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      blob: async () => new Blob(),
    }))
    global.fetch = fetchMock

    const url = '/api/v1/photos/PH_test/previews/small'

    /** Прямой путь не сработал: только тогда грузим blob. */
    async function mountWithBrokenDirectPath() {
      const wrapper = mount(AuthImage, {
        props: { url },
        global: { plugins: [Quasar] },
      })
      await flushPromises()
      await wrapper.find('img').trigger('error')
      await flushPromises()
      return wrapper
    }

    const first = await mountWithBrokenDirectPath()
    expect(create).toHaveBeenCalledTimes(1)

    first.unmount()
    // Сразу не освобождается: картинка ещё может понадобиться при прокрутке.
    expect(revoke).not.toHaveBeenCalled()

    const second = await mountWithBrokenDirectPath()

    // Повторного запроса нет — отдали удержанный blob.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(create).toHaveBeenCalledTimes(1)

    second.unmount()
    clearImageCache()
    expect(revoke).toHaveBeenCalledWith('blob:preview')
  })

  it('не качает blob, пока прямой путь работает', async () => {
    // Каждая плитка скачивалась дважды: браузер тянул картинку по src, а
    // компонент — ещё раз через fetch, причём результат нигде не показывался,
    // пока прямой путь не падал.
    clearImageCache()

    const create = vi.fn(() => 'blob:preview')
    global.URL.createObjectURL = create
    const fetchMock = vi.fn(async () => ({ ok: true, status: 200, blob: async () => new Blob() }))
    global.fetch = fetchMock

    const wrapper = mount(AuthImage, {
      props: { url: '/api/v1/photos/PH_test/previews/small' },
      global: { plugins: [Quasar] },
    })
    await flushPromises()

    expect(fetchMock).not.toHaveBeenCalled()
    expect(create).not.toHaveBeenCalled()
    // Картинку показывает сам браузер, по обычному src.
    expect(wrapper.find('img').attributes('src')).toContain('/previews/small')

    wrapper.unmount()
    clearImageCache()
  })
})

describe('AuthImage lazy', () => {
  class FakeObserver {
    static instances = []

    constructor(callback) {
      this.callback = callback
      this.elements = []
      FakeObserver.instances.push(this)
    }

    observe(element) {
      this.elements.push(element)
    }

    disconnect() {
      this.elements = []
    }

    /** Прокрутка: плитка вошла в окно или ушла из него. */
    enter(visible) {
      this.callback([{ isIntersecting: visible }])
    }
  }

  let fetchMock
  let create

  beforeEach(() => {
    clearImageCache()
    FakeObserver.instances.length = 0
    global.IntersectionObserver = FakeObserver
    create = vi.fn(() => 'blob:preview')
    global.URL.createObjectURL = create
    fetchMock = vi.fn(async () => ({ ok: true, status: 200, blob: async () => new Blob() }))
    global.fetch = fetchMock
  })

  async function mountLazy(url = '/api/v1/photos/PH_test/previews/small') {
    const wrapper = mount(AuthImage, {
      props: { url, lazy: true },
      global: { plugins: [Quasar] },
    })
    await flushPromises()
    return wrapper
  }

  it('наблюдает корень плитки, а не ветку blob', async () => {
    const wrapper = await mountLazy()
    const observer = FakeObserver.instances[0]
    expect(observer).toBeTruthy()
    // Раньше ref стоял на ветке blob: у обычной плитки наблюдать было нечего,
    // и компонент уходил в аварийную ветку с лишней загрузкой.
    expect(observer.elements[0].classList.contains('auth-image-root')).toBe(true)
    wrapper.unmount()
  })

  it('blob грузится по ошибке прямого пути и только для видимой плитки', async () => {
    const wrapper = await mountLazy()
    const observer = FakeObserver.instances[0]

    await wrapper.find('img').trigger('error')
    await flushPromises()

    // Плитка ещё за краем экрана — запасную копию не качаем.
    expect(fetchMock).not.toHaveBeenCalled()

    observer.enter(true)
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(create).toHaveBeenCalledTimes(1)
    expect(wrapper.html()).toContain('blob:preview')

    // Ушла из окна — удержанный blob отпускаем, вместо него заглушка.
    observer.enter(false)
    await flushPromises()
    expect(wrapper.html()).not.toContain('blob:preview')

    wrapper.unmount()
  })
})
