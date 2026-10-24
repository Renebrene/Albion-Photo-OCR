import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { fetchSelection, getToken, saveSelection } from '../api/client'

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
  { value: 'legal_address', label: 'Юридический адрес' },
  { value: 'simple_address', label: 'Упрощённый адрес' },
  { value: 'client', label: 'Клиент' },
  { value: 'brand', label: 'Бренд' },
  { value: 'category', label: 'Категория' },
  { value: 'size', label: 'Размер, px' },
  { value: 'created_at', label: 'Дата загрузки' },
  { value: 'taken_at', label: 'Дата съёмки' },
  { value: 'taken_time', label: 'Время съёмки' },
]

// How a downloaded or zipped file is named (item 11b):
//   filename — exactly as it came from the inspected folder;
//   legal    — "<юридический адрес> (<итерация>).<ext>", never the original
//              name. The iteration is the trailing "(N)" of the original
//              name (photos arrive as "… (10).JPG") or the position in the
//              current batch.
export const DOWNLOAD_NAME_MODES = [
  { value: 'filename', label: 'Имя файла — как в папке инспекции' },
  { value: 'legal', label: 'Юридическое имя (итерация)' },
]

/**
 * A saved mode that still exists, or the default.
 *
 * The old "simple" mode (address alias prefixed to the original name) was
 * replaced by the legal name; a saved "simple" is read as "legal" so the
 * address does not silently disappear from the names.
 */
function normaliseDownloadNameMode(value) {
  if (value === 'simple') return 'legal'

  return DOWNLOAD_NAME_MODES.some((option) => option.value === value)
    ? value
    : DEFAULT_DOWNLOAD_NAME_MODE
}

// Как складываются адреса и клиенты: ○ объединение, △ приоритет адресов,
// □ приоритет клиентов. Режим живёт в настройках пользователя.
export const ADDRESS_CLIENT_MODES = [
  { value: 'union', symbol: '○', label: 'Адреса ИЛИ клиенты' },
  { value: 'address', symbol: '△', label: 'Приоритет адресов' },
  { value: 'client', symbol: '□', label: 'Приоритет клиентов' },
]

const DEFAULT_TILE_COLUMNS = 'auto'
const DEFAULT_PANEL_WIDTH = 340
const DEFAULT_SIDE_LIST_HEIGHT = 300
const DEFAULT_LIST_FIELDS = ['filename', 'address', 'client']
// Плитка грида: исходное имя файла можно скрыть, оставив адрес и метаданные.
const DEFAULT_TILE_SHOW_ADDRESS_NAME = true
const DEFAULT_TILE_SHOW_FILENAME = true
const DEFAULT_DOWNLOAD_NAME_MODE = 'filename'
// The side panels of the photo page (addresses/collections on the left,
// clients/collections on the right). Each can be collapsed to the edge; the
// floating edge button brings it back.
const DEFAULT_SIDE_PANELS_OPEN = true
const STORAGE_KEY = 'scene.display.v1'

// Настройки отображения — за пользователем, а не за браузером: ключ
// localStorage получает суффикс с id пользователя.
let storageSuffix = ''

function storageKey() {
  return storageSuffix ? `${STORAGE_KEY}.u${storageSuffix}` : STORAGE_KEY
}

function baseStorageKey() {
  return `${storageKey()}.base`
}

