/**
 * Main application logic for the PhotoBAse mobile PWA.
 *
 * Данные — реальный API PhotoBAse (app/api): список фото с курсорной
 * пагинацией, подборки пользователя и адресная панель. Плитки показывают
 * сокращённое название и дату съёмки; превью — SMALL (640 px), авторизация
 * кукой сессии.
 */

import { api } from './api.js';
import { auth } from './auth.js';
import { registerPwa, forceUpdatePwa } from './pwa.js';

// ===== Constants =====

// Период подвала: от «вчера/позавчера» до года. Фильтр — по дате съёмки
// (`date_mode=capture`, как у десктопного «Сбросить фильтры»).
// `days` — число календарных дней включительно; `endOffset` сдвигает конец
// периода назад (у «вчера/позавчера» сегодняшний день не входит).
const PERIODS = [
  { label: 'Вчера/позавчера', days: 2, endOffset: 1 },
  { label: 'Неделя', days: 7 },
  { label: '2 недели', days: 14 },
  { label: 'Месяц', days: 30 },
  { label: '2 месяца', days: 60 },
  { label: 'Полгода', days: 182 },
  { label: 'Год', days: 365 },
];

const COLUMN_OPTIONS = ['3×4', '4×4', '5×4', '6×4'];
const PAGE_SIZE = 100;
// Адреса рисуем порциями: при 2000 адресов в группе весь список в DOM
// держать не нужно, «Показать ещё» добавляет следующую порцию.
const ADDRESS_PAGE_SIZE = 200;
// «Все группы» — только пока адресов немного. На большой базе нужно
// выбрать группу: иначе на экране окажется весь справочник.
const ADDRESS_ALL_LIMIT = 200;
// Имя служебной фото-подборки; сервер резервирует его под «Избранное».
const FAVORITES_COLLECTION_NAME = 'Избранные фото';

// ===== State =====

const state = {
  mode: 'dates',          // 'dates' | 'addresses'
  group: null,            // screens|rostov|cities|roads|small|null
  periodIndex: 1,         // «Неделя»
  columns: 3,
  view: { type: 'root' }, // root | day | photos
  darkMode: false,
  selectMode: false,
  selected: new Set(),
  favorite: new Set(),
  favoriteCollectionId: null,
  loading: false,
  error: null,
  photos: new Map(),      // photo_id → item
  days: [],               // [{ key, label, count, sample }] — дни съёмки

  collections: [],
  addresses: [],
  addressLimit: ADDRESS_PAGE_SIZE, // сколько плиток-адресов рисуем сейчас
  addressPickerLimit: ADDRESS_PAGE_SIZE, // сколько строк в панели выбора
  addressPanelKey: null,  // группа|период, для которых загружены адреса
  addressPickerLoading: false,
  addressFilter: [],      // выбранные значения addr:<id>
  searchQuery: '',
  searchSuggestions: [],
  page: null,             // { items, cursor, total, label, params }
  currentPhotoId: null,
  preview: null,          // { ids, index } — список для листания свайпами
  favoriteCollections: [], // именованные фото-подборки (десктопное Избранное)
  deleteCollectionTarget: null,
  pendingCollectionScope: 'photos',
  addressSelected: new Set(), // ключи выбранных плиток-адресов
  addressSelectMode: false,
  nearestDate: null,      // ближайший день с фото, если период пуст
};

// ===== DOM =====

const DOM = {
  loginScreen: document.getElementById('loginScreen'),
  mainApp: document.getElementById('mainApp'),
  loginName: document.getElementById('loginName'),
  loginPass: document.getElementById('loginPass'),
  loginBtn: document.getElementById('loginBtn'),
  headerTitle: document.getElementById('headerTitle'),
  headerFavoriteBtn: document.getElementById('headerFavoriteBtn'),
  headerSelectBtn: document.getElementById('headerSelectBtn'),
  searchInput: document.getElementById('searchInput'),
  searchSuggestions: document.getElementById('searchSuggestions'),
  modeDates: document.getElementById('modeDates'),
  modeAddresses: document.getElementById('modeAddresses'),
  content: document.getElementById('content'),
  selectionBar: document.getElementById('selectionBar'),
  selectionCount: document.getElementById('selectionCount'),
  selectAllBtn: document.getElementById('selectAllBtn'),
  favoriteBtn: document.getElementById('favoriteBtn'),
  copyBtn: document.getElementById('copyBtn'),
  exportBtn: document.getElementById('exportBtn'),
  clearSelectionBtn: document.getElementById('clearSelectionBtn'),
  footerCols: document.getElementById('footerCols'),
  footerAddressBtn: document.getElementById('addressPickerBtn'),
  footerAddressText: document.getElementById('footerAddressText'),
  footerPeriod: document.getElementById('footerPeriod'),
  addressPickerOverlay: document.getElementById('addressPickerOverlay'),
  addressPicker: document.getElementById('addressPicker'),
  addressSearchInput: document.getElementById('addressSearchInput'),
  addressPickerContent: document.getElementById('addressPickerContent'),
  addressCancelBtn: document.getElementById('addressCancelBtn'),
  addressApplyBtn: document.getElementById('addressApplyBtn'),
  addCollectionDialog: document.getElementById('addCollectionDialog'),
  collectionDialogTitle: document.getElementById('collectionDialogTitle'),
  deleteCollectionDialog: document.getElementById('deleteCollectionDialog'),
  deleteCollectionName: document.getElementById('deleteCollectionName'),
  deleteCollectionCancelBtn: document.getElementById('deleteCollectionCancelBtn'),
  deleteCollectionConfirmBtn: document.getElementById('deleteCollectionConfirmBtn'),
  collectionNameInput: document.getElementById('collectionNameInput'),
  addCollectionCancelBtn: document.getElementById('addCollectionCancelBtn'),
  addCollectionCreateBtn: document.getElementById('addCollectionCreateBtn'),
  addCollectionBtn: document.getElementById('addCollectionBtn'),
  drawerOverlay: document.getElementById('drawerOverlay'),
  drawer: document.getElementById('drawer'),
  menuBtn: document.getElementById('menuBtn'),
  drawerAvatar: document.getElementById('drawerAvatar'),
  drawerUserName: document.getElementById('drawerUserName'),
  drawerUserRole: document.getElementById('drawerUserRole'),
  logoutBtn: document.getElementById('logoutBtn'),
  navDates: document.getElementById('navDates'),
  navAddresses: document.getElementById('navAddresses'),
  navFavorites: document.getElementById('navFavorites'),
  syncBtn: document.getElementById('syncBtn'),
  syncStatus: document.getElementById('syncStatus'),
  updateAppBtn: document.getElementById('updateAppBtn'),
  themeBtn: document.getElementById('themeBtn'),
  themeIcon: document.getElementById('themeIcon'),
  previewOverlay: document.getElementById('previewOverlay'),
  previewCloseBtn: document.getElementById('previewCloseBtn'),
  previewPrevBtn: document.getElementById('previewPrevBtn'),
  previewNextBtn: document.getElementById('previewNextBtn'),
  previewImage: document.getElementById('previewImage'),
  previewCounter: document.getElementById('previewCounter'),
  previewAddress: document.getElementById('previewAddress'),
  previewClient: document.getElementById('previewClient'),
  previewBrand: document.getElementById('previewBrand'),
  previewTags: document.getElementById('previewTags'),
  previewDate: document.getElementById('previewDate'),
  previewFavoriteBtn: document.getElementById('previewFavoriteBtn'),
  previewShareBtn: document.getElementById('previewShareBtn'),
  previewDownloadBtn: document.getElementById('previewDownloadBtn'),
  previewCloseBottomBtn: document.getElementById('previewCloseBottomBtn'),
  toast: document.getElementById('toast'),
  buildVersion: document.getElementById('buildVersion'),
  groupButtons: Array.from(document.querySelectorAll('[data-group]')),
};

// ===== Helpers =====

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function pad2(value) {
  return String(value).padStart(2, '0');
}

function isoDate(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/** «2026-11-20 14:09:00» → «20.11.2026 14:09». */
function formatStamp(value) {
  if (!value) return '';

  const match = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}:\d{2}))?/,
  );

  if (!match) return String(value);

  const [, year, month, day, time] = match;

  return `${day}.${month}.${year}${time ? ` ${time}` : ''}`;
}

/** Подпись дня: Сегодня / Вчера / 20.11.2026. */
function dayLabel(dayKey) {
  const today = new Date();
  const yesterday = new Date();

  yesterday.setDate(today.getDate() - 1);

  if (dayKey === isoDate(today)) return 'Сегодня';
  if (dayKey === isoDate(yesterday)) return 'Вчера';

  const [year, month, day] = String(dayKey).split('-');

  return year && month && day ? `${day}.${month}.${year}` : 'Без даты';
}

/** ISO → «20.11.2026» (без «Сегодня/Вчера» — для подсказки о периоде). */
function formatDayRu(dayKey) {
  const [year, month, day] = String(dayKey).split('-');

  return year && month && day ? `${day}.${month}.${year}` : String(dayKey);
}

/**
 * Ближайший к выбранному периоду день, где есть фото.
 * Фасет запрашивается без date-фильтра, но с текущими группой/адресами.
 */
async function findNearestShootingDate(fromIso, toIso) {
  try {
    const data = await api.fetchPhotoDates({ ...baseFilters() });
    const dates = (data.items || [])
      .map((item) => item.date)
      .filter(Boolean);

    if (!dates.length) return null;

    const fromTime = Date.parse(`${fromIso}T00:00:00`);
    const toTime = Date.parse(`${toIso}T00:00:00`);
    let best = null;
    let bestDistance = Infinity;

    for (const date of dates) {
      const time = Date.parse(`${date}T00:00:00`);
      const distance = time < fromTime
        ? fromTime - time
        : (time > toTime ? time - toTime : 0);

      if (distance < bestDistance) {
        bestDistance = distance;
        best = date;
      }
    }

    return best;
  } catch (error) {
    console.warn('nearest date lookup failed:', error);
    return null;
  }
}

