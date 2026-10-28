// Подборки: без пиктограммы, строки одинаковые, список фильтруется по группе
// верхней панели (задание, п. 7, пункт «е»).
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import CollectionsPanel from '../src/components/CollectionsPanel.vue'
import { usePhotosStore } from '../src/stores/photos'

function mountPanel(scope = 'addresses') {
  return mount(CollectionsPanel, {
    props: { scope },
    global: { plugins: [Quasar] },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())

  const store = usePhotosStore()
  store.collections = [
    { collection_id: 1, name: 'Ростов', scope: 'addresses', members: 2, groups: ['rostov'] },
    { collection_id: 2, name: 'Таганрог', scope: 'addresses', members: 1, groups: ['cities'] },
    { collection_id: 3, name: 'Без группы', scope: 'addresses', members: 3, groups: [] },
    { collection_id: 4, name: 'Клиенты', scope: 'clients', members: 1 },
  ]
})

describe('CollectionsPanel.vue', () => {
  it('рисует строки без пиктограммы', async () => {
    usePhotosStore().group = null
    const wrapper = mountPanel()
    await wrapper.vm.$nextTick()

    // Удаление — отдельная кнопка-иконка; самой подборки пиктограммы нет.
    expect(wrapper.html()).not.toContain('bookmark')
    expect(wrapper.text()).toContain('Ростов')
  })

  it('показывает только подборки активной группы', async () => {
    usePhotosStore().group = 'rostov'
    const wrapper = mountPanel()
    await wrapper.vm.$nextTick()

    const text = wrapper.text()

    expect(text).toContain('Ростов')
    // Подборка без групп видна всегда, чужая группа — нет.
    expect(text).toContain('Без группы')
    expect(text).not.toContain('Таганрог')
  })

  it('клиентские подборки от группы не зависят', async () => {
    usePhotosStore().group = 'roads'
    const wrapper = mountPanel('clients')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Клиенты')
  })
})
