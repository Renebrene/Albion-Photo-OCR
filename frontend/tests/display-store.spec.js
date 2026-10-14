// @vitest-environment happy-dom
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import {
  DOWNLOAD_NAME_MODES,
  LIST_FIELDS,
  PANEL_LIMITS,
  SIDE_LIST_LIMITS,
  TILE_COUNTS,
  downloadFileName,
  fieldText,
  safeFilePart,
  sortPhotos,
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

    expect(display.tileColumns).toBe('auto')
    expect(display.listFields).toEqual(['filename', 'address', 'client'])
    expect(TILE_COUNTS.map((option) => option.value)).toContain(
      display.tileColumns,
    )
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

    expect(display.tileColumns).toBe('auto')
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
      downloadNameMode: 'filename',
      leftPanelOpen: true,
      rightPanelOpen: true,
      leftPanelWidth: 340,
      rightPanelWidth: 340,
      sideListHeight: 300,
    })

    display.reset()

    expect(display.tileColumns).toBe('auto')
    expect(display.listFields).toEqual(['filename', 'address', 'client'])
    expect(display.downloadNameMode).toBe('filename')
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
    expect(fieldText({ client: 'Яндекс' }, 'client')).toBe('Яндекс')
  })

  it('shows dates by day only', () => {
    expect(fieldText({ created_at: '2026-05-01T10:00:00' }, 'created_at')).toBe(
      '2026-05-01',
    )
    expect(fieldText({ taken_at: '2026-04-30T08:15:02' }, 'taken_at')).toBe(
      '2026-04-30',
    )
    expect(fieldText({ taken_at: null }, 'taken_at')).toBe('—')
  })

  it('every configurable field has a label', () => {
    for (const field of LIST_FIELDS) {
      expect(field.label).toBeTruthy()
    }
  })
})


describe('download file names (item 11b)', () => {
  const photo = {
    filename: 'Комарова13_11.JPG',
    address: '78_v33',
    simple_address: 'Мира 1',
    legal_address: 'ООО «Ромашка», ул. Мира, 1',
  }

  it('keeps the original name by default', () => {
    expect(downloadFileName(photo)).toBe('Комарова13_11.JPG')
    expect(downloadFileName(photo, 'filename')).toBe('Комарова13_11.JPG')
    expect(DOWNLOAD_NAME_MODES.map((mode) => mode.value)).toContain('filename')
  })

  it('prefixes the simplified address so names stay unique', () => {
    expect(downloadFileName(photo, 'simple')).toBe(
      'Мира 1__Комарова13_11.JPG',
    )
  })

  it('normalises the legal address and strips unsafe characters', () => {
    expect(downloadFileName(photo, 'legal')).toBe(
      'ООО «Ромашка», ул. Мира, 1__Комарова13_11.JPG',
    )

    // Unsafe file-name characters become underscores, whitespace collapses.
    expect(
      downloadFileName(
        { filename: 'a.jpg', legal_address: 'ООО "Р/С" * тест' },
        'legal',
      ),
    ).toBe('ООО _Р_С_ _ тест__a.jpg')
  })

  it('falls back to the recognised id, then to the original name', () => {
    expect(
      downloadFileName({ filename: 'a.jpg', address: '83_v33' }, 'simple'),
    ).toBe('83_v33__a.jpg')

    expect(downloadFileName({ filename: 'a.jpg' }, 'legal')).toBe('a.jpg')
    expect(downloadFileName({}, 'simple')).toBe('photo.jpg')
    expect(downloadFileName(null, 'legal')).toBe('photo.jpg')
  })

  it('safeFilePart collapses whitespace and handles empty values', () => {
    expect(safeFilePart('  ул.   Мира,  1 ')).toBe('ул. Мира, 1')
    expect(safeFilePart(null)).toBe('')
    expect(safeFilePart(42)).toBe('42')
  })

  it('persists the chosen mode', async () => {
    const display = useDisplayStore()

    expect(display.downloadNameMode).toBe('filename')

    display.downloadNameMode = 'legal'
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(JSON.parse(window.localStorage.getItem(STORAGE_KEY)).downloadNameMode).toBe(
      'legal',
    )

    display.reset()
    expect(display.downloadNameMode).toBe('filename')
  })

  it('ignores an unknown stored mode', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ downloadNameMode: 'nonsense' }),
    )

    expect(useDisplayStore().downloadNameMode).toBe('filename')
  })
})


