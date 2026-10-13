import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

// Display settings for the photo grid (number of tile columns, which fields a
// list row shows). Shared by the grid's gear dialog and the technical section,
// persisted in localStorage only — nothing is sent to the server.

export const TILE_COUNTS = [2, 3, 4, 5, 6]

// Fields that exist on the `/v1/photos` row (see app/api/repository.py).
export const LIST_FIELDS = [
  { value: 'filename', label: 'Имя файла' },
  { value: 'address', label: 'Адрес (распознавание)' },
  { value: 'client', label: 'Клиент' },
  { value: 'brand', label: 'Бренд' },
  { value: 'category', label: 'Категория' },
  { value: 'size', label: 'Размер, px' },
  { value: 'created_at', label: 'Дата загрузки' },
  { value: 'taken_at', label: 'Дата съёмки' },
]

// How a downloaded file is named (item 11b): the original name, or the
// address it belongs to (simplified alias / normalised legal name) prefixed
// to the original name so two photos of one address cannot overwrite itself.
export const DOWNLOAD_NAME_MODES = [
  { value: 'filename', label: 'Имя файла (как сейчас)' },
  { value: 'simple', label: 'Адрес (упрощённый / alias)' },
  { value: 'legal', label: 'Адрес (юридический)' },
]

const DEFAULT_TILE_COLUMNS = 4
const DEFAULT_LIST_FIELDS = ['filename', 'address', 'client']
const DEFAULT_DOWNLOAD_NAME_MODE = 'filename'
const STORAGE_KEY = 'scene.display.v1'

function loadState() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    if (parsed && typeof parsed === 'object') return parsed
  } catch {
    // unreadable or corrupt storage -> fall back to defaults
  }
  return {}
}

export const useDisplayStore = defineStore('display', () => {
  const saved = loadState()

  const tileColumns = ref(
    TILE_COUNTS.includes(saved.tileColumns)
      ? saved.tileColumns
      : DEFAULT_TILE_COLUMNS,
  )

  const listFields = ref(
    Array.isArray(saved.listFields) && saved.listFields.length
      ? saved.listFields.filter((field) =>
          LIST_FIELDS.some((option) => option.value === field),
        )
      : [...DEFAULT_LIST_FIELDS],
  )

  const downloadNameMode = ref(
    DOWNLOAD_NAME_MODES.some((option) => option.value === saved.downloadNameMode)
      ? saved.downloadNameMode
      : DEFAULT_DOWNLOAD_NAME_MODE,
  )

  function persist() {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          tileColumns: tileColumns.value,
          listFields: listFields.value,
          downloadNameMode: downloadNameMode.value,
        }),
      )
    } catch {
      // storage disabled (private mode): keep the value for this session only
    }
  }

  watch([tileColumns, listFields, downloadNameMode], persist, { deep: true })

  function reset() {
    tileColumns.value = DEFAULT_TILE_COLUMNS
    listFields.value = [...DEFAULT_LIST_FIELDS]
    downloadNameMode.value = DEFAULT_DOWNLOAD_NAME_MODE
  }

  return { tileColumns, listFields, downloadNameMode, reset }
})

// Characters a file name may not contain on the common platforms.
const UNSAFE_NAME_CHARS = /[\\/:*?"<>|\u0000-\u001f]/g

/** Make one address name safe to use as part of a file name. */
export function safeFilePart(value) {
  if (value === null || value === undefined) return ''

  return String(value).replace(UNSAFE_NAME_CHARS, '_').replace(/\s+/g, ' ').trim()
}

/**
 * File name for a download (item 11b).
 *
 * With mode 'filename' the original name is returned untouched. Otherwise the
 * address name is prefixed ("<address>__<original name>") so photos of the
 * same address stay unique instead of overwriting each other; a photo whose
 * address is not mapped yet keeps its original name.
 */
export function downloadFileName(photo, mode = DEFAULT_DOWNLOAD_NAME_MODE) {
  const original = (photo && photo.filename) || 'photo.jpg'

  if (mode === 'filename') return original

  const address =
    mode === 'simple'
      ? safeFilePart(photo && photo.simple_address)
      : safeFilePart(photo && photo.legal_address)

  const prefix = address || safeFilePart(photo && photo.address)

  return prefix ? `${prefix}__${original}` : original
}

/** Human-readable value of one list field for a photo row. */
export function fieldText(photo, key) {
  if (!photo) return '—'
  if (key === 'size') {
    return photo.width && photo.height
      ? `${photo.width}×${photo.height}`
      : '—'
  }
  const value = photo[key]
  if (value === null || value === undefined || value === '') return '—'
  // Dates are shown by day only: the time of an EXIF stamp is noise here.
  if (key === 'taken_at' || key === 'created_at') {
    return String(value).slice(0, 10)
  }
  return value
}
