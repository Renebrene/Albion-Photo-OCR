<script setup>
import { ref } from 'vue'

import Processing from './Processing.vue'
import Settings from './Settings.vue'
import UsersAdmin from '../components/UsersAdmin.vue'
import SystemMonitor from '../components/SystemMonitor.vue'
import FingerprintsList from '../components/FingerprintsList.vue'
import LastRun from '../components/LastRun.vue'
import DataModule from '../components/DataModule.vue'

// Mirrors the legacy NiceGUI "технический раздел" (components/technical.py)
// with its modules: photo_processing, qwen, automation, users, data.
const tab = ref('processing')
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
      <q-tab name="users" icon="group" label="Пользователи" />
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
        <q-banner class="bg-grey-2">
          Модуль автоматизации (watcher / расписание запусков) из легаси-NiceGUI
          пока не реализован. Сейчас запуск — вручную из «Обработка» или через
          очередь заданий (<code>app.jobs.worker</code>).
        </q-banner>
      </q-tab-panel>

      <q-tab-panel name="users">
        <UsersAdmin />
      </q-tab-panel>

      <q-tab-panel name="data">
        <DataModule />
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>
