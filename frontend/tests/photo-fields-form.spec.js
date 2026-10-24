// Общая форма полей описания: одни и те же пять полей показывают правка
// описания в карточке и ручной режим ИИ-поиска. Раньше это были две отдельные
// разметки с одинаковыми подписями (второй аудит, 2.5).
// @vitest-environment happy-dom

import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import PhotoFieldsForm from '../src/components/PhotoFieldsForm.vue'

function blankFields() {
  return {
    description: 'Текст описания',
    client: 'Клиент А',
    brand: 'Бренд Б',
    category: 'Категория В',
    tags: 'тег1, тег2',
  }
}

function mountForm(props = {}) {
  const fields = blankFields()
  const wrapper = mount(PhotoFieldsForm, {
    props: { fields, ...props },
    global: { plugins: [Quasar] },
  })

  return { wrapper, fields }
}

describe('форма полей описания', () => {
  it('показывает все пять полей с одинаковыми подписями', () => {
    const { wrapper } = mountForm({ columns: true })

    const labels = wrapper
      .findAll('.q-field__label')
      .map((label) => label.text().trim())

    expect(labels).toEqual([
      'Описание',
      'Клиент',
      'Бренд',
      'Категория',
      'Теги (через запятую)',
    ])
  })

  it('правит объект родителя, а не свою копию', async () => {
    const { wrapper, fields } = mountForm({ columns: true })

    const client = wrapper
      .findAll('input')
      .find((input) => input.element.value === 'Клиент А')
    expect(client).toBeTruthy()

    await client.setValue('Другой клиент')

    // Значение живёт в объекте вызывающего: сохранять его будет он же.
    expect(fields.client).toBe('Другой клиент')
    expect(fields.brand).toBe('Бренд Б')
  })

  it('в режиме поиска показывает один столбец и подсказку про теги', () => {
    const { wrapper } = mountForm({ tagsHint: 'Теги тоже участвуют в поиске' })

    // Сетки из двух колонок здесь нет.
    expect(wrapper.find('.row.q-col-gutter-sm').exists()).toBe(false)
    expect(wrapper.text()).toContain('Теги тоже участвуют в поиске')
  })

  it('в режиме правки сетка двухколоночная, подсказки про теги нет', () => {
    const { wrapper } = mountForm({ columns: true })

    expect(wrapper.find('.row.q-col-gutter-sm').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Теги тоже участвуют в поиске')
  })
})
