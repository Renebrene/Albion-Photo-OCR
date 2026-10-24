// Header «Обновление базы»: наблюдает за прогоном и управляет им.
// Диалоги Quasar рисуются в портале, поэтому их ищем в document.body.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import PipelineUpdateButton from '../src/components/PipelineUpdateButton.vue'

Notify.create = vi.fn()

const calls = []

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function setPipeline(payload, status = 200) {
  global.fetch = vi.fn(async (url, options = {}) => {
    calls.push({ url: String(url), method: (options.method || 'GET').toUpperCase() })
    return json(payload, status)
  })
}

function bodyButton(label) {
  return Array.from(document.body.querySelectorAll('button')).find((button) =>
    button.textContent.includes(label),
  )
}

async function mountButton(props = {}) {
  const wrapper = mount(PipelineUpdateButton, {
    global: { plugins: [Quasar] },
    props: { canRun: true, ...props },
    attachTo: document.body,
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  calls.length = 0
  Notify.create = vi.fn()
})

afterEach(() => {
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('Обновление базы', () => {
  it('скрывается, пока супервизор не развёрнут (404)', async () => {
    setPipeline({ detail: 'Not Found' }, 404)
    const wrapper = await mountButton()
    expect(wrapper.find('.pipeline-control').exists()).toBe(false)
    wrapper.unmount()
  })

  it('показывает кнопку, когда API доступен и прогона нет', async () => {
    setPipeline({ run: null })
    const wrapper = await mountButton()
    expect(wrapper.find('.pipeline-control').exists()).toBe(true)
    expect(wrapper.text()).toContain('Обновление базы')
    wrapper.unmount()
  })

  it('показывает живой прогресс INGEST «обработано x/y»', async () => {
    setPipeline({
      run: {
        run_id: 1, status: 'RUNNING', stage: 'INGEST', manifest: { files: ['a.jpg', 'b.jpg', 'c.jpg'] },
        stages: [{ stage: 'INGEST', done_count: 1, failed_count: 0, total_count: 3 }],
      },
    })
    const wrapper = await mountButton()
    expect(wrapper.text()).toContain('Обработано медиа 1/3')
    wrapper.unmount()
  })

  it('показывает прогресс стадии QWEN', async () => {
    setPipeline({
      run: {
        run_id: 1, status: 'RUNNING', stage: 'QWEN', manifest: {},
        stages: [{ stage: 'QWEN', done_count: 5, failed_count: 0, total_count: 10 }],
      },
    })
    const wrapper = await mountButton()
    expect(wrapper.text()).toContain('Описаний: 5')
    wrapper.unmount()
  })

  it('во время DINO число не дублируется: прогресс показывает строка прогона', async () => {
    setPipeline({
      run: {
        run_id: 1, status: 'RUNNING', stage: 'DINO', manifest: {},
        stages: [{ stage: 'DINO', done_count: 13686, failed_count: 2, total_count: 20904 }],
      },
    })
    const wrapper = await mountButton()
    expect(wrapper.find('.pipeline-status').exists()).toBe(false)
    wrapper.unmount()
  })

  it('показывает описания, когда параллельно идёт QWEN', async () => {
    setPipeline({
      run: {
        run_id: 1, status: 'RUNNING', stage: 'DINO', manifest: {},
        stages: [
          { stage: 'DINO', done_count: 13686, failed_count: 2, total_count: 20904 },
          { stage: 'QWEN', done_count: 5, failed_count: 0, total_count: 100 },
        ],
      },
    })
    const wrapper = await mountButton()
    expect(wrapper.find('.pipeline-status').text()).toContain('Описаний: 5')
    wrapper.unmount()
  })

  it('показывает «База обновлена» после завершения', async () => {
    setPipeline({
      run: {
        run_id: 1, status: 'DONE', stage: 'QWEN', finished_at: '2026-10-16 12:30:00',
        manifest: {}, stages: [],
      },
    })
    const wrapper = await mountButton()
    expect(wrapper.text()).toContain('База обновлена 2026-10-16 12:30')
    wrapper.unmount()
  })

  it('во время прогона открывает окно с остановкой и шлёт stop', async () => {
    setPipeline({
      run: { run_id: 42, status: 'RUNNING', stage: 'DINO', manifest: {}, stages: [{ stage: 'DINO', done_count: 3, total_count: 10 }] },
    })
    const wrapper = await mountButton()

    await bodyButton('Обновление базы').click()
    await flushPromises()

    expect(document.body.textContent).toContain('Остановить')
    await bodyButton('Остановить').click()
    await flushPromises()

    expect(calls.some((c) => c.url.endsWith('/v1/pipeline/42/stop'))).toBe(true)
    wrapper.unmount()
  })

  it('остановленный прогон предлагает Продолжить / Начать заново', async () => {
    setPipeline({
      run: { run_id: 7, status: 'STOPPED', stage: 'DINO', finished_at: '2026-10-16 12:00:00', manifest: {}, stages: [] },
    })
    const wrapper = await mountButton()

    expect(wrapper.text()).toContain('Процесс прерван 2026-10-16 12:00')

    await bodyButton('Обновление базы').click()
    await flushPromises()

    expect(document.body.textContent).toContain('Продолжить')
    expect(document.body.textContent).toContain('Начать заново')

    await bodyButton('Продолжить').click()
    await flushPromises()

    expect(calls.some((c) => c.url.endsWith('/v1/pipeline/7/resume'))).toBe(true)
    wrapper.unmount()
  })

  it('не даёт Гостю запустить прогон', async () => {
    setPipeline({ run: null })
    const wrapper = await mountButton({ canRun: false })

    const button = wrapper
      .findAll('button')
      .find((item) => item.text().includes('Обновление базы'))

    expect(button.attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
})