function emptyPeriodTitle() {
  return state.periodIndex === 0
    ? 'За вчера и позавчера фото нет'
    : 'За выбранный период фото нет';
}

/** Сообщение пустого периода: без сетки дней и с подсказкой. */
function emptyPeriodState(title) {
  const hint = state.nearestDate
    ? `Измените период: ближайший фотоотчёт был сделан ${formatDayRu(state.nearestDate)}.`
    : 'Измените период или группу адресов.';

  return `
    <div class="empty-state">
      <div>${esc(title)}</div>
      <div class="empty-state-hint">${esc(hint)}</div>
    </div>
  `;
}

/**
 * Период подвала — по датам СЪЁМКИ (`date_mode=capture`, EXIF taken_at).
 * Так плитки «По датам» и счётчики адресов говорят об одном и том же
 * промежутке: «Неделя» = снято за последние семь дней.
 */
function periodParams() {
  const period = PERIODS[state.periodIndex];
  const to = new Date();
  const from = new Date();
  const endOffset = period.endOffset || 0;

  // Обе границы включительны: «Неделя» — 7 календарных дней, а не 8.
  from.setDate(to.getDate() - endOffset - (period.days - 1));
  to.setDate(to.getDate() - endOffset);

  return { date_from: isoDate(from), date_to: isoDate(to), date_mode: 'capture' };
}

