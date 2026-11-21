// Нормализация клиентов и брендов: сбой загрузки виден отдельно от «пусто».
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import ClientNormalization from '../src/components/ClientNormalization.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

let failing

let settingsCalls

const LOW_PRIORITY = ['Sunlight', 'Санлайт']

function installFetch() {
  settingsCalls = []

  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url).split('?')[0]

    if (failing) return json({ detail: 'база недоступна' }, 500)

    if (path.endsWith('/v1/qwen/settings')) {
      if ((options.method || 'GET').toUpperCase() === 'PUT') {
        const body = JSON.parse(options.body)
        settingsCalls.push(body)
        return json({ ...body })
      }

      return json({
        low_priority_names: LOW_PRIORITY,
        low_priority_default: LOW_PRIORITY,
        forbidden_words: ['мат'],
      })
    }

    if (path.endsWith('/v1/client-aliases')) return json({ items: [] })
    if (path.endsWith('/v1/client-aliases/qwen-names')) return json({ items: [] })
    if (path.endsWith('/v1/client-aliases/audit')) return json({ items: [] })

    return json({}, 404)
  })
}

function mountPanel() {
  setActivePinia(createPinia())

  return mount(ClientNormalization, { global: { plugins: [Quasar] } })
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('нормализация клиентов', () => {
  it('при сбое показывает причину и повтор, а не «Алиасов нет»', async () => {
    failing = true
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('база недоступна')
    expect(wrapper.text()).toContain('Повторить')
    // Пустота и сбой различимы: «нет данных» — только когда запрос прошёл.
    expect(wrapper.text()).not.toContain('Алиасов нет')
    expect(wrapper.text()).not.toContain('Пока нет распознанных названий')

    wrapper.unmount()
  })

  it('после успешной загрузки показывает обычное пустое состояние', async () => {
    failing = false
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('Алиасов нет')
    expect(wrapper.text()).not.toContain('Повторить')

    wrapper.unmount()
  })

  it('показывает список «низкого приоритета» и сохраняет новое название', async () => {
    failing = false
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('Низкий приоритет при выдаче')
    expect(wrapper.text()).toContain('Sunlight')
    expect(wrapper.text()).toContain('Санлайт')

    const block = wrapper.find('.delivery-block--low')
    const input = block
      .findAllComponents({ name: 'QInput' })
      .find((item) => item.props('label') === 'Название клиента или бренда')

    expect(input).toBeTruthy()
    await input.setValue('Лента')

    const add = block
      .findAll('button')
      .find((button) => button.text().includes('Добавить'))

    await add.trigger('click')
    await flushPromises()

    expect(settingsCalls).toHaveLength(1)
    expect(settingsCalls[0].low_priority_names).toEqual([
      'Sunlight',
      'Санлайт',
      'Лента',
    ])

    wrapper.unmount()
  })

  it('показывает и дополняет список «запрещённых к выдаче» слов', async () => {
    failing = false
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('Запрещённые к выдаче слова')
    expect(wrapper.text()).toContain('мат')

    const block = wrapper.find('.delivery-block--forbidden')
    const input = block
      .findAllComponents({ name: 'QInput' })
      .find((item) => item.props('label') === 'Слово или часть слова')

    expect(input).toBeTruthy()
    await input.setValue('спам')

    const add = block
      .findAll('button')
      .find((button) => button.text().includes('Добавить'))

    await add.trigger('click')
    await flushPromises()

    expect(settingsCalls).toHaveLength(1)
    expect(settingsCalls[0].forbidden_words).toEqual(['мат', 'спам'])

    wrapper.unmount()
  })

  it('повтор перезапрашивает данные', async () => {
    failing = true
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    failing = false

    // Кнопок повтора пять (названия, сопоставления, история, низкий
    // приоритет, запрещённые слова) — нажимаем все.
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const retry = wrapper
        .findAll('button')
        .find((item) => item.text().includes('Повторить'))

      if (!retry) break

      await retry.trigger('click')
      await flushPromises()
    }

    expect(wrapper.text()).toContain('Алиасов нет')
    expect(wrapper.text()).not.toContain('база недоступна')

    wrapper.unmount()
  })
})
