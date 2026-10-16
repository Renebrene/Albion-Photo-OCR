// Диапазон дат для поля «Период…» на странице фото.
//
// Даты считаются по ЛОКАЛЬНОМУ календарю: фильтр на сервере сравнивает
// календарные сутки (`created_at::date` / `taken_at::date`), поэтому
// `toISOString()` здесь не годится — он переводит в UTC и в отрицательных
// часовых поясах отдаёт предыдущий день, из-за чего «сегодня» захватывало бы
// вчерашние фото.

const PERIODS = [
  { label: 'Все даты', value: 'all' },
  { label: 'Сегодня', value: 'today' },
  { label: 'Вчера', value: 'yesterday' },
  { label: 'Позавчера', value: 'day_before' },
  { label: 'За неделю', value: 'week' },
  { label: 'Текущий месяц', value: 'month' },
  { label: 'Предыдущий месяц', value: 'prev_month' },
  { label: 'Период…', value: 'custom' },
]

export { PERIODS }

/** Календарная дата в виде YYYY-MM-DD по локальному времени. */
export function isoDate(date) {
  const pad = (value) => String(value).padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** Дата, отстоящая от сегодняшней на `days` суток назад. */
export function daysAgo(days, now = new Date()) {
  const date = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  date.setDate(date.getDate() - days)

  return date
}

function monthRange(offset, now) {
  const first = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  const last = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)

  return [isoDate(first), isoDate(last)]
}

/**
 * Границы периода [с, по] или [null, null] для «Все даты».
 *
 * `now` передаётся только в тестах — в приложении берётся текущая дата.
 */
export function periodRange(period, { customFrom = null, customTo = null } = {}, now = new Date()) {
  switch (period) {
    case 'today':
      return [isoDate(now), isoDate(now)]
    case 'yesterday':
      return [isoDate(daysAgo(1, now)), isoDate(daysAgo(1, now))]
    case 'day_before':
      return [isoDate(daysAgo(2, now)), isoDate(daysAgo(2, now))]
    case 'week':
      // Последние семь суток, включая сегодняшние.
      return [isoDate(daysAgo(6, now)), isoDate(now)]
    case 'month':
      return monthRange(0, now)
    case 'prev_month':
      return monthRange(-1, now)
    case 'custom':
      return [customFrom || null, customTo || null]
    default:
      return [null, null]
  }
}
