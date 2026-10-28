// Обновление по подсказке «Доступна новая сборка»: адрес получает уникальный
// параметр, иначе кеширующий слой отдаёт старую оболочку и подсказка
// повторяется бесконечно (28.10.2026).
// @vitest-environment node

import { describe, expect, it } from 'vitest'

import { cacheBustUrl } from '../src/utils/cacheBust'

describe('cacheBustUrl', () => {
  it('добавляет уникальный параметр', () => {
    const url = cacheBustUrl('http://localhost:8010/', 'abc123')

    expect(url).toBe('http://localhost:8010/?_v=abc123')
  })

  it('сохраняет фильтры, которые живут в адресе', () => {
    const url = new URL(
      cacheBustUrl('http://localhost:8010/?period=month&group=roads&address=addr%3A5', 'x1'),
    )

    expect(url.searchParams.get('period')).toBe('month')
    expect(url.searchParams.get('group')).toBe('roads')
    expect(url.searchParams.get('address')).toBe('addr:5')
  })

  it('заменяет прежний параметр, а не плодит второй', () => {
    const url = new URL(cacheBustUrl('http://localhost:8010/?_v=old', 'new'))

    expect(url.searchParams.getAll('_v')).toEqual(['new'])
  })

  it('работает и без пути, и с вложенным адресом', () => {
    expect(new URL(cacheBustUrl('http://localhost:8010/videos', 'v1')).searchParams.get('_v'))
      .toBe('v1')
  })
})
