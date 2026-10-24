// Albion connection settings: masked token, "empty = keep", verify.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { useSessionStore } from '../src/stores/session'
import { createPinia, setActivePinia } from 'pinia'

import CloudSettings from '../src/components/CloudSettings.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

let calls
let settings

function installFetch() {
  calls = []
  settings = {
    base_url: 'https://files.example.ru',
    folder_id: 'folder-1',
    ttl_days: 90,
    configured: true,
    api_key_set: true,
    api_key_hint: '…cret',
  }

  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]
    const body = options.body ? JSON.parse(options.body) : null
    calls.push({ method, path, body })

    if (path === '/api/v1/cloud/settings' && method === 'GET') {
      return json(settings)
    }

    if (path === '/api/v1/cloud/settings' && method === 'PUT') {
      settings = {
        ...settings,
        ...body,
        api_key_set: body.api_key ? true : settings.api_key_set,
      }
      return json(settings)
    }

    if (path === '/api/v1/cloud/verify') {
      return json({ ok: true, name: 'Photobase', scopes: ['upload', 'download'] })
    }

    return json({}, 404)
  })
}

function mountSettings() {
  const pinia = createPinia()
  setActivePinia(pinia)
  // Открытый режим: спека проверяет настройки Albion без аутентификации.
  useSessionStore().authEnabled = false

  return mount(CloudSettings, {
    global: { plugins: [Quasar, pinia] },
  })
}

function button(wrapper, text) {
  return wrapper.findAll('button').find((item) => item.text().includes(text))
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('настройки Albion', () => {
  it('показывает адрес и маску сохранённого токена', async () => {
    installFetch()
    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('Файлохранилище Albion')

    const inputs = wrapper.findAll('input')
    expect(inputs[0].element.value).toBe('https://files.example.ru')
    expect(inputs[1].element.value).toBe('folder-1')
    expect(wrapper.text()).toContain('…cret')
    expect(wrapper.text()).not.toContain('super-secret')
    wrapper.unmount()
  })

  it('не отправляет токен, если поле оставили пустым', async () => {
    installFetch()
    const wrapper = mountSettings()
    await flushPromises()

    await button(wrapper, 'Сохранить').trigger('click')
    await flushPromises()

    const put = calls.find((item) => item.method === 'PUT')
    expect(put.body).toEqual({
      base_url: 'https://files.example.ru',
      folder_id: 'folder-1',
      ttl_days: 90,
    })
    expect(put.body).not.toHaveProperty('api_key')
    wrapper.unmount()
  })

  it('отправляет новый токен и проверяет связь', async () => {
    installFetch()
    const wrapper = mountSettings()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[3].setValue('alb_new_token')
    await button(wrapper, 'Сохранить').trigger('click')
    await flushPromises()

    expect(calls.find((item) => item.method === 'PUT').body.api_key).toBe('alb_new_token')

    await button(wrapper, 'Проверить связь').trigger('click')
    await flushPromises()

    expect(calls.some((item) => item.path === '/api/v1/cloud/verify')).toBe(true)
    expect(wrapper.text()).toContain('Связь есть')
    wrapper.unmount()
  })

  it('очищает токен отдельной кнопкой', async () => {
    installFetch()
    const wrapper = mountSettings()
    await flushPromises()

    await button(wrapper, 'Очистить токен').trigger('click')
    await flushPromises()

    expect(calls.find((item) => item.method === 'PUT').body).toEqual({ api_key: '' })
    wrapper.unmount()
  })
})

describe('срок ссылки', () => {
  it('проверяет диапазон и не даёт сохранить 0 или отрицательное', async () => {
    installFetch()
    const wrapper = mountSettings()
    await flushPromises()

    const ttl = wrapper.findAll('input')[2]

    // 0 раньше молча превращался в 90, отрицательное уходило как есть.
    // Проверяем гарантию: пока значение вне диапазона, сохранить нельзя, а
    // правило поля объясняет причину (сообщение Quasar показывает по blur).
    await ttl.setValue('0')
    await flushPromises()

    expect(button(wrapper, 'Сохранить').attributes('disabled')).toBeDefined()

    await ttl.setValue('-5')
    await flushPromises()
    expect(button(wrapper, 'Сохранить').attributes('disabled')).toBeDefined()

    await ttl.setValue('4000')
    await flushPromises()
    expect(button(wrapper, 'Сохранить').attributes('disabled')).toBeDefined()

    await ttl.setValue('30')
    await flushPromises()

    expect(button(wrapper, 'Сохранить').attributes('disabled')).toBeUndefined()

    await button(wrapper, 'Сохранить').trigger('click')
    await flushPromises()

    const put = calls.find((item) => item.method === 'PUT')

    expect(put.body.ttl_days).toBe(30)
    wrapper.unmount()
  })
})
