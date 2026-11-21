// Запрещённые к выдаче слова (настройка рядом с нормализацией клиентов).
//
// Фронтенд читает тот же список, что и обработка QWEN, и не пропускает такие
// слова в ручную правку карточки: мат и обрывки распознавания не должны
// сохраняться в описание, клиента, бренд или теги (владелец, 21.11.2026).
// Сервер проверяет то же самое — фронтенд лишь говорит об этом сразу.
import { fetchQwenSettings } from '../api/client'

/** Список с сервера; при сбое — пустой (сервер всё равно проверит сохранение). */
export async function loadForbiddenWords() {
  try {
    const data = await fetchQwenSettings()
    return Array.isArray(data?.forbidden_words) ? data.forbidden_words : []
  } catch {
    return []
  }
}

/** Словесный символ: буква или цифра любого алфавита (Cyrillic в `\b` не входит). */
function isWordChar(char) {
  return Boolean(char) && /[\p{L}\p{N}_]/u.test(char)
}

function isLower(char) {
  return Boolean(char) && /\p{Ll}/u.test(char)
}

function isUpper(char) {
  return Boolean(char) && /\p{Lu}/u.test(char)
}

/** Начало слова: разделитель или слипшееся слово с заглавной («СистемаПедо»). */
function startsWordAt(value, at) {
  if (at <= 0) return true

  const previous = value[at - 1]

  if (!isWordChar(previous)) return true

  return isLower(previous) && isUpper(value[at])
}

/** Конец слова: разделитель или заглавная после строчной («ПедоСистема»). */
function endsWordAt(value, end) {
  if (end >= value.length) return true

  const next = value[end]

  if (!isWordChar(next)) return true

  return isLower(value[end - 1]) && isUpper(next)
}

/**
 * Первое запрещённое слово в тексте — **целым словом**, без учёта регистра.
 *
 * «педо» ловится в «педо, щит» и «СистемаПедо», но не в «торпедо»: иначе
 * список режет нормальные слова (владелец, 21.11.2026).
 */
export function findForbiddenWord(text, words) {
  const value = String(text ?? '')
  const lower = value.toLocaleLowerCase('ru')

  for (const word of words || []) {
    const needle = String(word ?? '').trim().toLocaleLowerCase('ru')

    if (!needle) continue

    // Граница проверяется только с той стороны, где у слова словесный край:
    // «#мат» ищется и внутри других символов, «мат» — только словом.
    const needsStart = isWordChar(needle[0])
    const needsEnd = isWordChar(needle[needle.length - 1])

    let from = 0

    while (from <= lower.length) {
      const at = lower.indexOf(needle, from)

      if (at < 0) break

      const startOk = !needsStart || startsWordAt(value, at)
      const endOk = !needsEnd || endsWordAt(value, at + needle.length)

      if (startOk && endOk) return word

      from = at + 1
    }
  }

  return null
}

/**
 * Какие поля правки содержат запрещённые слова.
 *
 * `fields.tags` — строка через запятую, как в форме правки.
 */
export function forbiddenFieldHits(fields, words) {
  if (!words || !words.length) return []

  const hits = []

  for (const key of ['description', 'client', 'brand']) {
    const word = findForbiddenWord(fields?.[key], words)

    if (word) hits.push({ field: key, word })
  }

  for (const tag of String(fields?.tags || '').split(',')) {
    const word = findForbiddenWord(tag, words)

    if (word) {
      hits.push({ field: 'tags', word, value: tag.trim() })
      break
    }
  }

  return hits
}