function loadState({ migrate = false } = {}) {
  try {
    const key = storageKey()
    let raw = window.localStorage.getItem(key)

    // Первый вход после обновления: однажды переносим старый общий ключ
    // в личный ключ пользователя и убираем общий.
    if (!raw && migrate && storageSuffix) {
      const legacy = window.localStorage.getItem(STORAGE_KEY)
      if (legacy) {
        window.localStorage.setItem(key, legacy)
        window.localStorage.removeItem(STORAGE_KEY)
        raw = legacy
      }
    }

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
  const tileShowFilename = ref(DEFAULT_TILE_SHOW_FILENAME)
  // Короткое имя адреса в плитке. Выключено — видно реальное имя файла:
  // иногда нужно смотреть подборку именно по именам.
  const tileShowAddressName = ref(DEFAULT_TILE_SHOW_ADDRESS_NAME)
  // Источник даты для фильтра периода: дата съёмки (по умолчанию) или загрузки.
  const dateFilterMode = ref('capture')
  const addressClientMode = ref('union')
  // Desired (persisted) widths. The effective width shown in the grid is
  // clamped to the current window and is never written back to storage.
  const leftPanelWidth = ref(DEFAULT_PANEL_WIDTH)
  const rightPanelWidth = ref(DEFAULT_PANEL_WIDTH)
  const panelViewport = ref(0)
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

    if (Array.isArray(saved.listFields)) {
      const known = saved.listFields.filter((field) =>
        LIST_FIELDS.some((option) => option.value === field),
      )

      if (known.length) {
        // Явный пустой список — это выбор пользователя «без полей».
        listFields.value = known
      } else if (saved.listFields.length) {
        // Все сохранённые значения устарели — возвращаем умолчания.
        listFields.value = [...DEFAULT_LIST_FIELDS]
      } else {
        listFields.value = []
      }
    } else {
      listFields.value = [...DEFAULT_LIST_FIELDS]
    }

    downloadNameMode.value = normaliseDownloadNameMode(saved.downloadNameMode)

    addressClientMode.value = ADDRESS_CLIENT_MODES.some(
      (option) => option.value === saved.addressClientMode,
    )
      ? saved.addressClientMode
      : 'union'

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

    tileShowFilename.value =
      typeof saved.tileShowFilename === 'boolean'
        ? saved.tileShowFilename
        : DEFAULT_TILE_SHOW_FILENAME

    tileShowAddressName.value =
      typeof saved.tileShowAddressName === 'boolean'
        ? saved.tileShowAddressName
        : DEFAULT_TILE_SHOW_ADDRESS_NAME

    dateFilterMode.value =
      saved.dateFilterMode === 'upload' ? 'upload' : 'capture'
  }

  applyState(loadState())

  /**
   * Не дать панелям съесть грид: суммарная ширина открытых панелей
   * ограничена так, чтобы под грид осталось хотя бы 420 px.
   */
  function panelWidthLimit(viewportWidth = panelViewport.value) {
    if (!viewportWidth) return PANEL_LIMITS.max

    const openCount =
      Number(leftPanelOpen.value) + Number(rightPanelOpen.value)

    if (!openCount) return PANEL_LIMITS.max

    const minGrid = 420
    const handles = 24
    const available = Math.max(
      PANEL_LIMITS.min * openCount,
      viewportWidth - minGrid - handles,
    )

    return Math.min(
      PANEL_LIMITS.max,
      Math.max(PANEL_LIMITS.min, Math.floor(available / openCount)),
    )
  }

  /**
   * Apply the window constraint for RENDERING only.
   *
   * The saved widths stay untouched, so opening the page on a narrow screen
   * no longer overwrites the user's layout with shrunken values.
   */
  function fitPanels(viewportWidth = window.innerWidth || 0) {
    panelViewport.value = Number(viewportWidth) || 0
  }

  const leftPanelWidthEffective = computed(() =>
    Math.min(leftPanelWidth.value, panelWidthLimit()),
  )
  const rightPanelWidthEffective = computed(() =>
    Math.min(rightPanelWidth.value, panelWidthLimit()),
  )

  function snapshot() {
    return {
      tileColumns: tileColumns.value,
      listFields: [...listFields.value],
      downloadNameMode: downloadNameMode.value,
      tileShowFilename: tileShowFilename.value,
      tileShowAddressName: tileShowAddressName.value,
      dateFilterMode: dateFilterMode.value,
      addressClientMode: addressClientMode.value,
      leftPanelOpen: leftPanelOpen.value,
      rightPanelOpen: rightPanelOpen.value,
      leftPanelWidth: leftPanelWidth.value,
      rightPanelWidth: rightPanelWidth.value,
      sideListHeight: sideListHeight.value,
    }
  }

  // Base (starting) state: a snapshot of the settings that the installation is
  // known to work with. «Вернуть базовые» restores it - the 100 % working
  // layout - and it can be downloaded or loaded from a file as a backup.
  function loadBase({ migrate = false } = {}) {
    try {
      const key = baseStorageKey()
      let raw = window.localStorage.getItem(key)

      if (!raw && migrate && storageSuffix) {
        const legacy = window.localStorage.getItem(`${STORAGE_KEY}.base`)

        if (legacy) {
          window.localStorage.setItem(key, legacy)
          window.localStorage.removeItem(`${STORAGE_KEY}.base`)
          raw = legacy
        }
      }

      const parsed = raw ? JSON.parse(raw) : null

      if (parsed && typeof parsed === 'object') return parsed
    } catch {
      // unreadable storage -> no base yet
    }

    return null
  }

  const base = ref(loadBase())

  function saveAsBase() {
    const data = snapshot()

    base.value = data

    try {
      window.localStorage.setItem(baseStorageKey(), JSON.stringify(data))
    } catch {
      // private mode: the base lives for this session only
    }

    try {
      saveSelection({ display_base: data }).catch(() => {})
    } catch {
      // offline: the local copy is enough
    }
  }

  /** Back to the base state (or to the built-in defaults when none was saved). */
  function restoreBase() {
    applyState(base.value || {})
    persist()
  }

  function adoptBase(source) {
    applyState(source)
    saveAsBase()
  }

  let serverTimer = null
  // Гость видит грид, но настройки сайта за ним не сохраняются.
  let persistenceEnabled = true

  function setPersistence(enabled) {
    persistenceEnabled = Boolean(enabled)
  }

  function persist() {
    if (!persistenceEnabled) return

    const data = snapshot()

    try {
      window.localStorage.setItem(storageKey(), JSON.stringify(data))
    } catch {
      // storage disabled (private mode): keep the value for this session only
    }

    // The settings belong to the user, not to the browser: the same blob is
    // kept on the server (under the `display` key of the selection state) so a
    // login elsewhere brings them back. Debounced, failures are ignored.
    //
    // Capture BOTH the user key and the token now: another tab may log in as
    // someone else before the timer fires, and the token is read at send time.
    const scheduledKey = storageKey()
    const scheduledToken = getToken()
    clearTimeout(serverTimer)
    serverTimer = setTimeout(() => {
      serverTimer = null

      if (
        storageKey() !== scheduledKey
        || getToken() !== scheduledToken
      ) {
        return
      }

      try {
        saveSelection({ display: data }).catch(() => {})
      } catch {
        // No session or no network: the local copy is all we have.
      }
    }, 800)
  }

  /** Immediately persist the pending change (logout, page hide). */
  async function flush() {
    if (serverTimer !== null) {
      clearTimeout(serverTimer)
      serverTimer = null
    }

    if (!persistenceEnabled) return

    try {
      // keepalive lets the small settings blob survive page teardown; a plain
      // fetch is aborted and then the older server copy wins on next login.
      await saveSelection({ display: snapshot() }, { keepalive: true })
    } catch {
      // Offline or logged out: the local copy is all we have.
    }
  }

  /**
   * Switch to a user's local settings.
   *
   * `migrate` moves the old global key into this user's key once; a Guest and
   * the next user never inherit someone else's layout.
   */
  function setUserKey(key, { migrate = false } = {}) {
    // A pending save belongs to the previous user: drop it before switching.
    if (serverTimer !== null) {
      clearTimeout(serverTimer)
      serverTimer = null
    }

    storageSuffix = key ? String(key) : ''
    applyState(loadState({ migrate }))
    base.value = loadBase({ migrate })
  }

  /** Restore this user's settings after a login. */
  async function loadFromServer() {
    try {
      const payload = await fetchSelection()
      const state = payload && payload.state ? payload.state : {}

      if (state.display && typeof state.display === 'object') {
        applyState(state.display)
      }

      if (state.display_base && typeof state.display_base === 'object') {
        base.value = state.display_base
      }
    } catch {
      // Not authenticated (or the endpoint is unavailable): keep the local ones.
    }
  }

  // Открыли/закрыли панель — сразу проверяем, что грид не остался нулевым.
  watch([leftPanelOpen, rightPanelOpen], () => fitPanels())

  watch(
    [
      tileColumns,
      listFields,
      downloadNameMode,
      tileShowFilename,
      tileShowAddressName,
      dateFilterMode,
      addressClientMode,
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
    tileShowFilename.value = DEFAULT_TILE_SHOW_FILENAME
    tileShowAddressName.value = DEFAULT_TILE_SHOW_ADDRESS_NAME
    dateFilterMode.value = 'capture'
    addressClientMode.value = 'union'
    leftPanelOpen.value = DEFAULT_SIDE_PANELS_OPEN
    rightPanelOpen.value = DEFAULT_SIDE_PANELS_OPEN
    leftPanelWidth.value = DEFAULT_PANEL_WIDTH
    rightPanelWidth.value = DEFAULT_PANEL_WIDTH
    sideListHeight.value = DEFAULT_SIDE_LIST_HEIGHT
  }

  function resizePanel(side, delta) {
    if (side === 'left') {
      // Start from the width the user actually sees (may be window-clamped).
      leftPanelWidth.value = clamp(
        leftPanelWidthEffective.value + delta,
        PANEL_LIMITS,
      )
    } else {
      // Dragging the right border right moves it right: the width grows with
      // the negative delta, because the panel sits at the other edge.
      rightPanelWidth.value = clamp(
        rightPanelWidthEffective.value - delta,
        PANEL_LIMITS,
      )
    }
  }

  function resizeSideList(delta) {
    sideListHeight.value = clamp(sideListHeight.value + delta, SIDE_LIST_LIMITS)
  }

  return {
    tileColumns,
    listFields,
    downloadNameMode,
    tileShowFilename,
    tileShowAddressName,
    dateFilterMode,
    addressClientMode,
    leftPanelOpen,
    rightPanelOpen,
    leftPanelWidth,
    rightPanelWidth,
    leftPanelWidthEffective,
    rightPanelWidthEffective,
    sideListHeight,
    resizePanel,
    resizeSideList,
    fitPanels,
    reset,
    setPersistence,
    setUserKey,
    flush,
    loadFromServer,
    // Base (starting) state: reserve, restore, adopt from a file.
    base,
    saveAsBase,
    restoreBase,
    adoptBase,
    snapshot,
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

    // «По адресу» сортирует по видимому названию (override > справочник >
    // технический id), иначе исправленный адрес не менял бы порядок.
    const value = key === 'address'
      ? (row) => row.simple_address || row.legal_address || row.address || ''
      : (row) => row[key] || ''

    const av = value(a).toString()
    const bv = value(b).toString()

    return av.localeCompare(bv, 'ru') * factor
  })
}