// Символы, запрещённые в имени файла на общих платформах.
const UNSAFE_NAME_CHARS = /[\\/:*?"<>|\u0000-\u001f]/g;

function safeFilePart(value) {
  return String(value ?? '')
    .replace(UNSAFE_NAME_CHARS, '_')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Имя скачиваемого файла: «юридический адрес (итерация).ext».
 * Итерация — хвостовое «(N)» исходного имени, иначе позиция в списке.
 */
function downloadFileName(item, iteration = 1) {
  const original = item.filename || 'photo.jpg';
  const address = safeFilePart(
    item.legal_address || item.simple_address || item.address,
  );

  if (!address) return original;

  const dot = original.lastIndexOf('.');
  const stem = dot > 0 ? original.slice(0, dot) : original;
  const ext = dot > 0 ? original.slice(dot) : '';
  const found = /\((\d{1,4})\)\s*$/.exec(stem);
  const number = (found && Number(found[1])) || Number(iteration) || 1;

  return `${address} (${number})${ext}`;
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Превью храним только для текущей выборки (период/группа адресов). */
function clearPreviewCache() {
  if (navigator.serviceWorker && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage('clear-previews');
  }
}

function photoLabel(item) {
  return item.simple_address || item.legal_address || item.address
    || item.filename || item.photo_id;
}

function photoStamp(item) {
  return item.taken_at || item.created_at || '';
}

function showToast(message) {
  DOM.toast.textContent = message;
  DOM.toast.classList.add('show');
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => DOM.toast.classList.remove('show'), 2500);
}

function registerPhotos(items) {
  for (const item of items) {
    state.photos.set(item.photo_id, item);
  }
}

// ===== Data loading =====

/** Общие фильтры вкладок: группа верхней панели и выбранные адреса. */
function baseFilters() {
  return {
    group: state.group || undefined,
    address: state.addressFilter.length ? state.addressFilter : undefined,
  };
}

/** Ключ адресной панели: при смене группы/периода её нужно перезагрузить. */
function addressPanelKey() {
  return `${state.group || ''}|${state.periodIndex}`;
}

/** Коллекции адресов и строки адресов за текущий период/группу. */
async function fetchAddressPanelData() {
  const period = periodParams();
  const [collections, addresses] = await Promise.all([
    api.fetchCollections(),
    // Период передаём: `period_count` в ответе — число фото в пределах
    // выбранного фильтра (`count` остаётся за всё время).
    api.fetchAddresses({ group: state.group || undefined, ...period }),
  ]);

  return {
    // Фото-подборки (включая служебное «Избранные фото») живут в отдельном
    // экране «Избранное»: в адресном списке им не место.
    collections: (collections.items || []).filter(
      (item) => item.scope === 'addresses',
    ),
    addresses: (addresses.items || []).filter(
      (row) => (row.period_count ?? row.count ?? 0) > 0,
    ),
  };
}

/**
 * Корень «По датам» — фасет дней с сервера (`/photos/dates`).
 *
 * Раньше дни собирались из первой страницы `/photos` (100 фото), и при
 * широком периоде на экране оказывались один-два дня. Серверный фасет
 * перечисляет все реально существующие дни съёмки с их числом фото.
 */
async function loadRootDates() {
  state.view = { type: 'root' };
  state.loading = true;
  state.error = null;
  state.nearestDate = null;
  render();

  const period = periodParams();

  try {
    const data = await api.fetchPhotoDates({
      ...period,
      ...baseFilters(),
    });

    state.days = (data.items || []).map((item) => ({
      key: item.date,
      label: dayLabel(item.date),
      count: item.photos,
      sample: item.sample_photo_id,
    }));

    // Пустой период: не расширяем его, а подсказываем ближайшую съёмку.
    if (!state.days.length) {
      state.nearestDate = await findNearestShootingDate(
        period.date_from,
        period.date_to,
      );
    }
  } catch (error) {
    state.error = error.message;
  }

  state.loading = false;
  render();
}

async function loadRootAddresses() {
  state.view = { type: 'root' };
  state.loading = true;
  state.error = null;
  state.nearestDate = null;
  state.addressLimit = ADDRESS_PAGE_SIZE;
  // Список адресов перезагружается (группа/период/после создания) —
  // выбранные ключи могли исчезнуть, поэтому выделение сбрасываем.
  state.addressSelected.clear();
  state.addressSelectMode = false;
  render();

  const period = periodParams();

  try {
    const data = await fetchAddressPanelData();

    state.collections = data.collections;
    state.addresses = data.addresses;
    state.addressPanelKey = addressPanelKey();

    if (!state.addresses.length) {
      state.nearestDate = await findNearestShootingDate(
        period.date_from,
        period.date_to,
      );
    }
  } catch (error) {
    state.error = error.message;
    console.error('loadRootAddresses failed:', error);
  }

  state.loading = false;
  render();
}

/**
 * Универсальная загрузка страницы фотографий (подборка, адрес, поиск).
 * params — фильтры API; label — заголовок шапки.
 */
async function loadPhotosPage(
  params,
  { label, append = false, viewType = 'photos' } = {},
) {
  state.view = viewType === 'favorites'
    ? { type: 'favorites', collectionId: params.collection_id ?? null }
    : { type: 'photos' };
  state.loading = true;
  state.error = null;

  if (!append || !state.page) {
    state.page = { items: [], cursor: null, total: null, label, params };
  }

  state.page.label = label;
  render();

  try {
    const data = await api.fetchPhotos({
      ...params,
      cursor: append ? state.page.cursor || undefined : undefined,
      limit: PAGE_SIZE,
      sort: 'date',
      order: 'desc',
      count: append ? 0 : 1,
    });

    const items = data.items || [];

    state.page.items = append ? state.page.items.concat(items) : items;
    state.page.cursor = data.next_cursor || null;
    state.page.total = data.total ?? state.page.total;
    registerPhotos(items);
  } catch (error) {
    state.error = error.message;
  }

  state.loading = false;
  render();
}

async function openCollection(collection) {
  const id = collection.collection_id;
  const scope = collection.scope || 'photos';

  if (scope === 'photos') {
    await loadPhotosPage(
      { collection_id: id },
      { label: collection.name },
    );
    return;
  }

  try {
    const memberType = scope === 'addresses' ? 'address' : 'client';
    const members = (await api.getCollectionMembers(id, memberType)).items || [];

    if (!members.length) {
      state.view = { type: 'photos' };
      state.page = { items: [], cursor: null, total: 0, label: collection.name, params: {} };
      render();
      return;
    }

    const params = memberType === 'address'
      ? { address: members.slice(0, 100) }
      : { client: members.slice(0, 100) };

    await loadPhotosPage(params, { label: collection.name });
  } catch (error) {
    showToast('Ошибка подборки: ' + error.message);
  }
}

async function openAddressRow(row) {
  const values = (row.ids || [])
    .filter((id) => id !== null && id !== undefined)
    .slice(0, 100)
    .map((id) => `addr:${id}`);

  if (!values.length && row.address) {
    values.push(row.address);
  }

  // Тот же период, что и в счётчике плитки: иначе «2 фото» открывало бы
  // все 705 снимков адреса.
  await loadPhotosPage(
    { address: values, ...periodParams() },
    { label: row.name || row.address },
  );
}

/** День открывается как обычная страница фото за эту дату съёмки. */
async function openDay(day) {
  await loadPhotosPage(
    {
      ...baseFilters(),
      date_from: day.key,
      date_to: day.key,
      date_mode: 'capture',
    },
    { label: day.label },
  );
}

// ===== Search suggestions =====

const SUGGESTION_KINDS = {
  tag: 'Тег',
  client: 'Клиент',
  brand: 'Бренд',
  category: 'Категория',
  address: 'Адрес',
};

function hideSearchSuggestions() {
  suggestionsSeq += 1;
  DOM.searchSuggestions.hidden = true;
  DOM.searchSuggestions.innerHTML = '';
  state.searchSuggestions = [];
}

function renderSearchSuggestions(data) {
  const seen = new Set();
  const items = [];

  for (const item of [
    ...(data.items || []),
    ...((data.layout && data.layout.items) || []),
  ]) {
    if (!item || !item.value) continue;

    const key = `${item.kind}:${item.value}`;

    if (seen.has(key)) continue;

    seen.add(key);
    items.push(item);
  }

  state.searchSuggestions = items.slice(0, 12);

  if (!items.length) {
    hideSearchSuggestions();
    return;
  }

  DOM.searchSuggestions.innerHTML = state.searchSuggestions
    .map((item, index) => `
      <button class="search-suggestion" data-suggestion-index="${index}">
        <span>${esc(item.value)}</span>
        <span class="search-suggestion-kind">${esc(SUGGESTION_KINDS[item.kind] || item.kind)}</span>
      </button>
    `)
    .join('');
  DOM.searchSuggestions.hidden = false;
}

/** Подсказка задаёт точный фильтр (бренд/тег/…), адрес ищется текстом. */
function applySearchSuggestion(index) {
  const suggestion = state.searchSuggestions[index];

  if (!suggestion) return;

  // Отменяем отложенный q-поиск, иначе он перебьёт точный фильтр.
  clearTimeout(searchTimer);
  clearTimeout(suggestionsTimer);

  const value = suggestion.value;
  const exact = {
    tag: 'tag',
    client: 'client',
    brand: 'brand',
    category: 'category',
  }[suggestion.kind];

  DOM.searchInput.value = value;
  hideSearchSuggestions();

  // Поиск идёт в пределах выбранной группы адресов: результат не должен
  // показывать фото из других закладок.
  const group = state.group || undefined;

  if (exact) {
    loadPhotosPage(
      { [exact]: value, group },
      { label: `${SUGGESTION_KINDS[suggestion.kind]}: ${value}` },
    );
  } else {
    loadPhotosPage({ q: value, group }, { label: `Поиск: ${value}` });
  }
}

function goRoot() {
  if (state.mode === 'dates') {
    loadRootDates();
  } else {
    loadRootAddresses();
  }
}

// ===== Rendering =====

function render() {
  const title = state.view.type === 'root'
    ? 'АЛЬБИОН'
    : (state.page?.label || 'АЛЬБИОН');

  DOM.headerTitle.textContent = title;

  // «Выбрать» есть в сетке фото и в корне адресов (выбор папок-адресов).
  const photosView = state.view.type === 'photos';
  const addressesRoot = state.mode === 'addresses' && state.view.type === 'root';
  const selectActive = photosView
    ? state.selectMode
    : (addressesRoot && state.addressSelectMode);

  DOM.headerSelectBtn.style.display = (photosView || addressesRoot) ? 'flex' : 'none';
  DOM.headerSelectBtn.classList.toggle('active', selectActive);
  // Сердечко видно всегда; гостю без collections:write клик объяснит права.
  DOM.headerFavoriteBtn.style.display = 'flex';
  DOM.headerSelectBtn.textContent = selectActive ? '✓' : '☑';
  DOM.headerSelectBtn.setAttribute(
    'aria-label',
    selectActive
      ? 'Готово'
      : (addressesRoot ? 'Выбрать адреса' : 'Выбрать фото'),
  );

  let html = '';

  if (state.error) {
    html += `<div class="error-message">${esc(state.error)}</div>`;
  }

  if (state.loading && !state.days.length && !state.page && !state.collections.length) {
    html += '<div class="loading-spinner">Загрузка</div>';
  } else if (state.view.type === 'root') {
    html += state.mode === 'dates' ? renderDatesRoot() : renderAddressesRoot();
  } else if (state.view.type === 'favorites') {
    html += renderFavoritesPage();
  } else {
    html += renderPhotosPage();
  }

  DOM.content.innerHTML = html;
  updateSelectionBar();
}

function photoTile(item) {
  const id = esc(item.photo_id);
  const selected = state.selected.has(item.photo_id) ? 'selected' : '';
  const selectable = state.selectMode ? 'selectable' : '';
  const fav = state.favorite.has(item.photo_id) ? 'favorited' : '';
  const stamp = formatStamp(photoStamp(item));

  return `
    <div class="photo-tile ${selected} ${selectable} ${fav}" data-photo-id="${id}">
      <img class="photo-preview" loading="lazy" alt=""
           src="${esc(api.previewUrl(item.photo_id, 'small'))}"
           onerror="this.classList.add('failed')">
      <div class="photo-checkbox">✓</div>
      <svg class="photo-favorite" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
      <div class="photo-label">
        <div class="photo-address">${esc(photoLabel(item))}</div>
        <div class="photo-date">${esc(stamp)}</div>
      </div>
    </div>
  `;
}

/**
 * Плитка верхнего уровня: дата или адрес. Одна квадратная плитка,
 * подпись снизу; превью — первое фото, если оно известно.
 */
function folderTile({
  name,
  meta,
  previewPhotoId,
  action,
  deleteAction = '',
  selectable = false,
  selected = false,
  plain = false,
}) {
  // Удаление подборки: кнопка внутри плитки; клик по ней не должен
  // открывать подборку (обрабатывается до остальных веток).
  const removeButton = deleteAction
    ? `<button class="folder-tile-delete" ${deleteAction} aria-label="Удалить подборку">🗑</button>`
    : '';
  const checkbox = (selectable || selected)
    ? '<div class="folder-checkbox">✓</div>'
    : '';
  const classes = [
    'folder-tile',
    selectable ? 'selectable' : '',
    selected ? 'selected' : '',
  ].filter(Boolean).join(' ');

  const label = `
    <div class="folder-tile-label">
      <div class="folder-tile-name">${esc(name)}</div>
      <div class="folder-tile-meta">${esc(meta)}</div>
    </div>
  `;

  // Плитка-надпись: без иконки папки и градиента — название и счётчик
  // читаются контрастнее (используется для папок-адресов).
  if (plain) {
    return `
      <div class="${classes} plain-tile" ${action}>
        ${checkbox}
        ${label}
      </div>
    `;
  }

  if (previewPhotoId) {
    return `
      <div class="${classes}" ${action}>
        ${removeButton}
        ${checkbox}
        <img loading="lazy" alt=""
             src="${esc(api.previewUrl(previewPhotoId, 'small'))}"
             onerror="this.remove()">
        ${label}
      </div>
    `;
  }

  return `
    <div class="${classes} icon-only" ${action}>
      ${removeButton}
      ${checkbox}
      <svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
      ${label}
    </div>
  `;
}

/** Плитка «Добавить подборку» в сетке подборок; активна при выборе адресов. */
function addCollectionTile() {
  const allowed = auth.hasScope('collections:write');
  const count = state.addressSelected.size;
  const enabled = allowed && count > 0;
  const meta = !allowed
    ? 'нет прав'
    : (count > 0 ? `адресов: ${count}` : 'выберите адреса');

  return `
    <div class="folder-tile add-collection-tile ${enabled ? 'active' : 'disabled'}"
         data-add-collection="1">
      <div class="add-collection-plus">＋</div>
      <div class="folder-tile-label">
        <div class="folder-tile-name">Добавить подборку</div>
        <div class="folder-tile-meta">${esc(meta)}</div>
      </div>
    </div>
  `;
}

/** Первая плитка сетки фото — возврат на уровень вверх. */
function backTile() {
  return `
    <div class="photo-tile back-tile" data-action="back">
      <span class="back-arrow">←</span>
      <span>Назад</span>
    </div>
  `;
}

function renderDatesRoot() {
  if (!state.days.length) {
    return state.loading
      ? '<div class="loading-spinner">Загрузка</div>'
      : emptyPeriodState(emptyPeriodTitle());
  }

  let html = `<div class="photo-grid cols-${state.columns}">`;

  for (const [index, day] of state.days.entries()) {
    html += folderTile({
      name: day.label,
      meta: `${day.count} фото`,
      previewPhotoId: day.sample,
      action: `data-day-index="${index}"`,
    });
  }

  html += '</div>';

  return html;
}

function renderAddressesRoot() {
  let html = '';

  html += '<div class="section-title">Подборки адресов</div>';

  // Удалять подборки может только роль с правом collections:write
  // (у гостя его нет — сервер всё равно ответит 403).
  const canDeleteCollection = auth.hasScope('collections:write');

  html += `<div class="photo-grid cols-${state.columns}">`;

  for (const [index, collection] of state.collections.entries()) {
    // У подборок сервер не считает состав за период — показываем размер
    // подборки и подписываем это явно, чтобы не путать с числом за период.
    html += folderTile({
      name: collection.name,
      meta: `в подборке ${collection.members ?? 0}`,
      previewPhotoId: null,
      action: `data-collection-index="${index}"`,
      deleteAction: canDeleteCollection ? `data-delete-collection="${index}"` : '',
    });
  }

  // Кнопка создания — такая же плитка списка; активна только когда
  // выбраны папки-адреса (или у роли нет прав collections:write).
  html += addCollectionTile();

  html += '</div>';

  if (state.loading && !state.collections.length) {
    html += '<div class="loading-spinner">Загрузка</div>';
  }

  html += '<div class="section-title">Адреса</div>';

  if (!state.addresses.length) {
    html += state.loading
      ? '<div class="loading-spinner">Загрузка</div>'
      : emptyPeriodState('Адресов с фото за выбранный период нет');
  } else if (!state.group && state.addresses.length > ADDRESS_ALL_LIMIT) {
    // 2000 адресов «всех групп» одновременно не показываем: это тот случай,
    // когда нужна конкретная закладка.
    html += `
      <div class="empty-state">
        <div>Выберите группу адресов</div>
        <div class="empty-state-hint">
          В базе ${state.addresses.length} адресов — выберите закладку в меню.
        </div>
      </div>
    `;
  } else {
    html += `<div class="photo-grid cols-${state.columns}">`;

    const visible = state.addresses.slice(0, state.addressLimit);

    for (const [index, row] of visible.entries()) {
      html += folderTile({
        name: row.name || row.address,
        meta: `${row.period_count ?? row.count ?? 0} фото`,
        previewPhotoId: null,
        action: `data-address-index="${index}"`,
        selectable: state.addressSelectMode,
        selected: state.addressSelected.has(addressRowKey(row)),
        plain: true,
      });
    }

    html += '</div>';

    if (state.addresses.length > state.addressLimit) {
      html += `<button class="load-more" data-action="more-addresses">
        Показать ещё адреса (${state.addresses.length - state.addressLimit})
      </button>`;
    }
  }

  return html;
}

function renderPhotosPage() {
  // Возврат есть всегда: даже пустой результат не должен запирать вкладку.
  let html = `<div class="photo-grid cols-${state.columns}">${backTile()}`;

  if (state.page && state.page.items.length) {
    html += state.page.items.map(photoTile).join('');
  }

  html += '</div>';

  if (state.page && !state.page.items.length) {
    html += state.loading
      ? '<div class="loading-spinner">Загрузка</div>'
      : '<div class="empty-state">Ничего не найдено</div>';
  }

  if (state.page && state.page.cursor) {
    html += '<button class="load-more" data-action="load-more-photos">Загрузить ещё</button>';
  }

  return html;
}

/** «Избранное» — фото-подборка пользователя с действиями на всю коллекцию. */
function renderFavoritesPage() {
  const items = state.page?.items || [];
  const hasItems = items.length > 0;
  const disabled = hasItems ? '' : 'disabled';

  let html = `
    <div class="favorites-actions">
      <button class="favorites-action" data-action="download-favorites" ${disabled}>
        <span>⬇️</span><span>Скачать</span>
      </button>
      <button class="favorites-action" data-action="share-favorites" ${disabled}>
        <span>📤</span><span>В мессенджер</span>
      </button>
      <button class="favorites-action primary" data-action="name-favorites" ${disabled}>
        <span>🏷</span><span>Назвать</span>
      </button>
    </div>
  `;

  html += `<div class="photo-grid cols-${state.columns}">${backTile()}`;

  if (hasItems) {
    html += items.map(photoTile).join('');
  }

  html += '</div>';

  if (!hasItems) {
    html += state.loading
      ? '<div class="loading-spinner">Загрузка</div>'
      : `
        <div class="empty-state">
          <div>В избранном пока нет фото</div>
          <div class="empty-state-hint">Добавьте фото через «❤️» в карточке или в панели выбора.</div>
        </div>
      `;
  }

  if (state.page && state.page.cursor) {
    html += '<button class="load-more" data-action="load-more-favorites">Загрузить ещё</button>';
  }

  // Именованные фото-подборки (они же — десктопное «Избранное»).
  if (state.favoriteCollections.length) {
    const canDelete = auth.hasScope('collections:write');

    html += '<div class="section-title">Избранные подборки</div>';
    html += `<div class="photo-grid cols-${state.columns}">`;

    for (const [index, collection] of state.favoriteCollections.entries()) {
      html += folderTile({
        name: collection.name,
        meta: `${collection.members ?? 0} фото`,
        previewPhotoId: null,
        action: `data-favorite-collection-index="${index}"`,
        deleteAction: canDelete
          ? `data-delete-favorite-collection="${index}"`
          : '',
      });
    }

    html += '</div>';
  }

  return html;
}

// ===== Selection =====

function updateSelectionBar() {
  // Панель видна и в ручном режиме выбора, даже пока ничего не отмечено.
  // Для выбора папок-адресов она не используется — действие там плитка.
  const photosView = state.view.type === 'photos';
  const active = photosView && (state.selectMode || state.selected.size > 0);

  DOM.selectionBar.classList.toggle('active', active);
  DOM.selectionCount.textContent = `Выбрано: ${state.selected.size}`;
}

/** Обновить вид сетки и шапки под текущий режим выбора (без перерисовки). */
function applySelectModeUi() {
  const addressesRoot = state.mode === 'addresses' && state.view.type === 'root';
  const active = addressesRoot ? state.addressSelectMode : state.selectMode;

  DOM.headerSelectBtn.textContent = active ? '✓' : '☑';
  DOM.headerSelectBtn.classList.toggle('active', active);
  DOM.headerSelectBtn.setAttribute(
    'aria-label',
    active
      ? 'Готово'
      : (addressesRoot ? 'Выбрать адреса' : 'Выбрать фото'),
  );

  if (addressesRoot) {
    DOM.content.querySelectorAll('.folder-tile[data-address-index]').forEach((tile) => {
      tile.classList.toggle('selectable', state.addressSelectMode);

      if (!state.addressSelectMode) tile.classList.remove('selected');
    });

    updateAddressSelectionUi();
  } else {
    DOM.content.querySelectorAll('.photo-tile[data-photo-id]').forEach((tile) => {
      tile.classList.toggle('selectable', state.selectMode);

      if (!state.selectMode) tile.classList.remove('selected');
    });
  }

  updateSelectionBar();
}

/** Включить/выключить режим мультивыбора (кнопка «☑» в шапке). */
function toggleSelectMode() {
  // В корне «По адресам» кнопка выбирает папки-адреса для подборки.
  if (state.mode === 'addresses' && state.view.type === 'root') {
    state.addressSelectMode = !state.addressSelectMode;

    if (!state.addressSelectMode) state.addressSelected.clear();

    applySelectModeUi();

    if (state.addressSelectMode) {
      showToast('Выберите адреса, затем — «Добавить подборку»');
    }

    return;
  }

  state.selectMode = !state.selectMode;

  if (!state.selectMode) state.selected.clear();

  applySelectModeUi();
}

/** Ключ плитки-адреса для состояния выбора. */
function addressRowKey(row) {
  if (row.address) return row.address;

  const firstId = (row.ids || []).find(
    (id) => id !== null && id !== undefined,
  );

  return firstId !== undefined ? `addr:${firstId}` : (row.name || '');
}

/** Значения addr:<id> для сохранения в подборку адресов. */
function addressRowValues(row) {
  const values = (row.ids || [])
    .filter((id) => id !== null && id !== undefined)
    .map((id) => `addr:${id}`);

  if (!values.length && row.address) values.push(row.address);

  return values;
}

function toggleAddressSelection(index) {
  const row = state.addresses[index];

  if (!row) return;

  const key = addressRowKey(row);

  if (state.addressSelected.has(key)) {
    state.addressSelected.delete(key);
  } else {
    state.addressSelected.add(key);
  }

  updateAddressSelectionUi();
}

/** Обновить чекбоксы адресов и плитку «Добавить подборку» без перерисовки. */
function updateAddressSelectionUi() {
  DOM.content.querySelectorAll('.folder-tile[data-address-index]').forEach((tile) => {
    const row = state.addresses[Number(tile.dataset.addressIndex)];

    tile.classList.toggle(
      'selected',
      !!row && state.addressSelected.has(addressRowKey(row)),
    );
  });

  const addTile = DOM.content.querySelector('[data-add-collection]');

  if (!addTile) return;

  const allowed = auth.hasScope('collections:write');
  const count = state.addressSelected.size;
  const enabled = allowed && count > 0;

  addTile.classList.toggle('active', enabled);
  addTile.classList.toggle('disabled', !enabled);

  const meta = addTile.querySelector('.folder-tile-meta');

  if (meta) {
    meta.textContent = !allowed
      ? 'нет прав'
      : (count > 0 ? `адресов: ${count}` : 'выберите адреса');
  }
}

/** Все addr:<id> выбранных папок (без повторов, лимит подборки — 1000). */
function selectedAddressValues() {
  const seen = new Set();
  const values = [];

  for (const row of state.addresses) {
    if (!state.addressSelected.has(addressRowKey(row))) continue;

    for (const value of addressRowValues(row)) {
      if (seen.has(value)) continue;

      seen.add(value);
      values.push(value);
    }
  }

  return values.slice(0, 1000);
}

function toggleSelection(photoId) {
  if (state.selected.has(photoId)) {
    state.selected.delete(photoId);
  } else {
    state.selected.add(photoId);
  }

  const tile = DOM.content.querySelector(`[data-photo-id="${photoId}"]`);

  if (tile) {
    tile.classList.toggle('selected', state.selected.has(photoId));
  }

  updateSelectionBar();
}

function clearSelection() {
  state.selected.clear();
  state.selectMode = false;
  render();
}

async function addSelectedToFavorites() {
  if (!state.selected.size) return;

  const ids = Array.from(state.selected);

  try {
    const data = await api.addFavorites(ids);

    if (data && Array.isArray(data.photo_ids)) {
      state.favorite = new Set(data.photo_ids);
    } else {
      ids.forEach((id) => state.favorite.add(id));
    }

    if (data && data.collection_id) {
      state.favoriteCollectionId = data.collection_id;
    }

    showToast(`В избранном: ${ids.length} фото`);
    clearSelection();
  } catch (error) {
    showToast('Не удалось добавить в избранное: ' + error.message);
  }
}

/** Адрес фото для копирования/отправки. */
function selectionAddress(item) {
  return item.legal_address
    || item.address
    || item.simple_address
    || photoLabel(item);
}

/** Текст для буфера обмена: адреса (без повторов) и ссылки на фото. */
function buildSelectionText() {
  const addresses = [];
  const links = [];
  const seen = new Set();

  for (const id of state.selected) {
    const item = state.photos.get(id);

    if (!item) continue;

    const address = selectionAddress(item);

    if (address && !seen.has(address)) {
      seen.add(address);
      addresses.push(`• ${address}`);
    }

    links.push(`• ${new URL(api.previewUrl(id, 'middle'), window.location.origin).href}`);
  }

  if (!links.length) return '';

  const lines = [];

  if (addresses.length) {
    lines.push('Адреса:', ...addresses, '');
  }

  lines.push('Ссылки:', ...links);

  return lines.join('\n');
}

/** Запись в буфер: Clipboard API, иначе скрытая textarea (http/LAN). */
async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (error) {
    // Переходим к запасному способу.
  }

  const area = document.createElement('textarea');

  area.value = text;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();

  let ok = false;

  try {
    ok = document.execCommand('copy');
  } catch (error) {
    ok = false;
  }

  area.remove();
  return ok;
}

/** 📋 Копировать адреса и ссылки выбранных фото. */
async function copySelected() {
  if (!state.selected.size) return;

  const text = buildSelectionText();

  if (!text) return;

  const ok = await copyText(text);

  showToast(ok
    ? `Скопировано: ${state.selected.size} фото`
    : 'Не удалось скопировать');
}

/** 📤 Отправить выбранное в мессенджер через системное «Поделиться». */
async function shareSelected() {
  if (!state.selected.size) return;

  const text = buildSelectionText();

  if (!text) return;

  if (navigator.share) {
    try {
      await navigator.share({ title: 'АЛЬБИОН', text });
      return;
    } catch (error) {
      // Пользователь закрыл системное меню — это не ошибка.
      if (error && error.name === 'AbortError') return;
    }
  }

  const ok = await copyText(text);

  showToast(ok
    ? 'Скопировано — вставьте в мессенджер'
    : 'Не удалось отправить');
}

// ===== Favorites =====

/** Подтянуть id/collection избранного (сердечки на плитках, счётчики). */
async function loadFavoriteIds() {
  // Гость не пользуется избранным: GET создал бы ему служебную подборку.
  if (!auth.hasScope('collections:write')) return;

  try {
    const data = await api.getFavorites();

    state.favoriteCollectionId = data.collection_id ?? null;
    state.favorite = new Set(data.photo_ids || []);
  } catch (error) {
    // Гость или выключенная авторизация — просто нет данных избранного.
    console.log('favorites unavailable:', error.message);
  }
}

/** Все фото избранного (для архива/отправки/именованной подборки). */
async function fetchAllFavoriteItems(max = 500) {
  if (state.favoriteCollectionId === null) return [];

  const items = [];
  let cursor = null;

  do {
    const data = await api.fetchPhotos({
      collection_id: state.favoriteCollectionId,
      limit: PAGE_SIZE,
      sort: 'date',
      order: 'desc',
      count: 0,
      cursor: cursor || undefined,
    });

    items.push(...(data.items || []));
    cursor = data.next_cursor || null;
  } while (cursor && items.length < max);

  return items.slice(0, max);
}

/** Открыть внутреннее избранное — подборку фотографий пользователя. */
async function openFavorites() {
  if (!auth.hasScope('collections:write')) {
    showToast('Избранное доступно ролям с правом на подборки');
    return;
  }

  try {
    const data = await api.getFavorites();

    state.favoriteCollectionId = data.collection_id ?? null;
    state.favorite = new Set(data.photo_ids || []);
  } catch (error) {
    showToast('Не удалось открыть избранное: ' + error.message);
    return;
  }

  try {
    const collections = await api.fetchCollections();

    state.favoriteCollections = (collections.items || []).filter(
      (item) => item.scope === 'photos'
        && item.collection_id !== state.favoriteCollectionId
        && item.name !== FAVORITES_COLLECTION_NAME,
    );
  } catch (error) {
    // Список подборок вспомогательный: сами сердечки уже загружены.
    state.favoriteCollections = [];
    console.warn('favorite collections unavailable:', error.message);
  }

  if (state.favoriteCollectionId === null || !state.favorite.size) {
    state.view = { type: 'favorites', collectionId: state.favoriteCollectionId };
    state.page = {
      items: [],
      cursor: null,
      total: 0,
      label: 'Избранное',
      params: {},
    };
    state.loading = false;
    render();
    return;
  }

  await loadPhotosPage(
    { collection_id: state.favoriteCollectionId },
    { label: 'Избранное', viewType: 'favorites' },
  );
}

/** ⬇️ Скачать избранное одним ZIP (нужен scope originals). */
async function downloadFavorites() {
  if (!auth.hasScope('originals')) {
    showToast('Скачивание оригиналов недоступно для вашей роли');
    return;
  }

  try {
    const items = await fetchAllFavoriteItems(500);

    if (!items.length) {
      showToast('В избранном нет фото');
      return;
    }

    const payload = items.map((item) => ({
      photo_id: item.photo_id,
      name: [photoLabel(item), item.filename].filter(Boolean).join('__'),
    }));

    const blob = await api.fetchArchive(payload);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download = 'photobase-favorites.zip';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);

    showToast(state.favorite.size > items.length
      ? `Архив: первые ${items.length} из ${state.favorite.size} фото`
      : `Архив готов: ${items.length} фото`);
  } catch (error) {
    showToast('Не удалось скачать: ' + error.message);
  }
}

