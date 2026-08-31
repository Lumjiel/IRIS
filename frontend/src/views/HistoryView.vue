<template>
  <div class="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500">
    <div class="text-center max-w-md px-6">
      <svg class="w-16 h-16 mx-auto mb-4 text-accent/30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      <h2 class="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">研究历史</h2>
      <p class="text-body mb-4">查看和管理之前的投研会话记录</p>

      <div v-if="history.length === 0" class="text-label text-slate-400">
        暂无历史记录
      </div>
      <div v-else class="space-y-3 text-left max-h-96 overflow-y-auto">
        <div
          v-for="item in history"
          :key="item.id"
          class="p-3 rounded-lg border border-white/60 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl hover:border-accent/50 transition-colors cursor-pointer"
          @click="handleLoad(item)"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-body font-medium text-slate-700 dark:text-slate-300 truncate">{{ item.query || '未命名会话' }}</span>
            <button
              @click.stop="handleDelete(item)"
              class="text-slate-400 hover:text-red-500 transition-colors"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            </button>
          </div>
          <div class="text-label text-slate-400">{{ formatTime(item.timestamp) }}</div>
        </div>
      </div>

      <div class="mt-6 pt-4 border-t border-slate-200 dark:border-slate-700">
        <button
          @click="handleClear"
          class="text-label text-red-500 hover:text-red-600 transition-colors"
          :disabled="history.length === 0"
        >
          清空全部历史
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from '../composables/useToast';
import { getHistory, deleteSession, clearHistory, getSessionById } from '../services/history';
import { setThreadId } from '../services/api';

const toast = useToast();
const router = useRouter();
const history = ref([]);

onMounted(() => {
  loadHistory();
});

const loadHistory = () => {
  history.value = getHistory();
};

/** 真实加载：把会话写进 sessionStorage，跳回聊天页恢复消息与 thread_id */
const handleLoad = (item) => {
  const s = getSessionById(item.id);
  if (!s) {
    toast.error('会话不存在或已删除');
    loadHistory();
    return;
  }
  try {
    sessionStorage.setItem('iris_restore_session', JSON.stringify({
      threadId: s.threadId,
      query: s.query,
      messages: s.messages || [],
    }));
    toast.success('会话已加载');
    router.push('/');
  } catch {
    toast.error('加载失败，请重试');
  }
};

const handleDelete = (item) => {
  if (!confirm(`确定删除会话「${item.query || '未命名会话'}」吗？`)) return;
  if (deleteSession(item.id)) {
    loadHistory();
    toast.success('已删除');
  } else {
    toast.error('删除失败');
  }
};

const handleClear = () => {
  if (!confirm('确定清空全部历史吗？此操作不可恢复。')) return;
  clearHistory();
  loadHistory();
  toast.success('已清空');
};

const formatTime = (ts) => {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  return d.toLocaleDateString();
};
</script>
