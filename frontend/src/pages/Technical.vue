<script setup>
import { computed, ref } from 'vue'

import { useSessionStore } from '../stores/session'
import Processing from './Processing.vue'
import Settings from './Settings.vue'
import BaseSettings from '../components/BaseSettings.vue'
import UsersAdmin from '../components/UsersAdmin.vue'
import SystemMonitor from '../components/SystemMonitor.vue'
import FingerprintsList from '../components/FingerprintsList.vue'
import LastRun from '../components/LastRun.vue'
import DataModule from '../components/DataModule.vue'
import Automation from '../components/Automation.vue'
import DisplaySettings from '../components/DisplaySettings.vue'
import AddressDirectory from '../components/AddressDirectory.vue'
import ClientNormalization from '../components/ClientNormalization.vue'
import VisitsAdmin from '../components/VisitsAdmin.vue'
import IngestFolder from '../components/IngestFolder.vue'

// Mirrors the legacy NiceGUI "технический раздел" (components/technical.py)
// with its modules: photo_processing, qwen, automation, users, data.
const tab = ref('processing')

const session = useSessionStore()

// The user directory is administrator-only.
const isAdmin = computed(() => session.user?.role === 'Администратор')

// Editing client aliases needs the collections:write scope, which Администратор
// and Менеджер have; Гость would only get 403s, so the block is hidden for it.
const canEditClients = computed(() =>
  ['Администратор', 'Менеджер'].includes(session.user?.role),
)
</script>

<template>
  <q-page class="q-pa-md">
    <div class="text-h6 q-mb-md">Технический раздел</div>

    <!-- Порядок задан владельцем: сначала работа с фотографиями, затем службы,
         затем слепки и адреса, в конце — пользователи и вид. -->
    <q-tabs v-model="tab" dense align="left" class="text-primary q-mb-sm">
      <span class="tab-sep" />
      <q-tab name="ingest" icon="folder_open" label="Загрузка" />
      <q-tab name="processing" icon="play_circle" label="Обработка" />
      <q-tab name="qwen" icon="auto_awesome" label="Распознавание" />
      <span class="tab-sep" />
      <q-tab name="automation" icon="schedule" label="Автоматизация" />
      <q-tab name="last_run" icon="history" label="Последний запуск" />
      <q-tab name="system" icon="monitor_heart" label="Система" />
      <q-tab name="base" icon="tune" label="Настройки" />
      <q-tab name="data" icon="storage" label="Данные" />
      <span class="tab-sep" />
      <q-tab name="fingerprints" icon="fingerprint" label="Слепки" />
      <q-tab name="addresses" icon="place" label="Адреса" />
      <span class="tab-sep" />
      <q-tab v-if="isAdmin" name="users" icon="group" label="Пользователи" />
      <q-tab v-if="isAdmin" name="visits" icon="history_toggle_off" label="Посещения" />
      <q-tab name="display" icon="grid_view" label="Отображение" />
      <span class="tab-sep" />
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

      <q-tab-panel name="base">
        <BaseSettings />
      </q-tab-panel>

      <q-tab-panel name="fingerprints">
        <FingerprintsList />
      </q-tab-panel>

      <q-tab-panel name="addresses">
        <AddressDirectory />
      </q-tab-panel>

      <q-tab-panel name="automation">
        <Automation />
      </q-tab-panel>

      <q-tab-panel name="ingest">
        <IngestFolder />
      </q-tab-panel>

      <q-tab-panel name="display">
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-card flat bordered>
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
          </div>

          <div v-if="canEditClients" class="col-12 col-md-6">
            <q-card flat bordered>
              <q-card-section>
                <ClientNormalization />
                <div class="text-caption text-grey q-mt-sm">
                  Раньше этот блок стоял на странице фото в правой колонке.
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-tab-panel>

      <q-tab-panel v-if="isAdmin" name="users">
        <UsersAdmin />
      </q-tab-panel>

      <q-tab-panel v-if="isAdmin" name="visits">
        <VisitsAdmin />
      </q-tab-panel>

      <q-tab-panel name="data">
        <DataModule />
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>

<style scoped>
/* Разделители групп вкладок технического раздела. */
.tab-sep {
  width: 1px;
  height: 20px;
  align-self: center;
  margin: 0 10px;
  background: rgba(0, 0, 0, 0.16);
}

body.body--dark .tab-sep {
  background: rgba(255, 255, 255, 0.24);
}
</style>