/** 📤 Отправить избранное в мессенджер: названия + ссылки. */
async function shareFavorites() {
  let items = [];

  try {
    items = await fetchAllFavoriteItems(500);
  } catch (error) {
    showToast('Не удалось прочитать избранное: ' + error.message);
    return;
  }

  if (!items.length) {
    showToast('В избранном нет фото');
    return;
  }

  const total = state.favorite.size;
  const countLabel = total > items.length
    ? `${items.length} из ${total} фото`
    : `${items.length} фото`;
  const lines = [`Избранное (${countLabel})`, ''];
  const origin = window.location.origin;

  items.forEach((item, index) => {
    const name = photoLabel(item);
    const filename = item.filename ? ` — ${item.filename}` : '';
    const link = new URL(api.previewUrl(item.photo_id, 'middle'), origin).href;

    lines.push(`${index + 1}. ${name}${filename}`);
    lines.push(`   ${link}`);
  });

  const text = lines.join('\n');

  if (navigator.share) {
    try {
      await navigator.share({ title: 'Избранное', text });
      return;
    } catch (error) {
      if (error && error.name === 'AbortError') return;
    }
  }

  const ok = await copyText(text);

  showToast(ok
    ? 'Скопировано — вставьте в мессенджер'
    : 'Не удалось отправить');
}

