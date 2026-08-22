import { createApp, watch } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { useAppStore } from './stores/app';
import 'katex/dist/katex.min.css';
import './style.css';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

// 初始化 store（从 localStorage 恢复状态）
const appStore = useAppStore();
appStore.initFromStorage();

// 暗色模式同步到 html 根元素：dark: 变体与 .dark body/全局样式才能全站生效
watch(
  () => appStore.dark,
  (dark) => document.documentElement.classList.toggle("dark", dark),
  { immediate: true },
);

app.mount('#app');
