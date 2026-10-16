// Тесты диапазонов периода на странице фото: «сегодня»/«вчера»/«позавчера»/
// «за неделю» и месяцы считаются по локальному календарю, без сдвига в UTC.

import { describe, expect, it } from 'vitest'

import { PERIODS, daysAgo, isoDate, periodRange } from '../src/utils/periodRange'

// Фиксированная «сегодня» — 2026-03-01 (воскресенье), чтобы месяцы были
// проверяемыми, а переход через границу месяца — явным.
const NOW = new Date(2026, 2, 1, 12, 30)

describe('periodRange', () => {
  it('contains the quick options in the expected order', () => {
    expect(PERIODS.map((item) => item.value)).toEqual([
      'all',
      'today',
      'yesterday',
      'day_before',
      'week',
      'month',
      'prev_month',
      'custom',
    ])
  })

  it('returns both bounds of a single day for today/yesterday/day before', () => {
    expect(periodRange('today', {}, NOW)).toEqual(['2026-03-01', '2026-03-01'])
    expect(periodRange('yesterday', {}, NOW)).toEqual(['2026-02-28', '2026-02-28'])
    expect(periodRange('day_before', {}, NOW)).toEqual(['2026-02-27', '2026-02-27'])
  })

  it('covers the last seven days for the week option', () => {
    expect(periodRange('week', {}, NOW)).toEqual(['2026-02-23', '2026-03-01'])
  })

  it('returns month bounds including a short February', () => {
    expect(periodRange('month', {}, NOW)).toEqual(['2026-03-01', '2026-03-31'])
    expect(periodRange('prev_month', {}, NOW)).toEqual(['2026-02-01', '2026-02-28'])
  })

  it('passes the custom range through and empties every other option', () => {
    expect(
      periodRange('custom', { customFrom: '2026-01-05', customTo: '2026-01-09' }, NOW),
    ).toEqual(['2026-01-05', '2026-01-09'])

    expect(periodRange('all', {}, NOW)).toEqual([null, null])
    expect(periodRange('custom', {}, NOW)).toEqual([null, null])
  })

  it('uses the local calendar day, not the UTC one', () => {
    // Полночь по местному времени: toISOString() отдал бы предыдущий день в
    // часовых поясах с отрицательным смещением.
    const midnight = new Date(2026, 2, 1, 0, 5)

    expect(isoDate(midnight)).toBe('2026-03-01')
    expect(periodRange('today', {}, midnight)[0]).toBe('2026-03-01')
  })

  it('steps back across a month boundary', () => {
    expect(isoDate(daysAgo(1, NOW))).toBe('2026-02-28')
    expect(isoDate(daysAgo(6, NOW))).toBe('2026-02-23')
  })
})