// ===== Preview =====

/** Фото текущего экрана в порядке отображения — для листания свайпами. */
function currentPhotoIds() {
  // «Избранное» — такая же страница фото: свайп, стрелки и нумерация
  // скачивания должны работать и там.
  if (
    (state.view.type === 'photos' || state.view.type === 'favorites')
    && state.page
  ) {
    return state.page.items.map((item) => item.photo_id);
  }

  return [];
}

function openPreview(photoId) {
  const ids = currentPhotoIds();
  const index = ids.indexOf(photoId);

  state.preview = {
    ids: ids.length ? ids : [photoId],
    index: index >= 0 ? index : 0,
  };

  showPreviewAt(state.preview.index);
  DOM.previewOverlay.classList.add('open');
}

/** Подпись кнопки превью: «Добавить» или «Убрать» по статусу фото. */
function updatePreviewFavoriteButton() {
  const isFavorite = Boolean(
    state.currentPhotoId && state.favorite.has(state.currentPhotoId),
  );

  DOM.previewFavoriteBtn.textContent = isFavorite
    ? '❤️ Убрать'
    : '❤️ Добавить';
  DOM.previewFavoriteBtn.classList.toggle('active', isFavorite);
  DOM.previewFavoriteBtn.setAttribute(
    'aria-label',
    isFavorite ? 'Убрать из избранного' : 'Добавить в избранное',
  );
}

/** Нарисовать карточку фото по позиции в текущем списке. */
function showPreviewAt(index) {
  const { ids } = state.preview;

  if (!ids.length) return;

  // Листание циклическое: со последнего — на первый и обратно.
  const nextIndex = ((index % ids.length) + ids.length) % ids.length;
  const photoId = ids[nextIndex];
  const item = state.photos.get(photoId);

  if (!item) return;

  state.preview.index = nextIndex;
  state.currentPhotoId = photoId;

  DOM.previewImage.innerHTML = `
    <img alt="" draggable="false"
         src="${esc(api.previewUrl(photoId, 'middle'))}"
         style="max-width:100%;max-height:100%;object-fit:contain;border-radius:8px;">
  `;
  DOM.previewAddress.textContent = `📍 ${item.legal_address || photoLabel(item)}`;
  DOM.previewClient.textContent = item.client ? `👤 Клиент: ${item.client}` : '';
  DOM.previewBrand.textContent = item.brand ? `🏷 Бренд: ${item.brand}` : '';
  DOM.previewTags.textContent = item.category ? `🏷 Категория: ${item.category}` : '';
  DOM.previewDate.textContent = `📅 ${formatStamp(photoStamp(item))}`;
  DOM.previewCounter.textContent = ids.length > 1
    ? `${nextIndex + 1} / ${ids.length}`
    : '';

  updatePreviewFavoriteButton();

  // Стрелки (и тап по краю снимка) нужны только когда есть что листать.
  DOM.previewPrevBtn.hidden = ids.length < 2;
  DOM.previewNextBtn.hidden = ids.length < 2;
}

function stepPreview(delta) {
  if (!state.preview || DOM.previewOverlay.classList.contains('open') === false) {
    return;
  }

  showPreviewAt(state.preview.index + delta);
}

function closePreview() {
  DOM.previewOverlay.classList.remove('open');
  DOM.previewImage.innerHTML = '';
  DOM.previewCounter.textContent = '';
  DOM.previewPrevBtn.hidden = true;
  DOM.previewNextBtn.hidden = true;
  state.preview = null;
}

/** ⬇️ Скачать оригинал текущего фото под юридическим именем. */
async function downloadCurrentPhoto() {
  const photoId = state.currentPhotoId;

  if (!photoId) return;

  if (!auth.hasScope('originals')) {
    showToast('Скачивание оригиналов недоступно для вашей роли');
    return;
  }

  const item = state.photos.get(photoId);

  if (!item) {
    showToast('Нет данных о фото');
    return;
  }

  const iteration = state.preview ? state.preview.index + 1 : 1;
  const filename = downloadFileName(item, iteration);

  DOM.previewDownloadBtn.disabled = true;

  try {
    const blob = await api.fetchOriginal(photoId);

    saveBlob(blob, filename);
    showToast(`Скачано: ${filename}`);
  } catch (error) {
    showToast('Не удалось скачать: ' + error.message);
  } finally {
    DOM.previewDownloadBtn.disabled = false;
  }
}

// ===== Modes =====

function switchMode(mode) {
  state.mode = mode;
  state.selected.clear();
  state.selectMode = false;
  state.addressSelected.clear();
  state.addressSelectMode = false;
  hideSearchSuggestions();

  DOM.modeDates.classList.toggle('active', mode === 'dates');
  DOM.modeAddresses.classList.toggle('active', mode === 'addresses');

  state.page = null;

  if (mode === 'dates') {
    loadRootDates();
  } else {
    loadRootAddresses();
  }
}

// ===== Footer =====

function cycleColumns() {
  state.columns = state.columns >= 6 ? 3 : state.columns + 1;
  DOM.footerCols.textContent = COLUMN_OPTIONS[state.columns - 3];
  render();
}

