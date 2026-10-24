// Сквозной периодический опрос для Vue-компонентов и сторов.
//
// Проверка аудита: в проекте пять самописных циклов опроса (шапка,
// «Система», два в цикле слепков, ссылки облака), и почти у каждого свои
// болезни — тики накладываются (ответ дольше интервала), скрытая вкладка
// продолжает бить API часами, уход со страницы оставляет запросы и Notify в
// мёртвый компонент, один сетевой сбой навсегда рвёт цикл.
//
// Здесь это решено один раз:
//   * наложение — тик пропускается, пока предыдущий не завершился;
//   * скрытая вкладка — опрос пропускается, при возврате опрос идёт сразу;
//   * остановка — таймер и слушатель снимаются, «поколение» гасит уже
//     начатые ответы (они не трогают состояние после stop);
//   * ошибки — на усмотрение задачи: `tick` не глотает исключение, а
//     вызывающий решает, что делать (счётчик ретраев, текст ошибки).
//
// Использование в компоненте:
//
//   const poller = usePoller(async () => { info.value = await fetchSystem() },
//                            { intervalMs: 2000, immediate: true })
//   poller.start()          // остановится само при размонтировании
//
// В сторе (жизненного цикла компонента нет) берут `createPoller` и зовут
// start/stop сами.
import { onBeforeUnmount } from 'vue'

export function createPoller(task, { intervalMs = 2000, immediate = false } = {}) {
  let timer = null
  let inFlight = false
  let generation = 0
  let listeners = []
  let stopped = true

  function isHidden() {
    return typeof document !== 'undefined' && document.hidden
  }

  async function tick() {
    if (stopped || inFlight) return
    if (isHidden()) return

    inFlight = true
    const my = generation

    try {
      await task(my)
    } finally {
      inFlight = false
    }
  }

  // Устаревший ответ: его поколение уже сменилось остановкой/перезапуском.
  function isCurrent(my) {
    return my === generation
  }

  function onVisibility() {
    if (!isHidden()) void tick()
  }

  function start() {
    if (timer !== null) return

    stopped = false
    generation += 1
    timer = window.setInterval(tick, intervalMs)

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisibility)
      listeners.push(() => document.removeEventListener('visibilitychange', onVisibility))
    }

    if (immediate) void tick()
  }

  function stop() {
    if (timer !== null) window.clearInterval(timer)

    timer = null
    stopped = true
    generation += 1 // начатые ответы больше не применятся

    for (const off of listeners) off()
    listeners = []
  }

  return {
    start,
    stop,
    tick,
    isCurrent,
    get running() {
      return timer !== null
    },
  }
}

export function usePoller(task, options) {
  const poller = createPoller(task, options)

  onBeforeUnmount(poller.stop)

  return poller
}
