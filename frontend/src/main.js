import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 必须引入 CSS
import App from './App.vue'
import './style.css'

const app = createApp(App)
app.use(ElementPlus)
app.mount('#app')
// createApp(App).mount('#app').use(ElementPlus)

