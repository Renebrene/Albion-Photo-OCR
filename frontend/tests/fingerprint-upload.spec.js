// Удалённая загрузка папки для слепка: файлы с компьютера менеджера едут на
// сервер по одному, сборка идёт по билету загрузки (задание, п. 5а/5б).
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { DOMWrapper, flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import FingerprintsList from '../src/components/FingerprintsList.vue'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

let calls
let uploads

class FakeXhr {
  constructor() {
    this.upload = {}
    this.status = 201
    this.responseText = JSON.stringify({ name: 'a.jpg', received: 1 })
  }

  open(method, url) {
    this.method = method
    this.url = url
  }

  setRequestHeader() {}

  send(body) {
    uploads.push({ url: this.url, form: body })
    this.onload?.()
  }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    calls.push(`${method} ${path}`)

    if (method === 'GET' && path.endsWith('/v1/fingerprints/registry')) {
      return jsonResponse({ items: [] })
    }

    if (method === 'GET' && path.endsWith('/v1/fingerprints/browse')) {
      return jsonResponse({ path: null, parent: null, photos: 0, dirs: [] })
    }

    if (method === 'POST' && path.endsWith('/v1/fingerprints/uploads')) {
      return jsonResponse(
        {
          upload_id: 'a'.repeat(32),
          max_files: 150,
          max_file_bytes: 25 * 1024 * 1024,
          max_total_bytes: 1024 * 1024 * 1024,
        },
        201,
      )
    }

    if (method === 'POST' && path.endsWith('/v1/fingerprints/build')) {
      calls.push(JSON.parse(options.body))
      return jsonResponse({ job_id: 9, skipped: false, photos: 2, max_photos: null }, 202)
    }

    if (method === 'GET' && path.includes('/v1/jobs/')) {
      return jsonResponse({ id: 9, status: 'DONE', result: { images: 2 } })
    }

    if (method === 'GET' && path.endsWith('/v1/addresses/directory/grouped')) {
      return jsonResponse({ items: [] })
    }

    return jsonResponse({ items: [], next_cursor: null })
  })
}

function mountWindow() {
  return mount(FingerprintsList, { global: { plugins: [Quasar] } })
}

// Диалог Quasar рисуется порталом в document.body, поэтому его кнопки и поля
// ищутся там, а не в обёртке компонента.
function dialogRoot() {
  return document.body.querySelector('.q-dialog')
}

function dialogButton(text) {
  const element = [...(dialogRoot()?.querySelectorAll('button') || [])].find(
    (item) => item.textContent.replace(/\s+/g, ' ').trim() === text,
  )

  return element ? new DOMWrapper(element) : null
}

function dialogButtonContaining(text) {
  const element = [...(dialogRoot()?.querySelectorAll('button') || [])].find(
    (item) => item.textContent.includes(text),
  )

  return element ? new DOMWrapper(element) : null
}

async function openBuildDialog(wrapper) {
  const button = wrapper.findAll('button').find((item) => item.text().includes('Создать слепок'))
  await button.trigger('click')
  await flushPromises()
}

function chooseFiles(names) {
  const input = dialogRoot().querySelector('input[type="file"]')
  const files = names.map((name) => new File([new Uint8Array(64)], name, { type: 'image/jpeg' }))

  Object.defineProperty(input, 'files', { value: files, configurable: true })

  return new DOMWrapper(input).trigger('change')
}

beforeEach(() => {
  calls = []
  uploads = []
  setActivePinia(createPinia())
  // Окно сборки доступно Администратору: в открытом режиме роль всё равно
  // проверяется по session.user.
  const session = useSessionStore()
  session.authEnabled = false
  session.user = { user_id: 1, name: 'Администратор', role: 'Администратор' }
  global.XMLHttpRequest = FakeXhr
  installFetch()
})

afterEach(() => {
  delete global.fetch
  delete global.XMLHttpRequest
})

describe('удалённая загрузка папки', () => {
  it('отправляет файлы по одному и собирает по билету', async () => {
    const wrapper = mountWindow()
    await flushPromises()
    await openBuildDialog(wrapper)

    // Переключаемся на папку с компьютера и выбираем файлы.
    await dialogButtonContaining('Папка на моём компьютере').trigger('click')
    await flushPromises()
    await chooseFiles(['a.jpg', 'b.jpeg'])
    await flushPromises()

    expect(dialogRoot().textContent).toContain('2 файлов')

    // ID слепка и запуск сборки.
    await new DOMWrapper(dialogRoot().querySelector('input')).setValue('test_v33')

    await dialogButton('Собрать').trigger('click')
    await flushPromises()

    // Загрузка: билет и по одному запросу на файл.
    expect(calls).toContain('POST /api/v1/fingerprints/uploads')
    expect(uploads).toHaveLength(2)
    expect(uploads[0].url).toContain('aaaaaaaa')

    // Сборка идёт по upload_id, серверного пути в запросе нет.
    const buildCall = calls.find((item) => typeof item === 'object')
    expect(buildCall.fingerprint_id).toBe('test_v33')
    expect(buildCall.upload_id).toBe('a'.repeat(32))
    expect('folder' in buildCall).toBe(false)

    wrapper.unmount()
  })

  it('без выбранной папки сборку не запускает', async () => {
    const wrapper = mountWindow()
    await flushPromises()
    await openBuildDialog(wrapper)

    await dialogButtonContaining('Папка на моём компьютере').trigger('click')
    await flushPromises()

    await new DOMWrapper(dialogRoot().querySelector('input')).setValue('test_v33')

    await dialogButton('Собрать').trigger('click')
    await flushPromises()

    expect(calls).not.toContain('POST /api/v1/fingerprints/uploads')
    expect(Notify.create).toHaveBeenCalled()

    wrapper.unmount()
  })
})