describe('grid sorting', () => {
  const rows = [
    { photo_id: 'b', filename: 'б.jpg', client: 'Бета', taken_at: '2026-05-01T10:00:00' },
    { photo_id: 'a', filename: 'а.jpg', client: 'Альфа', created_at: '2026-01-01T10:00:00' },
    { photo_id: 'c', filename: 'в.jpg', client: null, taken_at: '2026-03-01T10:00:00' },
  ]

  it('sorts text fields in both directions', () => {
    expect(sortPhotos(rows, 'filename').map((r) => r.photo_id)).toEqual(['a', 'b', 'c'])
    expect(sortPhotos(rows, 'filename', 'desc').map((r) => r.photo_id)).toEqual([
      'c',
      'b',
      'a',
    ])
  })

  it('sorts by date using the capture date, falling back to the upload time', () => {
    // a has no capture date -> its upload time (January) puts it first.
    expect(sortPhotos(rows, 'date').map((r) => r.photo_id)).toEqual(['a', 'c', 'b'])
    expect(sortPhotos(rows, 'date', 'desc').map((r) => r.photo_id)).toEqual([
      'b',
      'c',
      'a',
    ])
  })

  it('treats a missing field as an empty string and never mutates the input', () => {
    const sorted = sortPhotos(rows, 'client')

    expect(sorted.map((r) => r.client)).toEqual([null, 'Альфа', 'Бета'])
    expect(rows.map((r) => r.photo_id)).toEqual(['b', 'a', 'c'])
  })

  it('tolerates a missing list', () => {
    expect(sortPhotos(null, 'filename')).toEqual([])
  })
})


describe('side panels of the photo page', () => {
  beforeEach(() => {
    window.localStorage.clear()
    setActivePinia(createPinia())
  })

  it('are open by default and remember being collapsed', async () => {
    const display = useDisplayStore()

    expect(display.leftPanelOpen).toBe(true)
    expect(display.rightPanelOpen).toBe(true)

    display.leftPanelOpen = false
    display.rightPanelOpen = false
    await new Promise((resolve) => setTimeout(resolve, 0))

    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY))
    expect(stored.leftPanelOpen).toBe(false)
    expect(stored.rightPanelOpen).toBe(false)

    display.reset()
    expect(display.leftPanelOpen).toBe(true)
    expect(display.rightPanelOpen).toBe(true)
  })

  it('honour stored false values', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ leftPanelOpen: false, rightPanelOpen: true }),
    )

    const display = useDisplayStore()
    expect(display.leftPanelOpen).toBe(false)
    expect(display.rightPanelOpen).toBe(true)
  })
})


describe('draggable panel sizes', () => {
  beforeEach(() => {
    window.localStorage.clear()
    setActivePinia(createPinia())
  })

  it('starts from the documented sizes', () => {
    const display = useDisplayStore()

    expect(display.leftPanelWidth).toBe(340)
    expect(display.rightPanelWidth).toBe(340)
    expect(display.sideListHeight).toBe(300)
  })

  it('moves the left border with the cursor and clamps it', () => {
    const display = useDisplayStore()

    display.resizePanel('left', 60)
    expect(display.leftPanelWidth).toBe(400)

    // Never below the minimum or above the maximum.
    display.resizePanel('left', -10_000)
    expect(display.leftPanelWidth).toBe(PANEL_LIMITS.min)

    display.resizePanel('left', 10_000)
    expect(display.leftPanelWidth).toBe(PANEL_LIMITS.max)
  })

  it('grows the right panel when its border moves left', () => {
    const display = useDisplayStore()

    // The right panel sits on the opposite edge, so a negative delta grows it.
    display.resizePanel('right', -40)

    expect(display.rightPanelWidth).toBe(380)
  })

  it('resizes the list/collections divider inside a panel', () => {
    const display = useDisplayStore()

    display.resizeSideList(50)
    expect(display.sideListHeight).toBe(350)

    display.resizeSideList(-10_000)
    expect(display.sideListHeight).toBe(SIDE_LIST_LIMITS.min)
  })

  it('ignores nonsense stored sizes and keeps sane ones', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        leftPanelWidth: 'широкая',
        rightPanelWidth: 500,
        sideListHeight: 1e9,
      }),
    )

    const display = useDisplayStore()

    expect(display.leftPanelWidth).toBe(PANEL_LIMITS.min)
    expect(display.rightPanelWidth).toBe(500)
    expect(display.sideListHeight).toBe(SIDE_LIST_LIMITS.max)
  })

  it('persists the sizes and restores the defaults', async () => {
    const display = useDisplayStore()

    display.resizePanel('left', 40)
    display.resizeSideList(40)
    await new Promise((resolve) => setTimeout(resolve, 0))

    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY))
    expect(stored.leftPanelWidth).toBe(380)
    expect(stored.sideListHeight).toBe(340)

    display.reset()
    expect(display.leftPanelWidth).toBe(340)
    expect(display.sideListHeight).toBe(300)
  })
})