function cyclePeriod() {
  state.periodIndex = (state.periodIndex + 1) % PERIODS.length;
  DOM.footerPeriod.textContent = `◄ ${PERIODS[state.periodIndex].label} ►`;
  clearPreviewCache();

  // Период влияет на обе вкладки: даты фильтруются на сервере, адреса
  // пересчитывают `period_count`.
  if (state.mode === 'dates') {
    loadRootDates();
  } else {
    loadRootAddresses();
  }
}

// ===== Address picker =====

async function openAddressPicker() {
  state.addressPickerLimit = ADDRESS_PAGE_SIZE;
  DOM.addressPickerOverlay.classList.add('open');
  DOM.addressPicker.classList.add('open');
  renderAddressPicker();

  // В режиме «По датам» адреса ещё не загружены, а после смены группы или
  // периода старый список относится к другой выборке. Догружаем панель.
  if (state.addressPanelKey === addressPanelKey()) return;

  state.addressPickerLoading = true;
  renderAddressPicker();

  try {
    const data = await fetchAddressPanelData();

    state.collections = data.collections;
    state.addresses = data.addresses;
    state.addressPanelKey = addressPanelKey();
  } catch (error) {
    showToast('Не удалось загрузить адреса: ' + error.message);
  } finally {
    state.addressPickerLoading = false;
    renderAddressPicker();
  }
}

function closeAddressPicker() {
  DOM.addressPickerOverlay.classList.remove('open');
  DOM.addressPicker.classList.remove('open');
}

function renderAddressPicker() {
  if (state.addressPickerLoading) {
    DOM.addressPickerContent.innerHTML = '<div class="loading-spinner">Загрузка</div>';
    return;
  }

  const search = DOM.addressSearchInput.value.trim().toLowerCase();
  const matches = (text) => !search || String(text || '').toLowerCase().includes(search);

  let html = '<div class="address-section">Подборки</div>';

  for (const [index, collection] of state.collections.entries()) {
    if (!matches(collection.name)) continue;

    html += `
      <div class="address-item" data-collection-pick="${index}">
        <div class="address-item-name">${esc(collection.name)}</div>
        <div class="address-item-count">${collection.members ?? 0}</div>
      </div>
    `;
  }

  html += '<div class="address-section">Адреса</div>';

  // Сначала отбираем совпадения поиска, затем рисуем порцию. Индекс строки
  // в state.addresses не зависит от фильтра/лимита — по нему работает
  // переключение выбора.
  const matchingRows = [];

  for (const [index, row] of state.addresses.entries()) {
    if (matches(row.name || row.address)) {
      matchingRows.push({ index, row });
    }
  }

  for (const { index, row } of matchingRows.slice(0, state.addressPickerLimit)) {
    const values = (row.ids || []).map((id) => `addr:${id}`);
    const checked = values.length && values.every((value) => state.addressFilter.includes(value));

    html += `
      <div class="address-item ${checked ? 'selected' : ''}" data-address-pick="${index}">
        <div class="address-checkbox">${checked ? '✓' : ''}</div>
        <div class="address-item-name">${esc(row.name || row.address)}</div>
        <div class="address-item-count">${row.period_count ?? row.count ?? 0}</div>
      </div>
    `;
  }

  if (matchingRows.length > state.addressPickerLimit) {
    html += `<button class="load-more" data-address-more="1">
      Показать ещё адреса (${matchingRows.length - state.addressPickerLimit})
    </button>`;
  }

  DOM.addressPickerContent.innerHTML = html;
}

/** Клики в нижней панели выбора адресов (она вне #content). */
function handleAddressPickerClick(event) {
  const more = event.target.closest('[data-address-more]');

  if (more) {
    state.addressPickerLimit += ADDRESS_PAGE_SIZE;
    renderAddressPicker();
    return;
  }

  const collectionPick = event.target.closest('[data-collection-pick]');

  if (collectionPick) {
    const collection = state.collections[
      Number(collectionPick.dataset.collectionPick)
    ];

    closeAddressPicker();

    if (collection) openCollection(collection);

    return;
  }

  const addressPick = event.target.closest('[data-address-pick]');

  if (addressPick) {
    toggleAddressPick(Number(addressPick.dataset.addressPick));
  }
}

function toggleAddressPick(index) {
  const row = state.addresses[index];

  if (!row) return;

  const values = (row.ids || []).map((id) => `addr:${id}`);

  if (!values.length) return;

  const allSelected = values.every((value) => state.addressFilter.includes(value));

  if (allSelected) {
    state.addressFilter = state.addressFilter.filter((value) => !values.includes(value));
  } else {
    for (const value of values) {
      if (!state.addressFilter.includes(value)) {
        state.addressFilter.push(value);
      }
    }
  }

  renderAddressPicker();
}

function applyAddressFilter() {
  DOM.footerAddressText.textContent = state.addressFilter.length
    ? `Адресов: ${state.addressFilter.length}`
    : 'Все адреса';

  clearPreviewCache();
  closeAddressPicker();

  if (state.mode === 'dates') {
    loadRootDates();
  }
}

// ===== Add collection =====

function showAddCollectionDialog(scope = 'photos') {
  state.pendingCollectionScope = scope;
  DOM.collectionDialogTitle.textContent = scope === 'addresses'
    ? 'Новая подборка адресов'
    : (scope === 'favorites' ? 'Назвать избранное' : 'Новая подборка');
  DOM.addCollectionDialog.classList.add('open');
  DOM.collectionNameInput.value = '';
  DOM.collectionNameInput.focus();
}

function closeAddCollectionDialog() {
  DOM.addCollectionDialog.classList.remove('open');
}

async function createCollection() {
  const name = DOM.collectionNameInput.value.trim();
  const mode = state.pendingCollectionScope;
  const isAddresses = mode === 'addresses';
  const isFavorites = mode === 'favorites';
  const addressValues = isAddresses ? selectedAddressValues() : [];
  const favoriteIds = isFavorites
    ? Array.from(state.favorite).slice(0, 5000)
    : [];
  const memberType = isAddresses ? 'address' : 'photo';
  const memberValues = isAddresses ? addressValues : favoriteIds;

  if (!name) {
    showToast('Введите название подборки');
    return;
  }

  if (isAddresses && !addressValues.length) {
    showToast('Сначала выберите адреса');
    return;
  }

  if (isFavorites && !favoriteIds.length) {
    showToast('В избранном нет фото');
    return;
  }

  DOM.addCollectionCreateBtn.disabled = true;

  try {
    const created = await api.request('/collections', {
      method: 'POST',
      body: JSON.stringify({
        name,
        kind: 'Моя',
        scope: isAddresses ? 'addresses' : 'photos',
      }),
    });

    if (isAddresses || isFavorites) {
      try {
        await api.request(`/collections/${created.collection_id}/members`, {
          method: 'POST',
          body: JSON.stringify({
            member_type: memberType,
            values: memberValues,
          }),
        });
      } catch (error) {
        // Не оставляем пустую подборку, если состав не сохранился.
        try {
          await api.deleteCollection(created.collection_id);
        } catch (cleanupError) {
          console.warn('collection cleanup failed:', cleanupError);
        }

        throw error;
      }

      if (isAddresses) {
        state.addressSelected.clear();
        state.addressSelectMode = false;
      }
    }

    closeAddCollectionDialog();

    if (isAddresses) {
      showToast(`Подборка «${name}»: адресов ${addressValues.length}`);
      await loadRootAddresses();
    } else if (isFavorites) {
      // Новая именованная подборка должна сразу появиться в списке,
      // а не только после повторного открытия «Избранного».
      await openFavorites();
      showToast(`«${name}» сохранена — видна в «Избранном» на десктопе`);
    } else {
      showToast(`Подборка «${name}» создана`);
      await loadRootAddresses();
    }
  } catch (error) {
    showToast('Не удалось создать подборку: ' + error.message);
  } finally {
    DOM.addCollectionCreateBtn.disabled = false;
  }
}

// ===== Delete collection =====

function showDeleteCollectionDialog(collection) {
  if (!collection) return;

  state.deleteCollectionTarget = collection;
  DOM.deleteCollectionName.textContent = collection.name;
  DOM.deleteCollectionDialog.classList.add('open');
}

function closeDeleteCollectionDialog() {
  DOM.deleteCollectionDialog.classList.remove('open');
  state.deleteCollectionTarget = null;
}

async function confirmDeleteCollection() {
  const collection = state.deleteCollectionTarget;

  if (!collection) {
    closeDeleteCollectionDialog();
    return;
  }

  DOM.deleteCollectionConfirmBtn.disabled = true;

  try {
    await api.deleteCollection(collection.collection_id);
    closeDeleteCollectionDialog();
    showToast(`Подборка «${collection.name}» удалена`);

    if (state.view.type === 'favorites') {
      await openFavorites();
    } else {
      await loadRootAddresses();
    }
  } catch (error) {
    // 403 у Гостя, 404 если подборку уже удалили с другого устройства.
    showToast('Не удалось удалить подборку: ' + error.message);
  } finally {
    DOM.deleteCollectionConfirmBtn.disabled = false;
  }
}

// ===== Drawer =====

function toggleDrawer() {
  const isOpen = DOM.drawer.classList.contains('open');

  DOM.drawer.classList.toggle('open', !isOpen);
  DOM.drawerOverlay.classList.toggle('open', !isOpen);
}

function setGroup(group) {
  state.group = group || null;
  toggleDrawer();
  clearPreviewCache();
  hideSearchSuggestions();

  DOM.groupButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.group === state.group);
  });

  // Если поиск уже открыт, он должен пересчитаться в границах новой
  // группы, а не показывать выдачу прошлой.
  const query = DOM.searchInput.value.trim();

  if (query.length >= 2) {
    loadPhotosPage(
      { q: query, group: state.group || undefined },
      { label: `Поиск: ${query}` },
    );
  } else if (state.mode === 'dates') {
    loadRootDates();
  } else {
    loadRootAddresses();
  }
}

