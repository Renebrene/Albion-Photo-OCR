// ID слепка из имени папки: транслит, лимит 64 символа, уникальность.
//
// Сервер принимает только ^[A-Za-z0-9._-]{1,64}$ — кириллица и длинные имена
// давали отказ («String should have at most 64 characters» либо «ID может
// содержать буквы…»). Здесь проверяется, что автоподстановка всегда даёт
// допустимый и не занятый ID.

import { describe, expect, it } from 'vitest'

import {
  FINGERPRINT_ID_MAX,
  FINGERPRINT_ID_RE,
  VERSION_SUFFIX,
  assignBatchIds,
  slugifyName,
  uniqueId,
} from '../src/utils/fingerprint-id'

describe('транслит имени папки в ID', () => {
  it('переводит кириллицу и сохраняет суффикс версии', () => {
    expect(slugifyName('Менжинского 2', { suffix: VERSION_SUFFIX })).toBe(
      'menzhinskogo_2_v33',
    )
  })

  it('сохраняет точку и цифры: 16.02 остаётся 16.02', () => {
    expect(slugifyName('16.02', { suffix: VERSION_SUFFIX })).toBe('16.02_v33')
  })

  it('запятые и пробелы становятся одним подчёркиванием', () => {
    expect(slugifyName('10,12 таганрог', { suffix: VERSION_SUFFIX })).toBe(
      '10_12_taganrog_v33',
    )
  })

  it('латиница и цифры не меняются', () => {
    expect(slugifyName('Shop 5', { suffix: VERSION_SUFFIX })).toBe('shop_5_v33')
  })

  it('пустое имя даёт запасной ID, а не пустую строку', () => {
    expect(slugifyName('', { suffix: VERSION_SUFFIX })).toBe('fp_v33')
    expect(slugifyName('   ', { suffix: VERSION_SUFFIX })).toBe('fp_v33')
  })

  it('длинное имя обрезается под лимит вместе с суффиксом', () => {
    const id = slugifyName('а'.repeat(200), { suffix: VERSION_SUFFIX })

    expect(id.length).toBe(FINGERPRINT_ID_MAX)
    expect(id.endsWith(VERSION_SUFFIX)).toBe(true)
    expect(FINGERPRINT_ID_RE.test(id)).toBe(true)
  })

  it('после обрезки не оставляет разделитель в конце основы', () => {
    const id = slugifyName(`${'a'.repeat(59)} б`, { suffix: VERSION_SUFFIX })

    expect(id).toBe(`${'a'.repeat(59)}_v33`)
    expect(id).not.toContain('__')
  })
})

describe('уникальность ID', () => {
  it('свободный ID не меняется', () => {
    expect(uniqueId('78_v33', ['90_v33'])).toBe('78_v33')
  })

  it('занятый ID получает суффикс _1, потом _2', () => {
    expect(uniqueId('78_v33', ['78_v33'])).toBe('78_v33_1')
    expect(uniqueId('78_v33', ['78_v33', '78_v33_1'])).toBe('78_v33_2')
  })

  it('суффикс учитывает лимит длины', () => {
    const base = 'a'.repeat(FINGERPRINT_ID_MAX)
    const id = uniqueId(base, [base])

    expect(id.length).toBeLessThanOrEqual(FINGERPRINT_ID_MAX)
    expect(FINGERPRINT_ID_RE.test(id)).toBe(true)
    expect(id).not.toBe(base)
  })
})

describe('ID по умолчанию для папок батч-сборки', () => {
  const dirs = [
    { name: 'Менжинского 2', path: '/photos/Менжинского 2', photos: 3 },
    { name: 'Менжинского 2', path: '/photos/Менжинского 2 (копия)', photos: 3 },
    { name: '78', path: '/photos/78', photos: 5 },
  ]

  it('разводит совпадения между папками и с существующими слепками', () => {
    const ids = assignBatchIds(dirs, ['78_v33'])

    expect(ids).toEqual({
      '/photos/Менжинского 2': 'menzhinskogo_2_v33',
      '/photos/Менжинского 2 (копия)': 'menzhinskogo_2_v33_1',
      // 78_v33 уже занят реестром: сборка идёт с replace и перезаписала бы его.
      '/photos/78': '78_v33_1',
    })
  })

  it('все ID допустимы по формату сервера', () => {
    for (const id of Object.values(assignBatchIds(dirs, []))) {
      expect(FINGERPRINT_ID_RE.test(id)).toBe(true)
    }
  })
})
