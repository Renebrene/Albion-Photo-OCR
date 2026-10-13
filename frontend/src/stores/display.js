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

const DEFAULT_TILE_COLUMNS = 4
const DEFAULT_LIST_FIELDS = ['filename', 'address', 'client']
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

  function persist() {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          tileColumns: tileColumns.value,
          listFields: listFields.value,
        }),
      )
    } catch {
      // storage disabled (private mode): keep the value for this session only
    }
  }

  watch([tileColumns, listFields], persist, { deep: true })

  function reset() {
    tileColumns.value = DEFAULT_TILE_COLUMNS
    listFields.value = [...DEFAULT_LIST_FIELDS]
  }

  return { tileColumns, listFields, reset }
})

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