async function syncNow() {
  DOM.syncStatus.textContent = '...';

  try {
    // Сердечки и именованные подборки живут отдельно от корня грида:
    // синхронизация должна подтянуть и их, иначе изменения с десктопа
    // останутся незаметными до перезагрузки.
    await loadFavoriteIds();

    if (state.view.type === 'favorites') {
      await openFavorites();
    } else if (state.mode === 'dates') {
      await loadRootDates();
    } else {
      await loadRootAddresses();
    }

    DOM.syncStatus.textContent = 'Готово ✓';
    showToast('Данные обновлены');
  } catch (error) {
    DOM.syncStatus.textContent = 'Ошибка';
    showToast('Ошибка синхронизации: ' + error.message);
  }
}

function toggleDarkMode() {
  state.darkMode = !state.darkMode;
  document.body.classList.toggle('dark-mode', state.darkMode);
  DOM.themeIcon.textContent = state.darkMode ? '☀️' : '🌙';
  toggleDrawer();
}

// ===== Auth =====

async function doLogin() {
  const name = DOM.loginName.value.trim();
  const password = DOM.loginPass.value;

  if (!name || !password) {
    showToast('Введите логин и пароль');
    return;
  }

  DOM.loginBtn.disabled = true;

  try {
    const user = await auth.login(name, password);
    showMainApp(user);
    showToast(`Добро пожаловать, ${user.name}!`);
    // Избранное — отдельное хранилище; подтягиваем его при входе, а не
    // только при перезагрузке страницы.
    await loadFavoriteIds();
    await loadData();
  } catch (error) {
    console.error('Login failed:', error);
    showToast('Ошибка входа: ' + error.message);
  } finally {
    DOM.loginBtn.disabled = false;
  }
}

function showMainApp(user) {
  DOM.loginScreen.classList.add('hidden');
  DOM.mainApp.style.display = 'flex';

  DOM.drawerAvatar.textContent = (user.name || '?').slice(0, 1).toUpperCase();
  DOM.drawerUserName.textContent = user.name || '—';
  DOM.drawerUserRole.textContent = auth.getRole();
}

async function doLogout() {
  // Данные прошлого пользователя не должны остаться в кэше общего профиля.
  if (navigator.serviceWorker && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage('clear-private-cache');
  }

  await auth.logout();

  DOM.loginScreen.classList.remove('hidden');
  DOM.mainApp.style.display = 'none';

  // Полный сброс пользовательского состояния: следующий вход может быть
  // под другой учётной записью, и чужие сердечки/подборки не должны
  // остаться ни на экране, ни в памяти.
  closePreview();
  hideSearchSuggestions();
  DOM.searchInput.value = '';
  state.photos.clear();
  state.days = [];
  state.page = null;
  state.collections = [];
  state.addresses = [];
  state.favorite.clear();
  state.favoriteCollectionId = null;
  state.favoriteCollections = [];
  state.selected.clear();
  state.selectMode = false;
  state.addressSelected.clear();
  state.addressSelectMode = false;
  state.addressFilter = [];
  state.addressLimit = ADDRESS_PAGE_SIZE;
  state.addressPanelKey = null;
  state.addressPickerLimit = ADDRESS_PAGE_SIZE;
  state.searchQuery = '';
  state.searchSuggestions = [];
  state.currentPhotoId = null;
  state.preview = null;
  state.deleteCollectionTarget = null;
  state.nearestDate = null;
  state.loading = false;
  state.error = null;
  state.group = null;
  state.view = { type: 'root' };

  DOM.footerAddressText.textContent = 'Все адреса';
  DOM.groupButtons.forEach((button) => {
    button.classList.toggle(
      'active',
      (button.dataset.group || null) === state.group,
    );
  });

  toggleDrawer();
}

async function loadData() {
  if (state.mode === 'dates') {
    await loadRootDates();
  } else {
    await loadRootAddresses();
  }
}

// ===== Events =====

let pressTimer = null;
let searchTimer = null;
let suggestionsTimer = null;
let suggestionsSeq = 0;

