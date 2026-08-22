import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { useAppStore } from './stores/app';
import './style.css';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

// 初始化 store（从 localStorage 恢复状态）
const appStore = useAppStore();
appStore.initFromStorage();

app.mount('#app');
