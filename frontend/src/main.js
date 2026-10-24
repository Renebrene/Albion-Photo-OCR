import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { Quasar } from 'quasar'

import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/dist/quasar.css'
// Loaded after Quasar so the calmer look wins (presentation only).
import './css/app.css'

import App from './App.vue'
import { QUASAR_PLUGINS } from './quasar-plugins'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Quasar, { plugins: QUASAR_PLUGINS })

app.mount('#app')
