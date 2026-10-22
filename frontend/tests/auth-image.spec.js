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
  it('приводит строку "16/9" к числу', async () => {
    const wrapper = await mountImage('16/9')

    // Не дожидаясь загрузки, упавший/скелетный блок уже получает aspect-ratio,
    // посчитанный из дроби, а не NaN.
    expect(wrapper.html()).toContain(String(16 / 9))
    expect(wrapper.html()).not.toContain('NaN')
  })

  it('принимает числовой ratio как есть', async () => {
    const wrapper = await mountImage(1.5)
    expect(wrapper.html()).toContain('1.5')
  })

  it('игнорирует некорректный ratio', async () => {
    const wrapper = await mountImage('ab/cd')
    expect(wrapper.html()).not.toContain('NaN')
    expect(wrapper.html()).toContain('min-height')
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
    const first = mount(AuthImage, {
      props: { url },
      global: { plugins: [Quasar] },
    })
    await flushPromises()
    expect(create).toHaveBeenCalledTimes(1)

    first.unmount()
    // Сразу не освобождается: картинка ещё может понадобиться при прокрутке.
    expect(revoke).not.toHaveBeenCalled()

    const second = mount(AuthImage, {
      props: { url },
      global: { plugins: [Quasar] },
    })
    await flushPromises()

    // Повторного запроса нет — отдали удержанный blob.
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(create).toHaveBeenCalledTimes(1)

    second.unmount()
    clearImageCache()
    expect(revoke).toHaveBeenCalledWith('blob:preview')
  })
})
