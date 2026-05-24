import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router/index.js'
import App from './App.vue'
import './index.css'

const app = createApp(App)

app.use(createPinia())   // ← MUST be before router
app.use(router)

app.mount('#app')
