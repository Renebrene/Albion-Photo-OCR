import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

import { fetchSelection, saveSelection } from '../api/client'

// Display settings for the photo grid (number of tile columns, which fields a
// list row shows). Shared by the grid's gear dialog and the technical section.
// They are kept per user on the server (the `display` key of the selection
// state) and mirrored into localStorage, so a login on another machine brings
// the same view back.

// Tile mode: a fixed number of columns, or 'auto' - the grid counts columns
// from its own width, so dragging the panel border reflows the tiles.
export const TILE_COUNTS = [
  { value: 'auto', label: 'Авто (по ширине)' },
  { value: 2, label: '2' },
  { value: 3, label: '3' },
  { value: 4, label: '4' },
  { value: 5, label: '5' },
  { value: 6, label: '6' },
]

// Target tile width used by 'auto': the grid fits as many columns as possible
// while keeping tiles at least this wide.
export const AUTO_TILE_MIN_WIDTH = 190

// Draggable panel sizes (px). Clamped so a panel can never eat the grid.
export const PANEL_LIMITS = { min: 240, max: 620 }
export const SIDE_LIST_LIMITS = { min: 140, max: 640 }

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

const DEFAULT_TILE_COLUMNS = 'auto'
const DEFAULT_PANEL_WIDTH = 340
const DEFAULT_SIDE_LIST_HEIGHT = 300
const DEFAULT_LIST_FIELDS = ['filename', 'address', 'client']
const DEFAULT_DOWNLOAD_NAME_MODE = 'filename'
// The side panels of the photo page (addresses/collections on the left,
// clients/collections on the right). Each can be collapsed to the edge; the
// floating edge button brings it back.
const DEFAULT_SIDE_PANELS_OPEN = true
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
  const clamp = (value, { min, max }) =>
    Math.min(max, Math.max(min, Math.round(Number(value) || min)))

  const tileColumns = ref(DEFAULT_TILE_COLUMNS)
  const listFields = ref([...DEFAULT_LIST_FIELDS])
  const downloadNameMode = ref(DEFAULT_DOWNLOAD_NAME_MODE)
  const leftPanelWidth = ref(DEFAULT_PANEL_WIDTH)
  const rightPanelWidth = ref(DEFAULT_PANEL_WIDTH)
  const sideListHeight = ref(DEFAULT_SIDE_LIST_HEIGHT)
  const leftPanelOpen = ref(DEFAULT_SIDE_PANELS_OPEN)
  const rightPanelOpen = ref(DEFAULT_SIDE_PANELS_OPEN)

  /**
   * Take the settings from a plain object (localStorage or the server),
   * falling back to the defaults for anything missing or unusable.
   */
  function applyState(source) {
    const saved = source && typeof source === 'object' ? source : {}

    tileColumns.value = TILE_COUNTS.some(
      (option) => option.value === saved.tileColumns,
    )
      ? saved.tileColumns
      : DEFAULT_TILE_COLUMNS

    listFields.value =
      Array.isArray(saved.listFields) && saved.listFields.length
        ? saved.listFields.filter((field) =>
            LIST_FIELDS.some((option) => option.value === field),
          )
        : [...DEFAULT_LIST_FIELDS]

    downloadNameMode.value = DOWNLOAD_NAME_MODES.some(
      (option) => option.value === saved.downloadNameMode,
    )
      ? saved.downloadNameMode
      : DEFAULT_DOWNLOAD_NAME_MODE

    leftPanelWidth.value = clamp(
      saved.leftPanelWidth ?? DEFAULT_PANEL_WIDTH,
      PANEL_LIMITS,
    )

    rightPanelWidth.value = clamp(
      saved.rightPanelWidth ?? DEFAULT_PANEL_WIDTH,
      PANEL_LIMITS,
    )

    // Height of the Адреса/Клиенты card; below it sits the Подборки card.
    sideListHeight.value = clamp(
      saved.sideListHeight ?? DEFAULT_SIDE_LIST_HEIGHT,
      SIDE_LIST_LIMITS,
    )

    leftPanelOpen.value =
      typeof saved.leftPanelOpen === 'boolean'
        ? saved.leftPanelOpen
        : DEFAULT_SIDE_PANELS_OPEN

    rightPanelOpen.value =
      typeof saved.rightPanelOpen === 'boolean'
        ? saved.rightPanelOpen
        : DEFAULT_SIDE_PANELS_OPEN
  }

  applyState(loadState())

  function snapshot() {
    return {
      tileColumns: tileColumns.value,
      listFields: [...listFields.value],
      downloadNameMode: downloadNameMode.value,
      leftPanelOpen: leftPanelOpen.value,
      rightPanelOpen: rightPanelOpen.value,
      leftPanelWidth: leftPanelWidth.value,
      rightPanelWidth: rightPanelWidth.value,
      sideListHeight: sideListHeight.value,
    }
  }

  let serverTimer = null

  function persist() {
    const data = snapshot()

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch {
      // storage disabled (private mode): keep the value for this session only
    }

    // The settings belong to the user, not to the browser: the same blob is
    // kept on the server (under the `display` key of the selection state) so a
    // login elsewhere brings them back. Debounced, failures are ignored.
    clearTimeout(serverTimer)
    serverTimer = setTimeout(() => {
      try {
        saveSelection({ display: data }).catch(() => {})
      } catch {
        // No session or no network: the local copy is all we have.
      }
    }, 800)
  }

  /** Restore this user's settings after a login. */
  async function loadFromServer() {
    try {
      const payload = await fetchSelection()
      const remote = payload && payload.state ? payload.state.display : null

      if (remote && typeof remote === 'object') {
        applyState(remote)
      }
    } catch {
      // Not authenticated (or the endpoint is unavailable): keep the local ones.
    }
  }

  watch(
    [
      tileColumns,
      listFields,
      downloadNameMode,
      leftPanelOpen,
      rightPanelOpen,
      leftPanelWidth,
      rightPanelWidth,
      sideListHeight,
    ],
    persist,
    { deep: true },
  )

  function reset() {
    tileColumns.value = DEFAULT_TILE_COLUMNS
    listFields.value = [...DEFAULT_LIST_FIELDS]
    downloadNameMode.value = DEFAULT_DOWNLOAD_NAME_MODE
    leftPanelOpen.value = DEFAULT_SIDE_PANELS_OPEN
    rightPanelOpen.value = DEFAULT_SIDE_PANELS_OPEN
    leftPanelWidth.value = DEFAULT_PANEL_WIDTH
    rightPanelWidth.value = DEFAULT_PANEL_WIDTH
    sideListHeight.value = DEFAULT_SIDE_LIST_HEIGHT
  }

  function resizePanel(side, delta) {
    if (side === 'left') {
      leftPanelWidth.value = clamp(leftPanelWidth.value + delta, PANEL_LIMITS)
    } else {
      // Dragging the right border right moves it right: the width grows with
      // the negative delta, because the panel sits at the other edge.
      rightPanelWidth.value = clamp(rightPanelWidth.value - delta, PANEL_LIMITS)
    }
  }

  function resizeSideList(delta) {
    sideListHeight.value = clamp(sideListHeight.value + delta, SIDE_LIST_LIMITS)
  }

  return {
    tileColumns,
    listFields,
    downloadNameMode,
    leftPanelOpen,
    rightPanelOpen,
    leftPanelWidth,
    rightPanelWidth,
    sideListHeight,
    resizePanel,
    resizeSideList,
    reset,
    loadFromServer,
  }
})

// Characters a file name may not contain on the common platforms.
const UNSAFE_NAME_CHARS = /[\\/:*?"<>|\u0000-\u001f]/g

/**
 * Sort photo rows for the grid (item: sorting with an up/down arrow).
 *
 * `date` uses the capture date when the photo has one and the upload time
 * otherwise; the other keys are compared as text in Russian.
 */
export function sortPhotos(items, key, direction = 'asc') {
  const factor = direction === 'desc' ? -1 : 1
  const rows = Array.isArray(items) ? [...items] : []

  return rows.sort((a, b) => {
    if (key === 'date') {
      const av = a.taken_at || a.created_at || ''
      const bv = b.taken_at || b.created_at || ''

      if (av === bv) return 0

      return (av < bv ? -1 : 1) * factor
    }

    const av = (a[key] || '').toString()
    const bv = (b[key] || '').toString()

    return av.localeCompare(bv, 'ru') * factor
  })
}

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
