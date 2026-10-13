// @vitest-environment happy-dom
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import {
  LIST_FIELDS,
  TILE_COUNTS,
  fieldText,
  useDisplayStore,
} from '../src/stores/display'

const STORAGE_KEY = 'scene.display.v1'

describe('display store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    setActivePinia(createPinia())
  })

  it('starts from documented defaults', () => {
    const display = useDisplayStore()

    expect(display.tileColumns).toBe(4)
    expect(display.listFields).toEqual(['filename', 'address', 'client'])
    expect(TILE_COUNTS).toContain(display.tileColumns)
  })

  it('drops unknown fields and invalid tile counts from storage', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        tileColumns: 9,
        listFields: ['filename', 'nope', 'client'],
      }),
    )

    const display = useDisplayStore()

    expect(display.tileColumns).toBe(4)
    expect(display.listFields).toEqual(['filename', 'client'])
  })

  it('persists changes and reset() restores the defaults', async () => {
    const display = useDisplayStore()

    display.tileColumns = 6
    display.listFields = ['filename', 'brand']
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY))).toEqual({
      tileColumns: 6,
      listFields: ['filename', 'brand'],
    })

    display.reset()

    expect(display.tileColumns).toBe(4)
    expect(display.listFields).toEqual(['filename', 'address', 'client'])
  })
})

describe('fieldText', () => {
  it('formats the pixel size field', () => {
    expect(fieldText({ width: 1920, height: 1080 }, 'size')).toBe('1920×1080')
    expect(fieldText({ width: null, height: null }, 'size')).toBe('—')
  })

  it('renders a dash for empty values and passes strings through', () => {
    expect(fieldText({ address: '' }, 'address')).toBe('—')
    expect(fieldText({}, 'client')).toBe('—')
    expect(fieldText(null, 'filename')).toBe('—')
    expect(fieldText({ created_at: '2026-05-01T10:00:00' }, 'created_at')).toBe(
      '2026-05-01T10:00:00',
    )
  })

  it('every configurable field has a label', () => {
    for (const field of LIST_FIELDS) {
      expect(field.label).toBeTruthy()
    }
  })
})
