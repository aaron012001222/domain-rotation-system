// frontend/src/main.js
import './assets/main.css'

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 引入 Element Plus 样式

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)
app.use(ElementPlus) // 全局注册 Element Plus

app.mount('#app')