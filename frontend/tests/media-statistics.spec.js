// Раздел СТАТИСТИКА технической страницы: сводка и месяцы.
// @vitest-environment happy-dom

import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import MediaStatistics from '../src/components/MediaStatistics.vue'

const stats = {
  photos: 326,
  videos: 9,
  period_start: '2025-04-01T10:00:00',
  period_end: '2026-10-17T09:30:00',
  last_photo_at: '2026-10-17T09:30:00',
  last_video_at: '2026-09-02T12:00:00',
  today_photos: 2,
  today_videos: 1,
  yesterday_photos: 3,
  yesterday_videos: 0,
  day_before_photos: 4,
  day_before_videos: 2,
  last_7_days_photos: 20,
  last_7_days_videos: 3,
  this_month_photos: 50,
  this_month_videos: 4,
  months: [
    { month: '2026-09-01', photos: 10, videos: 1 },
    { month: '2026-10-01', photos: 20, videos: 2 },
  ],
}

beforeEach(() => {
  global.fetch = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => stats,
  }))
})

it('показывает последние загрузки, итоги и периоды', async () => {
  const wrapper = mount(MediaStatistics, {
    global: { plugins: [Quasar] },
  })

  await flushPromises()

  const text = wrapper.text()

  expect(text).toContain('Последняя загрузка фото')
  expect(text).toContain('17.10.2026 09:30')
  expect(text).toContain('Последняя загрузка видео')
  expect(text).toContain('02.09.2026 12:00')
  expect(text).toContain('326 фото · 9 видео')
  expect(text).toContain('01.04.2025 — 17.10.2026')

  // Периоды: сегодня/вчера/позавчера/неделя/месяц.
  expect(text).toContain('Сегодня')
  expect(text).toContain('Вчера')
  expect(text).toContain('Позавчера')
  expect(text).toContain('За неделю')
  expect(text).toContain('Текущий месяц')

  // Месяцы: новые сверху.
  expect(text).toContain('Октябрь 2026')
  expect(text).toContain('Сентябрь 2026')
  expect(text.indexOf('Октябрь 2026')).toBeLessThan(
    text.indexOf('Сентябрь 2026'),
  )

  wrapper.unmount()
})

it('показывает ошибку загрузки', async () => {
  global.fetch = vi.fn(async () => ({
    ok: false,
    status: 503,
    json: async () => ({ detail: 'stats unavailable' }),
  }))

  const wrapper = mount(MediaStatistics, {
    global: { plugins: [Quasar] },
  })

  await flushPromises()

  expect(wrapper.text()).toContain('API error 503')

  wrapper.unmount()
})
