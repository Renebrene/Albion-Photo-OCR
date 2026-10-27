// ID слепка из имени папки: транслит в ASCII, лимит 64 символа, уникальность.
//
// Сервер принимает только `^[A-Za-z0-9._-]{1,64}$` (app/api/fingerprints.py) и
// Pydantic дополнительно ограничивает длину 64 (app/api/schemas.py). Прежний
// генератор брал последний сегмент пути как есть, поэтому папка «Менжинского 2»
// давала кириллический ID, а длинное имя — превышение лимита; в UI это
// выглядело как «String should have at most 64 characters» или как отказ
// «ID может содержать буквы…» без подсказки, что делать.
//
// Здесь только чистые функции: компонент показывает результат, а тесты
// (tests/fingerprint-id.spec.js) проверяют таблицу транслита, лимит и суффиксы.

export const FINGERPRINT_ID_MAX = 64
export const FINGERPRINT_ID_RE = /^[A-Za-z0-9._-]{1,64}$/
// Версия схемы слепка — та же, что была в прежнем `<имя>_v33`.
export const VERSION_SUFFIX = '_v33'

const TRANSLIT = {
  а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z',
  и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r',
  с: 's', т: 't', у: 'u', ф: 'f', х: 'kh', ц: 'ts', ч: 'ch', ш: 'sh',
  щ: 'shch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
  // Украинские буквы: встречаются в названиях папок, транслит не хуже прочих.
  і: 'i', ї: 'yi', є: 'ye', ґ: 'g',
}

function transliterate(text) {
  let out = ''
  for (const char of String(text ?? '').toLowerCase()) {
    out += TRANSLIT[char] ?? char
  }
  return out
}

/** Обрезает основу так, чтобы `base + extra` уложилось в лимит. */
function capped(base, extra) {
  const room = FINGERPRINT_ID_MAX - extra.length
  const head = base.slice(0, Math.max(1, room)).replace(/[._-]+$/, '')
  return (head || 'fp') + extra
}

/**
 * ASCII-основа ID из имени папки: транслит, недопустимые символы → `_`,
 * лишние разделители схлопываются, хвост обрезается под лимит.
 */
export function slugifyName(name, { suffix = '' } = {}) {
  const cleaned = transliterate(name)
    .replace(/[^a-z0-9._-]+/g, '_')
    .replace(/_{2,}/g, '_')
    .replace(/^[._-]+|[._-]+$/g, '')

  return capped(cleaned, suffix)
}

/**
 * Уникальный ID: при совпадении добавляет `_1`, `_2`, … (с учётом лимита).
 */
export function uniqueId(base, taken = []) {
  const used = taken instanceof Set ? taken : new Set(taken)

  if (!used.has(base)) return base

  for (let index = 1; index <= 999; index += 1) {
    const candidate = capped(base, `_${index}`)
    if (!used.has(candidate)) return candidate
  }

  return capped(base, `_${Date.now()}`)
}

function folderName(dir) {
  if (dir?.name) return dir.name
  return String(dir?.path ?? '').split('/').filter(Boolean).pop() || ''
}

/**
 * ID по умолчанию для списка папок: у каждой свой, без совпадений между собой
 * и с уже существующими слепками. Совпадение с существующим ID опасно: сборка
 * идёт с `replace`, то есть перезаписала бы чужой слепок.
 */
export function assignBatchIds(dirs = [], taken = []) {
  const used = new Set(taken)
  const ids = {}

  for (const dir of dirs) {
    const id = uniqueId(slugifyName(folderName(dir), { suffix: VERSION_SUFFIX }), used)
    used.add(id)
    ids[dir.path] = id
  }

  return ids
}
