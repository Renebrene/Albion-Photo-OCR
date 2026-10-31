// «Уточнение» доступно только тогда, когда есть что сравнивать: QWEN
// участвует в прогоне или в базе уже лежат его описания.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QToggle, Quasar } from 'quasar'

import RefineStage from '../src/components/RefineStage.vue'

Notify.create = vi.fn()

function installFetch(payload) {
  global.fetch = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => payload,
  }))
}

async function mountStage(payload, rules = {
  version: 0,
  rules: {
    schema_version: 1,
    max_gap_seconds: 10,
    max_crop_dhash_distance: 6,
    description_mode: 'fill_empty',
    tags_mode: 'union_unique',
    conflict_mode: 'block_group',
  },
}) {
  global.fetch = vi.fn(async (_url, options = {}) => {
    const body = options.body ? JSON.parse(options.body) : null
    const result = String(_url).endsWith('/refine/settings')
      ? payload
      : String(_url).endsWith('/refine/rules') && options.method === 'GET'
        ? rules
        : String(_url).endsWith('/refine/rules')
          ? { version: rules.version + 1, rules: body.rules }
          : String(_url).endsWith('/refine/preview')
            ? { ...body, rules_version: rules.version + 1, rows_scanned: 10, proposal_photos: 2, description_fills: 1, tag_updates: 1, conflict_groups: 0, samples: [{ photo_id: 'PH_a', changes: { tags: ['x'] } }], preview_token: 'preview-token-1234567890', writes_performed: false }
            : { applied_photos: 2, stale_skipped: 0, writes_performed: true }
    return { ok: true, status: 200, json: async () => result }
  })
  const wrapper = mount(RefineStage, { global: { plugins: [Quasar] } })
  await flushPromises()
  return wrapper
}

afterEach(() => {
  delete global.fetch
})

describe('этап «Уточнение»', () => {
  it('выключатель доступен, когда QWEN дал результаты', async () => {
    const wrapper = await mountStage({
      enabled: false,
      available: true,
      gap_seconds: 30,
      crop_retention_days: 7,
      photos_ready: 12,
    })

    const toggle = wrapper.findComponent(QToggle)
    expect(toggle.props('disable')).toBe(false)
    expect(wrapper.text()).not.toContain('Этап недоступен')
  })

  it('сохраняет JSON-правила, строит preview и применяет только после отдельного действия', async () => {
    const wrapper = await mountStage({
      enabled: false, available: true, gap_seconds: 30, crop_retention_days: 7, photos_ready: 12,
    })

    expect(wrapper.text()).toContain('версия 0')
    const saveRulesButton = wrapper.findAll('button').find(button => button.text().includes('Проверить и сохранить версию'))
    await saveRulesButton.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('версия 1')

    const previewButton = wrapper.findAll('button').find(button => button.text().includes('Предпросмотр'))
    await previewButton.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Предпросмотр · версия 1')
    expect(wrapper.text()).toContain('Предпросмотр не записывает данные')

    const applyButton = wrapper.findAll('button').find(button => button.text().includes('Применить предложения'))
    await applyButton.trigger('click')
    await flushPromises()
    expect(global.fetch.mock.calls.some(([url]) => String(url).includes('/refine/apply'))).toBe(true)
  })

  it('без QWEN выключатель заблокирован и объяснён', async () => {
    const wrapper = await mountStage({
      enabled: false,
      available: false,
      gap_seconds: 30,
      crop_retention_days: 7,
      photos_ready: 0,
    })

    expect(wrapper.findComponent(QToggle).props('disable')).toBe(true)
    expect(wrapper.text()).toContain('Этап недоступен')
    expect(wrapper.text()).toContain('Запускать QWEN в «Обновлении базы»')
  })
})
