<template>
  <div class="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500">
    <div class="text-center max-w-md px-6">
      <svg class="w-16 h-16 mx-auto mb-4 text-accent/30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 6V4M12 6C10.3431 6 9 7.34315 9 9C9 10.6569 10.3431 12 12 12C13.6569 12 15 13.6569 15 15C15 16.3431 13.6569 17.6962 12 17.6962"/>
        <path d="M12 6C13.6569 6 15 7.34315 15 9"/>
        <path d="M12 17.6962V20"/>
      </svg>
      <h2 class="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">设置</h2>
      <p class="text-body mb-6">配置 API 密钥、模型偏好和研究参数</p>

      <div class="space-y-4 text-left">
        <div>
          <label class="text-label text-slate-600 dark:text-slate-400 block mb-1">API 端点</label>
          <input
            v-model="apiBase"
            type="text"
            class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-body text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
            placeholder="http://localhost:8000"
          />
        </div>
        <div>
          <label class="text-label text-slate-600 dark:text-slate-400 block mb-1">搜索模式</label>
          <select
            v-model="searchMode"
            class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-body text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
          >
            <option value="hybrid">混合搜索（推荐）</option>
            <option value="document">仅本地文档</option>
          </select>
        </div>
        <button
          @click="handleSave"
          class="w-full py-2 rounded-md bg-accent hover:bg-accent/90 text-white text-body font-medium transition-colors"
        >
          保存设置
        </button>
      </div>

        <div class="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700 w-full">
          <div class="flex items-center justify-between mb-2">
            <span class="text-label text-slate-600 dark:text-slate-400">长期记忆（跨会话）</span>
            <button @click="loadMemories" class="text-label text-accent hover:underline">刷新</button>
          </div>
          <p v-if="!memories.length" class="text-caption text-slate-400">暂无记忆。研究过的股票和"记住…"的偏好会自动保存到这里。</p>
          <ul v-else class="space-y-2 max-h-48 overflow-y-auto">
            <li v-for="m in memories" :key="m.key" class="flex items-start justify-between gap-2 px-2 py-1.5 rounded bg-slate-50 dark:bg-slate-800/60">
              <div class="min-w-0">
                <span class="text-[10px] uppercase tracking-wide text-accent/80 mr-1">{{ m.kind }}</span>
                <span class="text-body text-slate-700 dark:text-slate-300 break-all">{{ m.content }}</span>
              </div>
              <button @click="handleDeleteMemory(m)" class="shrink-0 text-label text-red-400 hover:text-red-600">删除</button>
            </li>
          </ul>
        </div>

      <div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
        <button
          @click="handleResetSession"
          class="text-label text-red-500 hover:text-red-600 transition-colors"
        >
          重置会话（清除 thread_id）
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useAppStore } from '../stores/app';
import { useToast } from '../composables/useToast';
import { listMemories, deleteMemory } from '../services/api';

const appStore = useAppStore();
const toast = useToast();

const apiBase = ref(localStorage.getItem('iris_api_base') || 'http://localhost:8000');
const searchMode = ref(localStorage.getItem('iris_search_mode') || 'hybrid');

const handleSave = () => {
  localStorage.setItem('iris_api_base', apiBase.value);
  localStorage.setItem('iris_search_mode', searchMode.value);
  appStore.setPreferences({ apiBase: apiBase.value, searchMode: searchMode.value });
  toast.success('设置已保存');
};

const handleResetSession = () => {
  appStore.resetSession();
  toast.success('会话已重置');
};

// === 长期记忆管理 ===
const memories = ref([]);

async function loadMemories() {
  try {
    const data = await listMemories();
    memories.value = data.items || [];
  } catch {
    toast.error('记忆加载失败');
  }
}

async function handleDeleteMemory(m) {
  // 红线操作：二次确认
  if (!confirm(`确定删除这条记忆吗？\n\n${m.content}`)) return;
  try {
    await deleteMemory(m.key);
    memories.value = memories.value.filter((x) => x.key !== m.key);
    toast.success('记忆已删除');
  } catch {
    toast.error('删除失败');
  }
}

onMounted(loadMemories);
</script>
