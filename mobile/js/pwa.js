/**
 * Обновление PWA-оболочки.
 *
 * - регистрирует service worker с `updateViaCache: 'none'`;
 * - проверяет обновление при запуске и не чаще одного раза в сутки
 *   (а также при возврате на вкладку), затем перезагружает страницу,
 *   когда новый SW встал под контроль;
 * - `forceUpdatePwa()` — принудительное обновление из меню: проверка
 *   обновления, активация нового SW, очистка кэшей и перезагрузка.
 */

const SW_CHECK_KEY = 'photobase_sw_checked_on';

let registration = null;
let reloading = false;
let hadController = false;

function todayKey() {
  const now = new Date();

  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0'),
  ].join('-');
}

function reloadOnce() {
  if (reloading) return;

  reloading = true;
  window.location.reload();
}

/** Проверка обновлений: не чаще одного раза в сутки. */
async function updateOncePerDay() {
  if (!registration) return;

  const today = todayKey();

  if (localStorage.getItem(SW_CHECK_KEY) === today) return;

  localStorage.setItem(SW_CHECK_KEY, today);

  try {
    await registration.update();
  } catch (error) {
    // Нет сети или обновление уже идёт — не мешаем работе приложения.
    console.log('SW update check failed:', error);
  }

  // Заодно чистим старые записи кэша (раз в сутки).
  try {
    registration.active?.postMessage('cleanup');
  } catch (error) {
    console.log('SW cleanup message failed:', error);
  }
}

/** Зарегистрировать SW и включить автообновление. */
export async function registerPwa() {
  if (!('serviceWorker' in navigator)) return null;

  // Первая установка не должна перезагружать страницу: контроллера ещё нет.
  hadController = !!navigator.serviceWorker.controller;

  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (hadController) reloadOnce();
  });

  try {
    registration = await navigator.serviceWorker.register('sw.js', {
      updateViaCache: 'none',
    });
  } catch (error) {
    console.log('SW registration failed:', error);
    return null;
  }

  await updateOncePerDay();

  // Приложение может быть открыто сутками: проверяем смену дня при
  // возврате на вкладку.
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') updateOncePerDay();
  });

  return registration;
}

/** Принудительное обновление: меню → проверка, кэши, перезагрузка. */
export async function forceUpdatePwa() {
  try {
    const registrations = await navigator.serviceWorker.getRegistrations();

    await Promise.all(registrations.map(async (item) => {
      try {
        await item.update();

        const worker = item.installing || item.waiting;

        if (worker) worker.postMessage({ type: 'skip-waiting' });
      } catch (error) {
        console.log('SW force update failed:', error);
      }
    }));

    if (window.caches) {
      // Только кэши мобильной оболочки: оверлей живёт на том же origin,
      // что и десктопная SPA, чужие кэши не трогаем.
      const keys = (await caches.keys())
        .filter((key) => key.startsWith('albion-'));

      await Promise.all(keys.map((key) => caches.delete(key)));
    }
  } catch (error) {
    console.log('PWA force update failed:', error);
  }

  localStorage.removeItem(SW_CHECK_KEY);
  window.location.reload();
}
