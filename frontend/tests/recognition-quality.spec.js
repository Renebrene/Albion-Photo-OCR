// Read-only snapshot view of recognition quality.
// @vitest-environment happy-dom

import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import RecognitionQuality from '../src/components/RecognitionQuality.vue'

const snapshot = {
  schema_version: 1,
  generated_at: '2026-11-08',
  title: 'Сравнение распознавания HYBRID run 4',
  source: {
    experiment: 'comparison_combinations',
    run_id: 4,
    sample_items: 56574,
    labelled_items: 31983,
    unlabelled_items: 24591,
    label_method: 'эвристическое сопоставление имени файла',
    label_normalization: 'canonical IDs',
    is_temporal_holdout: false,
    independent_manual_labels: false,
    notes: ['Это офлайн-оценка, не live-оценка production.'],
  },
  totals: { items: 56574, labelled: 31983, unlabelled: 24591 },
  address_metrics_source: {
    experiment: 'labeled_error_table', run_id: 4, items: 32021, labelled: 32021,
    correct: 30376, wrong: 1607, unknown: 38, notes: 'Separate aggregate.',
    selection: 'error_rate > 5% of items', total_addresses: 109, selected_addresses: 3,
    error_addresses: 2, naming_variant_addresses: 1,
    label_error_addresses: 0, label_error_items: 0,
    selected_items: 433, error_items: 406, naming_variant_items: 27,
  },
  variants: [
    {
      id: 'production', name: 'Production baseline', family: 'DINO + HYBRID',
      labelled: 31983, correct: 30383, wrong: 1600, review: 0,
      accuracy: 30383 / 31983, delta_vs_production: 0, weights: null,
      wrong_pairs: [
        { expected_id: 176, expected: 'Космонавтов 15', predicted_id: 177, predicted: 'Космонавтов 15-17', count: 208 },
      ],
    },
    {
      id: 'experiment', name: 'Эксперимент', family: 'rescore',
      labelled: 31983, correct: 30430, wrong: 1553, review: 0,
      accuracy: 30430 / 31983, delta_vs_production: 47, weights: null,
      wrong_pairs: [],
    },
  ],
  addresses: [
    {
      address_id: 176, name: 'Космонавтов 15', items: 329, fingerprint_items: 46,
      correct: 47, wrong: 282, unknown: 0, error_rate: 282 / 329,
      top_confusions: [{ address_id: 177, name: 'Космонавтов 15-17', count: 192 }],
      is_naming_variant: false, classification: 'recognition_error',
    },
    {
      address_id: 173, name: 'Космонавтов 14а', items: 104, fingerprint_items: 12,
      correct: 32, wrong: 72, unknown: 0, error_rate: 72 / 104,
      top_confusions: [{ address_id: 174, name: 'Космонавтов 14-16 А на квадро', count: 55 }],
      is_naming_variant: false, classification: 'recognition_error',
    },
    {
      address_id: 175, name: 'Космонавтов 14-16 Б в центр', items: 27, fingerprint_items: 10,
      correct: 18, wrong: 9, unknown: 0, error_rate: 9 / 27,
      top_confusions: [{ address_id: 173, name: 'Космонавтов 14а', count: 9 }],
      is_naming_variant: true, classification: 'naming_variant',
      canonical_address_id: 173, canonical_name: 'Космонавтов 14а',
    },
  ],
}

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

it('показывает provenance, выборку и направленные ошибки адресов', async () => {
  global.fetch = vi.fn(async () => json(snapshot))

  const wrapper = mount(RecognitionQuality, { global: { plugins: [Quasar] } })
  await flushPromises()

  const text = wrapper.text()
  expect(text).toContain('не live-точность production')
  expect(text).toContain('31 983')
  expect(text).toContain('Temporal holdout: нет')
  expect(text).toContain('В таблице 3 из 109 адресов')
  expect(text).toContain('ошибки — 2, варианты названия — 1, ошибки в названии — 0')
  expect(text).toContain('вариантов названия — 1, ошибок в названии — 0')
  expect(text).toContain('Космонавтов 15-17')
  expect(text).toContain('вариант названия')
  expect(text).toContain('→ Космонавтов 14а')
  expect(text).toContain('85,71%')
  expect(text).toContain('69,23%')

  const firstAddress = wrapper.find('[data-address-number="1"]')
  expect(firstAddress.exists()).toBe(true)
  expect(firstAddress.text()).toContain('Космонавтов 15')

  wrapper.unmount()
})

it('показывает серверную ошибку снимка', async () => {
  global.fetch = vi.fn(async () => json({ detail: 'снимок пока не опубликован' }, 503))

  const wrapper = mount(RecognitionQuality, { global: { plugins: [Quasar] } })
  await flushPromises()

  expect(wrapper.text()).toContain('снимок пока не опубликован')
  wrapper.unmount()
})

it('объявляет вкладку качества между «Слепками» и «Адресами»', () => {
  const source = readFileSync(join(process.cwd(), 'src/pages/Technical.vue'), 'utf8')
  const tabNames = [...source.matchAll(/<q-tab name="([^"]+)"/g)].map((match) => match[1])

  const fingerprints = tabNames.indexOf('fingerprints')
  const quality = tabNames.indexOf('recognition_quality')
  const addresses = tabNames.indexOf('addresses')

  expect(quality).toBe(fingerprints + 1)
  expect(addresses).toBe(quality + 1)
  expect(source).toContain('<q-tab-panel name="recognition_quality">')
})
