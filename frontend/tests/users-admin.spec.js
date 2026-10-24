// The users panel: an existing user's name, role and colour can be edited
// (the colour used to be settable only when the user was created).
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import UsersAdmin from '../src/components/UsersAdmin.vue'
import { setToken } from '../src/api/client'

Notify.create = vi.fn()

let users
let updates
let creates

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

beforeEach(() => {
  updates = []
  creates = []
  users = [
    {
      user_id: 1,
      name: 'Администратор',
      role: 'Администратор',
      color: '#1976d2',
      active: true,
    },
    {
      user_id: 2,
      name: 'Гость',
      role: 'Гость',
      color: null,
      active: true,
    },
  ]

  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    if (method === 'GET' && path.endsWith('/v1/users')) {
      return jsonResponse({ items: users })
    }

    if (method === 'POST' && path.endsWith('/v1/users')) {
      creates.push(JSON.parse(options.body))
      return jsonResponse({ ...users[0], user_id: 9, name: JSON.parse(options.body).name })
    }

    if (method === 'PATCH' && path.includes('/v1/users/')) {
      updates.push(JSON.parse(options.body))
      return jsonResponse(users[0])
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })

  setActivePinia(createPinia())
  setToken('test-token')
})

afterEach(() => {
  setToken(null)
  delete global.fetch
})

function mountPanel() {
  return mount(UsersAdmin, { global: { plugins: [Quasar] } })
}

function openEditDialog(wrapper) {
  const button = wrapper
    .findAll('button')
    .find((item) => item.html().includes('edit'))

  return button.trigger('click')
}

describe('UsersAdmin.vue', () => {
  it('edits the colour of an existing user', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    await openEditDialog(wrapper)
    await flushPromises()

    expect(document.body.textContent).toContain('Пользователь: Администратор')

    // The dialog carries the name, role and colour selects of the edit form.
    const selects = wrapper.findAllComponents({ name: 'QSelect' })
    const colour = selects.at(selects.length - 1)

    expect(colour.props('modelValue')).toBe('#1976d2')

    await colour.setValue('#26a69a')

    const save = [...document.body.querySelectorAll('button')].find((button) =>
      button.textContent.includes('Сохранить'),
    )
    save.click()
    await flushPromises()

    expect(updates).toHaveLength(1)
    expect(updates[0]).toEqual({
      name: 'Администратор',
      role: 'Администратор',
      color: '#26a69a',
    })
  })

  it('clears the colour when the field is emptied', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    await openEditDialog(wrapper)
    await flushPromises()

    const selects = wrapper.findAllComponents({ name: 'QSelect' })
    await selects.at(selects.length - 1).setValue(null)

    const save = [...document.body.querySelectorAll('button')].find((button) =>
      button.textContent.includes('Сохранить'),
    )
    save.click()
    await flushPromises()

    // The API reads null as "leave as is", so clearing sends an empty string.
    expect(updates[0].color).toBe('')
  })
})

describe('пустое имя', () => {
  it('не отправляется, а подсвечивается у поля', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const add = wrapper
      .findAll('button')
      .find((item) => item.html().includes('person_add') || item.text().includes('Добавить'))

    expect(add).toBeTruthy()
    await add.trigger('click')
    await flushPromises()

    const create = Array.from(document.body.querySelectorAll('button')).find((node) =>
      node.textContent.includes('Создать'),
    )

    expect(create).toBeTruthy()
    create.click()
    await flushPromises()

    // Ни запроса, ни нового пользователя: сказано, что имя нужно указать.
    expect(creates).toEqual([])
    expect(
      Notify.create.mock.calls.some((call) =>
        String(call[0]?.message || '').includes('Укажите имя'),
      ),
    ).toBe(true)

    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
