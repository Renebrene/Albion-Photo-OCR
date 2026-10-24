// Опрос задания до терминального состояния — с ретраями и отменой.
//
// Вынесено из окна слепков, чтобы поведение можно было проверить тестом:
// цикл «каждые 2 секунды спросить статус» ломался на первом же сетевом сбое
// и продолжал работать после ухода со страницы.
import { computed, onBeforeUnmount } from 'vue'

export const POLL_STEP_MS = 2000
export const POLL_MAX_FAILURES = 3

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/**
 * @param fetchOnce  () => Promise<данные>
 * @param isFinished (данные) => boolean — терминальное состояние
 * @returns { data } | { cancelled } | { error } | { timeout }
 */
export async function pollUntil(
  fetchOnce,
  isFinished,
  {
    tries = 120,
    stepMs = POLL_STEP_MS,
    maxFailures = POLL_MAX_FAILURES,
    isCancelled = () => false,
  } = {},
) {
  let failures = 0

  for (let attempt = 0; attempt < tries; attempt += 1) {
    await sleep(stepMs)

    // Скрытая вкладка не опрашивает API: задание всё равно идёт в воркере, а
    // ответ понадобится, когда пользователь вернётся. Раньше скрытая страница
    // продолжала стучать в API каждые две секунды.
    // Ждём возвращения, не расходуя попытки: иначе длинный уход со страницы
    // «съедал» все tries и опрос завершался таймаутом.
    while (
      typeof document !== 'undefined'
      && document.hidden
      && !isCancelled()
    ) {
      await sleep(stepMs)
    }

    if (isCancelled()) return { cancelled: true }

    try {
      const data = await fetchOnce()

      // Счётчик сбоев обнуляется только после успешного запроса: иначе
      // «три подряд» никогда не сработает.
      failures = 0

      if (isFinished(data)) return { data }
    } catch (err) {
      failures += 1

      if (failures >= maxFailures) return { error: err }
    }
  }

  return { timeout: true }
}

/**
 * Поколение опроса для компонента: закрытие диалога и уход со страницы гасят
 * цикл, а ответ старого цикла больше не пишет в состояние.
 */
export function usePollToken() {
  let token = 0

  onBeforeUnmount(() => {
    token += 1
  })

  return {
    bump() {
      token += 1
      return token
    },
    isCancelled(my) {
      return my !== token
    },
  }
}
