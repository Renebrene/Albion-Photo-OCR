// Component test: the backup card shows the paths and the schedule it was given,
// posts the parts the operator ticked, and follows the queue job instead of
// pretending the request finished the backup. Driven by a stubbed global.fetch.
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import BackupModule from '../src/components/BackupModule.vue'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

const STATUS = {
  backup_dir: '/media/alexice/TEST/albion-photobase-backups',
  directory: {
    path: '/media/alexice/TEST/albion-photobase-backups',
    exists: true,
    mounted: true,
    writable: true,
    same_filesystem_as_project: false,
  },
  disk: { path: '/media/alexice/TEST', total: 1e12, free: 4e11, used: 6e11, used_pct: 55 },
  project_dir: '/home/alexice/projects/albion-photobase',
  data_dir: '/home/alexice/projects/albion-photobase/data',
  schedule: {
    unit: 'scene-backup.timer',
    on_calendar: '*-*-* 02:30:00',
    next_human: 'Sun 2026-10-25 02:36:29 MSK',
    last_human: 'Sat 2026-10-24 02:32:30 MSK',
    active: true,
    available: true,
    error: null,
  },
  retention: { keep_daily: 14, keep_weekly: 8, keep_monthly: 6 },
  working_database: 'photobase_ingest_test',
  backups: [
    {
      name: 'photobase_ingest_test_20261024_170357.dump',
      kind: 'database',
      stamp: '20261024_170357',
      created: '2026-10-24T17:03:57+00:00',
      size: 52571351,
      sha256: '6d2ceba66c1b64bd4cca9d2ee3e3a7af19ca978480a338361a1aaeddb2345b30',
      manifest: {},
    },
    {
      name: 'scene-data_20261024_171728.tar.gz',
      kind: 'data',
      stamp: '20261024_171728',
      created: '2026-10-24T17:17:28+00:00',
      size: 366121587,
      sha256: 'abe7d2ebb27e9983ddff49b67eb9dabaae22cdabe1204019a427041882876297',
      manifest: {},
    },
  ],
}

let posted
let jobPolls
let archiveCalls

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    if (method === 'GET' && path === '/api/v1/backup/status') {
      return jsonResponse(STATUS)
    }

    if (method === 'POST' && path === '/api/v1/backup/run') {
      posted.push(JSON.parse(options.body))
      return jsonResponse({ job_id: 4242, parts: ['database', 'data'] })
    }

    if (method === 'GET' && path === '/api/v1/jobs/4242') {
      jobPolls += 1
      return jsonResponse({
        id: 4242,
        job_type: 'BACKUP',
        status: 'DONE',
        progress: { done: 2, total: 2, stage: 'бэкап готов', percent: 100 },
        result: { parts: ['database', 'data'] },
      })
    }

    if (method === 'GET' && path.startsWith('/api/v1/backup/archive/')) {
      archiveCalls.push(path)
      return jsonResponse({
        file: 'scene-data_20261024_171728.tar.gz',
        members: [
          'data/fingerprints/56_v33/faiss.index',
          'env/scene-fingerprint.env',
          'models/dinov2/config.json',
        ],
      })
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })
}

async function mountModule({ role = 'Администратор' } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)

  if (role) {
    const session = useSessionStore()
    session.authEnabled = true
    session.user = { name: 'tester', role }
  } else {
    // Без роли — открытый режим: вход выключен на сервере.
    useSessionStore().authEnabled = false
  }

  const wrapper = mount(BackupModule, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()
  return wrapper
}

function button(wrapper, label) {
  return wrapper.findAll('button').find((item) => item.text().includes(label))
}

beforeEach(() => {
  posted = []
  jobPolls = 0
  archiveCalls = []
  installFetch()
})

describe('BackupModule', () => {
  it('shows the backup path, the schedule and every backup it was given', async () => {
    const wrapper = await mountModule()
    const text = wrapper.text()

    expect(text).toContain('/media/alexice/TEST/albion-photobase-backups')
    expect(text).toContain('scene-backup.timer')
    expect(text).toContain('*-*-* 02:30:00')
    expect(text).toContain('Sun 2026-10-25 02:36:29 MSK')
    expect(text).toContain('photobase_ingest_test_20261024_170357.dump')
    expect(text).toContain('scene-data_20261024_171728.tar.gz')
    // Размеры показываются в человеческих единицах, а не байтами.
    expect(text).toContain('50.1 МБ')
    expect(text).toContain('349.2 МБ')
    // Том другой — значит, бэкап переживёт смерть диска проекта.
    expect(text).toContain('отдельный том')
  })

  it('posts the ticked parts and follows the queue job', async () => {
    const wrapper = await mountModule()

    const start = button(wrapper, 'Создать бэкап')
    expect(start).toBeTruthy()

    await start.trigger('click')
    await flushPromises()

    expect(posted).toEqual([{ parts: ['database', 'data'], allow_same_filesystem: false }])
    expect(jobPolls).toBeGreaterThan(0)
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'positive' }),
    )
  })

  it('adds the models when they are ticked', async () => {
    const wrapper = await mountModule()

    const models = wrapper
      .findAll('.q-checkbox')
      .find((item) => item.text().includes('Модели'))
    await models.trigger('click')

    await button(wrapper, 'Создать бэкап').trigger('click')
    await flushPromises()

    expect(posted[0].parts).toEqual(['database', 'data', 'models'])
  })

  it('lists the files inside an archive so they can be restored one by one', async () => {
    const wrapper = await mountModule()

    const open = button(wrapper, 'Выбрать файлы')
    expect(open).toBeTruthy()

    await open.trigger('click')
    await flushPromises()

    expect(archiveCalls).toHaveLength(1)
    expect(document.body.textContent).toContain('data/fingerprints/56_v33/faiss.index')
    expect(document.body.textContent).toContain('models/dinov2/config.json')
    // Слепки и модель отмечены сразу: обычно восстанавливают именно их.
    expect(document.body.textContent).toContain('Отмечено 2 из 3')
  })

  it('refuses to start a backup when nothing is ticked', async () => {
    const wrapper = await mountModule()

    for (const label of ['База данных', 'Данные и слепки']) {
      const box = wrapper.findAll('.q-checkbox').find((item) => item.text().includes(label))
      await box.trigger('click')
    }

    await button(wrapper, 'Создать бэкап').trigger('click')
    await flushPromises()

    expect(posted).toEqual([])
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'warning' }),
    )
  })

  it('hides restore and run controls from a role that may not manage backups', async () => {
    // Гость видит пути, расписание и опись, но не кнопки запуска и
    // восстановления: это scope settings:write, то есть Администратор.
    const wrapper = await mountModule({ role: 'Гость' })

    expect(wrapper.text()).toContain('/media/alexice/TEST/albion-photobase-backups')
    expect(wrapper.text()).toContain('scene-backup.timer')
    expect(wrapper.text()).toContain('Запуск доступен только Администратору')
    expect(button(wrapper, 'В папку')).toBeUndefined()
    expect(button(wrapper, 'На место')).toBeUndefined()

    const start = button(wrapper, 'Создать бэкап')
    expect(start.attributes('disabled')).toBeDefined()
  })
})
