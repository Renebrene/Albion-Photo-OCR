// «Качество»: сводка по прогону HYBRID — точность по подписанным фото,
// таблица адресов, влияние на решение и частый перепутанный адрес.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import RecognitionQuality from '../src/components/RecognitionQuality.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const snapshot = {
  run: {
    hybrid_run_id: 15,
    dino_batch_id: 14,
    photos: 973,
    hybrid_finished_at: '2026-11-21T02:05:39',
    last_sort_at: '2026-11-21T02:05:33',
    last_hybrid_at: '2026-11-21T02:05:39',
  },
  totals: {
    photos: 973,
    labelled: 1114,
    correct: 947,
    wrong: 167,
    no_label: 0,
    no_prediction: 0,
    accuracy: 0.8501,
  },
  addresses: [
    {
      address_id: 196,
      name: 'Нагибина 19 А',
      photos: 66,
      fingerprint_photos: 146,
      labelled: 10,
      correct: 9,
      wrong: 1,
      accuracy: 0.9,
      influence: { kind: 'dino', share: 0.97, counts: { dino: 64, neighbors: 2 } },
      confused_with: { address_id: 197, name: 'Нагибина 21', count: 1 },
    },
    {
      address_id: 227,
      name: 'Шеболдаева 95',
      photos: 43,
      fingerprint_photos: 111,
      labelled: 0,
      correct: 0,
      wrong: 0,
      accuracy: null,
      influence: { kind: 'neighbors', share: 0.6, counts: { neighbors: 3, dino: 2 } },
      confused_with: null,
    },
  ],
}

let calls

function installFetch(live = snapshot) {
  calls = []

  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]
    calls.push({ path, url: String(url) })

    if (path.endsWith('/v1/recognition-quality/runs')) {
      return json({
        items: [
          { hybrid_run_id: 15, photos: 973, finished_at: '2026-11-21T02:05:39' },
          { hybrid_run_id: 13, photos: 42923, finished_at: '2026-11-17T21:47:41' },
        ],
      })
    }

    if (path.endsWith('/v1/recognition-quality/live')) {
      return json(live)
    }

    return json({}, 404)
  })
}

function mountPanel() {
  return mount(RecognitionQuality, { global: { plugins: [Quasar] } })
}

beforeEach(() => {
  installFetch()
})

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('качество распознавания', () => {
  it('показывает даты сортировки и общую точность', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Последняя сортировка')
    expect(text).toContain('21.11.2026 02:05')
    expect(text).toContain('85')
    expect(text).toContain('Верно')
    expect(text).toContain('947')

    wrapper.unmount()
  })

  it('строит таблицу адресов с процентом, влиянием и путаницей', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Нагибина 19 А')
    expect(text).toContain('90')
    expect(text).toContain('DINO (лучший)')
    expect(text).toContain('Нагибина 21')

    // У адреса без подписанных фото процент не выдумывается.
    expect(text).toContain('Шеболдаева 95')
    expect(text).toContain('соседи')

    wrapper.unmount()
  })

  it('предлагает полный прогон, когда в последнем мало подписанных кадров', async () => {
    installFetch({
      ...snapshot,
      totals: { ...snapshot.totals, labelled: 3, correct: 3, wrong: 0, accuracy: 1 },
    })

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('Взять полный прогон')

    wrapper.unmount()
  })

  it('запрашивает сводку последнего прогона по умолчанию', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const live = calls.find((call) => call.path.endsWith('/recognition-quality/live'))
    expect(live.url).not.toContain('hybrid_run_id')

    wrapper.unmount()
  })
})
