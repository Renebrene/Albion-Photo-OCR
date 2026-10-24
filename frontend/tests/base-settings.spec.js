// «Ссылки Albion» и настройки хранилища живут во вкладке «Настройки»,
// а не в «Отображении».
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import { useSessionStore } from '../src/stores/session'

import BaseSettings from '../src/components/BaseSettings.vue'
import DisplaySettings from '../src/components/DisplaySettings.vue'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]

    if (path === '/api/v1/cloud/settings') {
      return json({
        base_url: 'https://files.example.ru',
        folder_id: 'folder-1',
        ttl_days: 90,
        configured: true,
        api_key_set: false,
        api_key_hint: null,
      })
    }

    if (path === '/api/v1/media-links') {
      return json({ items: [], configured: true })
    }

    return json({}, 404)
  })
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('вкладка «Настройки»', () => {
  it('содержит настройки Albion и список ссылок', async () => {
    installFetch()
    const pinia = createPinia()
    setActivePinia(pinia)
    useSessionStore().authEnabled = false
    const wrapper = mount(BaseSettings, {
      global: { plugins: [Quasar, pinia] },
    })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Файлохранилище Albion')
    expect(text).toContain('Ссылки Albion')
    wrapper.unmount()
  })

  it('«Отображение» больше не содержит ссылки Albion', async () => {
    installFetch()
    const wrapper = mount(DisplaySettings, {
      global: { plugins: [Quasar, createPinia()] },
    })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Ссылки Albion')
    wrapper.unmount()
  })
})
