// Запрещённые к выдаче слова: фронтенд читает список QWEN и не пропускает
// такие слова в ручную правку карточки.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  findForbiddenWord,
  forbiddenFieldHits,
  loadForbiddenWords,
} from '../src/composables/forbiddenWords'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('запрещённые слова на фронтенде', () => {
  it('читает список из настроек QWEN', async () => {
    global.fetch = vi.fn(async () => json({ forbidden_words: ['мат', 'спам'] }))

    expect(await loadForbiddenWords()).toEqual(['мат', 'спам'])
  })

  it('при недоступности настроек не блокирует правку', async () => {
    global.fetch = vi.fn(async () => json({ detail: 'нет связи' }, 500))

    expect(await loadForbiddenWords()).toEqual([])
  })

  it('ищет целое слово без учёта регистра', () => {
    expect(findForbiddenWord('Реклама МАТ', ['мат'])).toBe('мат')
    expect(findForbiddenWord('щит «Мат»', ['мат'])).toBe('мат')
    // Подстрока в другом слове — не совпадение: «торпедо» остаётся.
    expect(findForbiddenWord('матовая поверхность', ['мат'])).toBeNull()
    expect(findForbiddenWord('Реклама Торпедо', ['педо'])).toBeNull()
    expect(findForbiddenWord('велосипедов', ['педо'])).toBeNull()
    // Склеенные слова QWEN («Система ПЕДО» → «СистемаПедо») ловятся по смене регистра.
    expect(findForbiddenWord('СистемаПедо', ['педо'])).toBe('педо')
    expect(findForbiddenWord('педо-щит', ['педо'])).toBe('педо')
    expect(findForbiddenWord('чисто', ['мат'])).toBeNull()
    expect(findForbiddenWord('', ['мат'])).toBeNull()
  })

  it('перечисляет поля с запрещёнными словами', () => {
    const hits = forbiddenFieldHits(
      {
        description: 'Реклама',
        client: 'ООО «Ромашка»',
        brand: 'МАТ',
        tags: 'акция, мат',
      },
      ['мат'],
    )

    expect(hits).toEqual([
      { field: 'brand', word: 'мат' },
      { field: 'tags', word: 'мат', value: 'мат' },
    ])
  })

  it('без списка ничего не блокирует', () => {
    expect(forbiddenFieldHits({ brand: 'МАТ', tags: 'мат' }, [])).toEqual([])
  })

  it('не блокирует слово, внутри которого стоит запрещённое', () => {
    const hits = forbiddenFieldHits(
      {
        description: 'Реклама торпедо и акция',
        client: 'Торпедо',
        brand: 'Торпедо',
        tags: 'торпедо, акция',
      },
      ['педо'],
    )

    expect(hits).toEqual([])
  })
})
