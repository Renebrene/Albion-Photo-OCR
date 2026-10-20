// Руководство пользователя: новые возможности (кроп щита, облачное
// распознавание, автообновление грида) должны быть описаны для всех ролей.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it } from 'vitest'
import { h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia } from 'pinia'

import Help from '../src/pages/Help.vue'

afterEach(() => {
  document.body.innerHTML = ''
})

// QPage рендерится только внутри QLayout — оборачиваем страницу так же, как
// это делает App.vue. Render-функция, а не template: runtime-компилятор в
// тестовой сборке не подключён.
const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(Help) }),
    }),
}

async function mountHelp() {
  const wrapper = mount(Host, {
    attachTo: document.body,
    global: { plugins: [Quasar, createPinia()] },
  })
  await flushPromises()
  return wrapper
}

describe('руководство пользователя', () => {
  it('описывает кроп рекламного щита', async () => {
    const wrapper = await mountHelp()
    const text = wrapper.text()

    expect(text).toContain('Поиск рекламного щита')
    expect(text).toContain('crop рекламного щита для QWEN')
    wrapper.unmount()
  })

  it('описывает локальное и облачное распознавание', async () => {
    const wrapper = await mountHelp()
    const text = wrapper.text()

    expect(text).toContain('Распознавание: кроп щита и облако')
    expect(text).toContain('Облако (OpenAI-совместимый)')
    expect(text).toContain('отправляется на внешний сервис')
    wrapper.unmount()
  })

  it('объясняет автообновление грида после HYBRID', async () => {
    const wrapper = await mountHelp()

    expect(wrapper.text()).toContain('галерея обновляется сама')
    wrapper.unmount()
  })
})