/** Make one address name safe to use as part of a file name. */
export function safeFilePart(value) {
  if (value === null || value === undefined) return ''

  return String(value).replace(UNSAFE_NAME_CHARS, '_').replace(/\s+/g, ' ').trim()
}

// Trailing copy index of a source file: "…154 А (10).JPG" -> 10.
const ITERATION_RE = /\((\d{1,4})\)\s*$/

function splitFileName(value) {
  const name = String(value || '')
  const dot = name.lastIndexOf('.')

  return dot > 0
    ? { stem: name.slice(0, dot), ext: name.slice(dot) }
    : { stem: name, ext: '' }
}

/**
 * File name for a download or a ZIP entry (item 11b).
 *
 * 'filename' returns the name as it came from the inspected folder.
 *
 * 'legal' returns "<юридический адрес> (<итерация>)<ext>" and never the
 * original name. The iteration is the trailing "(N)" of the original name
 * (photos arrive as "… (10).JPG"); when there is none, `iteration` (the
 * position in the current batch, 1-based) is used, and a lone file gets 1.
 * A photo without a mapped address keeps its original name — an invented
 * address would be worse than the honest file name.
 */
export function downloadFileName(
  photo,
  mode = DEFAULT_DOWNLOAD_NAME_MODE,
  iteration,
) {
  const original = (photo && photo.filename) || 'photo.jpg'

  if (mode !== 'legal') return original

  const address = safeFilePart(
    (photo && (photo.legal_address || photo.simple_address)) ||
      (photo && photo.address),
  )

  if (!address) return original

  const { stem, ext } = splitFileName(original)
  const found = ITERATION_RE.exec(stem)
  const number = (found && Number(found[1])) || Number(iteration) || 1

  return `${address} (${number})${ext}`
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
  // Dates are shown by day only; отдельное поле «Время съёмки» показывает
  // ЧЧ:ММ:СС из того же taken_at.
  if (key === 'taken_time') {
    const moment = photo && photo.taken_at
    const time = moment ? String(moment).split(/[T ]/)[1] || '' : ''
    return time.slice(0, 8) || '—'
  }

  if (key === 'taken_at' || key === 'created_at') {
    return String(value).slice(0, 10)
  }
  return value
}
