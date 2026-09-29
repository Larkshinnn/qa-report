import { createApp } from 'vue'
import { createPinia } from 'pinia'
import '@fontsource/fira-sans/latin-400.css'
import '@fontsource/fira-sans/latin-500.css'
import '@fontsource/fira-sans/latin-600.css'
import '@fontsource/fira-sans/latin-700.css'
import '@fontsource/fira-code/latin-400.css'
import './shared/styles/globals.css'
import App from './App.vue'
import { router } from './router'

createApp(App).use(createPinia()).use(router).mount('#app')
