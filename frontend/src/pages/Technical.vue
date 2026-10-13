<script setup>
import { computed, ref } from 'vue'

import { useSessionStore } from '../stores/session'
import Processing from './Processing.vue'
import Settings from './Settings.vue'
import UsersAdmin from '../components/UsersAdmin.vue'
import SystemMonitor from '../components/SystemMonitor.vue'
import FingerprintsList from '../components/FingerprintsList.vue'
import LastRun from '../components/LastRun.vue'
import DataModule from '../components/DataModule.vue'
import Automation from '../components/Automation.vue'
import DisplaySettings from '../components/DisplaySettings.vue'
import IngestFolder from '../components/IngestFolder.vue'

// Mirrors the legacy NiceGUI "технический раздел" (components/technical.py)
// with its modules: photo_processing, qwen, automation, users, data.
const tab = ref('processing')

const session = useSessionStore()

// The user directory is administrator-only.
const isAdmin = computed(() => session.user?.role === 'Администратор')
</script>

<template>
  <q-page class="q-pa-md">
    <div class="text-h6 q-mb-md">Технический раздел</div>

    <q-tabs v-model="tab" dense align="left" class="text-primary q-mb-sm">
      <q-tab name="processing" icon="play_circle" label="Обработка" />
      <q-tab name="last_run" icon="history" label="Последний запуск" />
      <q-tab name="qwen" icon="auto_awesome" label="QWEN" />
      <q-tab name="automation" icon="schedule" label="Автоматизация" />
      <q-tab name="system" icon="monitor_heart" label="Система" />
      <q-tab name="fingerprints" icon="fingerprint" label="Слепки" />
      <q-tab name="ingest" icon="folder_open" label="Ingest" />
      <q-tab name="display" icon="grid_view" label="Отображение" />
      <q-tab v-if="isAdmin" name="users" icon="group" label="Пользователи" />
      <q-tab name="data" icon="storage" label="Данные" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="processing">
        <Processing />
      </q-tab-panel>

      <q-tab-panel name="last_run">
        <LastRun />
      </q-tab-panel>

      <q-tab-panel name="qwen">
        <Settings />
      </q-tab-panel>

      <q-tab-panel name="system">
        <SystemMonitor />
      </q-tab-panel>

      <q-tab-panel name="fingerprints">
        <FingerprintsList />
      </q-tab-panel>

      <q-tab-panel name="automation">
        <Automation />
      </q-tab-panel>

      <q-tab-panel name="ingest">
        <IngestFolder />
      </q-tab-panel>

      <q-tab-panel name="display">
        <q-card flat bordered style="max-width: 640px">
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">
              Настройки отображения грида
            </div>
            <DisplaySettings />
            <div class="text-caption text-grey q-mt-sm">
              То же окно открывается шестерёнкой рядом с переключателем
              «Плитка/Список» на странице фото.
            </div>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <q-tab-panel v-if="isAdmin" name="users">
        <UsersAdmin />
      </q-tab-panel>

      <q-tab-panel name="data">
        <DataModule />
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>