function initEvents() {
  DOM.loginBtn.addEventListener('click', doLogin);
  DOM.loginPass.addEventListener('keyup', (event) => {
    if (event.key === 'Enter') doLogin();
  });

  DOM.modeDates.addEventListener('click', () => switchMode('dates'));
  DOM.modeAddresses.addEventListener('click', () => switchMode('addresses'));

  DOM.footerCols.addEventListener('click', cycleColumns);
  DOM.footerAddressBtn.addEventListener('click', openAddressPicker);
  DOM.footerPeriod.addEventListener('click', cyclePeriod);

  DOM.addressCancelBtn.addEventListener('click', closeAddressPicker);
  DOM.addressApplyBtn.addEventListener('click', applyAddressFilter);
  DOM.addressSearchInput.addEventListener('input', () => {
    state.addressPickerLimit = ADDRESS_PAGE_SIZE;
    renderAddressPicker();
  });
  DOM.addressPickerOverlay.addEventListener('click', closeAddressPicker);
  DOM.addressPickerContent.addEventListener('click', handleAddressPickerClick);

  DOM.addCollectionBtn.addEventListener('click', () => {
    toggleDrawer();
    showAddCollectionDialog('photos');
  });
  DOM.addCollectionCancelBtn.addEventListener('click', closeAddCollectionDialog);
  DOM.addCollectionCreateBtn.addEventListener('click', createCollection);
  DOM.headerSelectBtn.addEventListener('click', toggleSelectMode);
  DOM.headerFavoriteBtn.addEventListener('click', openFavorites);

  DOM.deleteCollectionCancelBtn.addEventListener('click', closeDeleteCollectionDialog);
  DOM.deleteCollectionConfirmBtn.addEventListener('click', confirmDeleteCollection);
  DOM.deleteCollectionDialog.addEventListener('click', (event) => {
    if (event.target === DOM.deleteCollectionDialog) closeDeleteCollectionDialog();
  });

  DOM.menuBtn.addEventListener('click', toggleDrawer);
  DOM.drawerOverlay.addEventListener('click', toggleDrawer);
  DOM.logoutBtn.addEventListener('click', doLogout);
  DOM.navDates.addEventListener('click', () => {
    switchMode('dates');
    toggleDrawer();
  });
  DOM.navAddresses.addEventListener('click', () => {
    switchMode('addresses');
    toggleDrawer();
  });
  DOM.navFavorites.addEventListener('click', () => {
    toggleDrawer();
    openFavorites();
  });
  DOM.syncBtn.addEventListener('click', syncNow);
  DOM.updateAppBtn.addEventListener('click', async () => {
    if (DOM.drawer.classList.contains('open')) toggleDrawer();
    showToast('Обновление приложения…');
    await forceUpdatePwa();
  });
  DOM.themeBtn.addEventListener('click', toggleDarkMode);
  DOM.groupButtons.forEach((button) => {
    button.addEventListener('click', () => setGroup(button.dataset.group));
  });

  DOM.selectAllBtn.addEventListener('click', () => {
    const items = state.page?.items || [];
    const allSelected = items.length > 0
      && items.every((item) => state.selected.has(item.photo_id));

    if (allSelected) {
      state.selected.clear();
    } else {
      items.forEach((item) => state.selected.add(item.photo_id));
    }

    DOM.content.querySelectorAll('.photo-tile[data-photo-id]').forEach((tile) => {
      tile.classList.toggle(
        'selected',
        state.selected.has(tile.dataset.photoId),
      );
    });

    updateSelectionBar();
  });
  DOM.favoriteBtn.addEventListener('click', addSelectedToFavorites);
  DOM.copyBtn.addEventListener('click', copySelected);
  DOM.exportBtn.addEventListener('click', shareSelected);
  DOM.clearSelectionBtn.addEventListener('click', clearSelection);

  DOM.previewCloseBtn.addEventListener('click', closePreview);
  DOM.previewCloseBottomBtn.addEventListener('click', closePreview);
  DOM.previewDownloadBtn.addEventListener('click', downloadCurrentPhoto);

  // Прозрачные стрелки по бокам карточки.
  DOM.previewPrevBtn.addEventListener('click', () => stepPreview(-1));
  DOM.previewNextBtn.addEventListener('click', () => stepPreview(1));

  // Листание превью свайпом влево/вправо. Учитываем только заметно
  // горизонтальные жесты, чтобы вертикальная прокрутка не перелистывала.
  let swipeStart = null;

  DOM.previewOverlay.addEventListener('pointerdown', (event) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.target.closest(
      '.preview-action-btn, .preview-close, .preview-nav',
    )) return;

    swipeHandled = false;
    swipeStart = { x: event.clientX, y: event.clientY };
  });

  // После свайпа браузер присылает click по фону — его не нужно трактовать
  // как «закрыть карточку».
  let swipeHandled = false;

  // Слушаем window: pointerup придёт, даже если палец ушёл за оверлей.
  // setPointerCapture здесь нельзя — он делает цель click оверлеем, и
  // обычный тап по снимку закрывал бы карточку.
  window.addEventListener('pointerup', (event) => {
    if (!swipeStart) return;

    const start = swipeStart;

    swipeStart = null;

    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;

    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.2) {
      swipeHandled = true;
      stepPreview(dx < 0 ? 1 : -1);
    }
  });

  window.addEventListener('pointercancel', () => {
    swipeStart = null;
  });

  // Стрелки клавиатуры — то же листание на десктопе.
  document.addEventListener('keydown', (event) => {
    if (!DOM.previewOverlay.classList.contains('open')) return;

    if (event.key === 'ArrowRight') stepPreview(1);
    if (event.key === 'ArrowLeft') stepPreview(-1);
    if (event.key === 'Escape') closePreview();
  });
  DOM.previewOverlay.addEventListener('click', (event) => {
    if (swipeHandled) {
      swipeHandled = false;
      return;
    }

    // Тап по краю снимка листает: левая четверть — назад,
    // правая четверть — вперёд.
    const image = event.target.closest('.preview-image img');

    if (image) {
      const rect = image.getBoundingClientRect();
      const x = event.clientX - rect.left;

      if (x < rect.width * 0.25) {
        stepPreview(-1);
      } else if (x > rect.width * 0.75) {
        stepPreview(1);
      }

      return;
    }

    if (event.target === DOM.previewOverlay) closePreview();
  });
  DOM.previewFavoriteBtn.addEventListener('click', async () => {
    const photoId = state.currentPhotoId;

    if (!photoId) return;

    if (!auth.hasScope('collections:write')) {
      showToast('Избранное доступно ролям с правом на подборки');
      return;
    }

    const inFavorites = state.favorite.has(photoId);

    DOM.previewFavoriteBtn.disabled = true;

    try {
      const data = inFavorites
        ? await api.removeFavorite(photoId)
        : await api.addFavorites([photoId]);

      if (data && Array.isArray(data.photo_ids)) {
        state.favorite = new Set(data.photo_ids);
      } else if (inFavorites) {
        state.favorite.delete(photoId);
      } else {
        state.favorite.add(photoId);
      }

      if (data && data.collection_id) {
        state.favoriteCollectionId = data.collection_id;
      }

      const tile = DOM.content.querySelector(
        `.photo-tile[data-photo-id="${photoId}"]`,
      );

      if (tile) {
        tile.classList.toggle('favorited', state.favorite.has(photoId));
      }

      showToast(inFavorites
        ? 'Убрано из избранного'
        : 'Добавлено в избранное');
    } catch (error) {
      showToast('Не удалось: ' + error.message);
    } finally {
      DOM.previewFavoriteBtn.disabled = false;
      updatePreviewFavoriteButton();
    }
  });
  DOM.previewShareBtn.addEventListener('click', () => {
    if (!state.currentPhotoId) return;

    // Не теряем выбор пользователя: shareSelected() собирает текст
    // синхронно, после чего прежний набор возвращается.
    const previousSelection = state.selected;

    state.selected = new Set([state.currentPhotoId]);
    shareSelected();
    state.selected = previousSelection;
    updateSelectionBar();
  });

  // Заголовок-«назад»: из дня/списка — к корню.
  DOM.headerTitle.addEventListener('click', () => {
    if (state.view.type !== 'root') goRoot();
  });

  // Поиск с задержкой: q — подстрочный поиск, плюс подсказки из QWEN.
  DOM.searchInput.addEventListener('input', () => {
    const query = DOM.searchInput.value.trim();

    clearTimeout(searchTimer);
    clearTimeout(suggestionsTimer);

    if (!query) {
      hideSearchSuggestions();

      if (state.view.type === 'photos') goRoot();

      return;
    }

    if (query.length >= 2) {
      const seq = ++suggestionsSeq;

      suggestionsTimer = setTimeout(async () => {
        try {
          const data = await api.getSearchSuggestions(
            query,
            state.group || undefined,
          );

          if (seq === suggestionsSeq
            && DOM.searchInput.value.trim() === query) {
            renderSearchSuggestions(data);
          }
        } catch (error) {
          // Подсказки — вспомогательные: ошибка не мешает поиску.
        }
      }, 250);
    } else {
      hideSearchSuggestions();
    }

    searchTimer = setTimeout(() => {
      if (query.length >= 2) {
        loadPhotosPage(
          { q: query, group: state.group || undefined },
          { label: `Поиск: ${query}` },
        );
      } else if (state.view.type === 'photos') {
        goRoot();
      }
    }, 350);
  });

  DOM.searchSuggestions.addEventListener('click', (event) => {
    const item = event.target.closest('[data-suggestion-index]');

    if (item) applySearchSuggestion(Number(item.dataset.suggestionIndex));
  });

  DOM.searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      hideSearchSuggestions();
      DOM.searchInput.blur();
    }
  });

  document.addEventListener('pointerdown', (event) => {
    if (DOM.searchSuggestions.hidden) return;
    if (DOM.searchInput.contains(event.target)) return;
    if (DOM.searchSuggestions.contains(event.target)) return;

    hideSearchSuggestions();
  });

  // Долгое нажатие — режим выбора; обычный тап — превью или чекбокс.
  let pressFired = false;
  let pressOrigin = null;

  DOM.content.addEventListener('pointerdown', (event) => {
    // В «Избранном» мультивыбора нет — долгое нажатие не перехватываем.
    const photoTile = state.view.type === 'photos'
      ? event.target.closest('.photo-tile:not(.back-tile)')
      : null;
    const addressTile = event.target.closest('.folder-tile[data-address-index]');
    const tile = photoTile || addressTile;

    if (!tile) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    pressFired = false;
    pressOrigin = { x: event.clientX, y: event.clientY };
    clearTimeout(pressTimer);

    pressTimer = setTimeout(() => {
      pressFired = true;
      pressOrigin = null;

      if (addressTile) {
        state.addressSelectMode = true;
        applySelectModeUi();
        toggleAddressSelection(Number(addressTile.dataset.addressIndex));
      } else {
        state.selectMode = true;
        applySelectModeUi();
        toggleSelection(tile.dataset.photoId);
      }
    }, 500);
  });

  // Отменяем долгое нажатие только при заметном сдвиге пальца: на телефоне
  // pointermove срабатывает от малейшего дрожания.
  DOM.content.addEventListener('pointermove', (event) => {
    if (!pressOrigin) return;

    const dx = event.clientX - pressOrigin.x;
    const dy = event.clientY - pressOrigin.y;

    if (Math.hypot(dx, dy) > 10) {
      clearTimeout(pressTimer);
      pressOrigin = null;
    }
  });

  ['pointerup', 'pointerleave', 'pointercancel'].forEach((name) => {
    DOM.content.addEventListener(name, () => {
      clearTimeout(pressTimer);
      pressOrigin = null;
    });
  });

  // Долгое нажатие на Android открывает контекстное меню «Сохранить фото».
  DOM.content.addEventListener('contextmenu', (event) => {
    if (event.target.closest('.photo-tile, .folder-tile')) {
      event.preventDefault();
    }
  });

  DOM.content.addEventListener('click', (event) => {
    // Клик после долгого нажатия не должен снимать только что поставленный выбор.
    if (pressFired) {
      pressFired = false;
      return;
    }

    // Кнопка удаления на плитке подборки — раньше остальных веток, иначе
    // клик открыл бы подборку.
    const deleteBtn = event.target.closest('[data-delete-collection]');

    if (deleteBtn) {
      showDeleteCollectionDialog(
        state.collections[Number(deleteBtn.dataset.deleteCollection)],
      );
      return;
    }

    const deleteFavoriteBtn = event.target.closest(
      '[data-delete-favorite-collection]',
    );

    if (deleteFavoriteBtn) {
      showDeleteCollectionDialog(
        state.favoriteCollections[
          Number(deleteFavoriteBtn.dataset.deleteFavoriteCollection)
        ],
      );
      return;
    }

    const loadMore = event.target.closest('[data-action]');

    if (loadMore) {
      const action = loadMore.dataset.action;

      if (action === 'load-more-photos') {
        const params = state.page?.params || {};
        loadPhotosPage(params, { label: state.page?.label, append: true });
      } else if (action === 'load-more-favorites') {
        loadPhotosPage(
          state.page?.params || {},
          { label: 'Избранное', append: true, viewType: 'favorites' },
        );
      } else if (action === 'more-addresses') {
        state.addressLimit += ADDRESS_PAGE_SIZE;
        render();
      } else if (action === 'download-favorites') {
        downloadFavorites();
      } else if (action === 'share-favorites') {
        shareFavorites();
      } else if (action === 'name-favorites') {
        showAddCollectionDialog('favorites');
      } else if (action === 'add-collection') {
        showAddCollectionDialog();
      } else if (action === 'back') {
        goRoot();
      }

      return;
    }

    const addCollectionCard = event.target.closest('[data-add-collection]');

    if (addCollectionCard) {
      if (addCollectionCard.classList.contains('disabled')) {
        showToast(auth.hasScope('collections:write')
          ? 'Сначала выберите адреса'
          : 'Нет прав на создание подборок');
        return;
      }

      showAddCollectionDialog('addresses');
      return;
    }

    const dayCard = event.target.closest('[data-day-index]');

    if (dayCard) {
      openDay(state.days[Number(dayCard.dataset.dayIndex)]);
      return;
    }

    const collectionCard = event.target.closest('[data-collection-index]');

    if (collectionCard) {
      openCollection(state.collections[Number(collectionCard.dataset.collectionIndex)]);
      return;
    }

    const favoriteCollectionCard = event.target.closest(
      '[data-favorite-collection-index]',
    );

    if (favoriteCollectionCard) {
      openCollection(
        state.favoriteCollections[
          Number(favoriteCollectionCard.dataset.favoriteCollectionIndex)
        ],
      );
      return;
    }

    const addressCard = event.target.closest('[data-address-index]');

    if (addressCard) {
      const index = Number(addressCard.dataset.addressIndex);

      if (state.addressSelectMode) {
        toggleAddressSelection(index);
        return;
      }

      const row = state.addresses[index];

      if (row) {
        state.addressSelected.clear();
        openAddressRow(row);
      }

      return;
    }

    const tile = event.target.closest('.photo-tile');

    if (!tile) return;

    if (state.selectMode) {
      toggleSelection(tile.dataset.photoId);
    } else {
      openPreview(tile.dataset.photoId);
    }
  });
}

// ===== Init =====

async function init() {
  initEvents();

  // Автообновление PWA: проверка раз в сутки и перезагрузка после установки
  // нового service worker. Не блокирует загрузку данных.
  registerPwa();

  DOM.footerPeriod.textContent = `◄ ${PERIODS[state.periodIndex].label} ►`;
  DOM.footerCols.textContent = COLUMN_OPTIONS[state.columns - 3];
  DOM.buildVersion.textContent = '2026-11-22';

  const user = await auth.init();

  if (user) {
    showMainApp(user);
    await loadFavoriteIds();
    await loadData();
  } else {
    console.log('📱 PhotoBAse Mobile PWA');
    console.log(
      '   Backend: http://%s:%s (запустите `python -m app.api.main`)',
      window.location.hostname,
      '8010',
    );
  }
}

init();
