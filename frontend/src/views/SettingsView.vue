<template>
  <div class="h-screen overflow-y-auto bg-transparent">
    <div class="min-h-full flex flex-col items-center py-8 px-4">
      <div class="w-full max-w-xl space-y-4">
        <!-- 标题 -->
        <div class="text-center mb-2">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-soft">
            <svg class="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
          </div>
          <h1 class="text-xl font-bold text-slate-900 dark:text-slate-100">设置</h1>
          <p class="text-label text-slate-500 dark:text-slate-400 mt-1">端点 / 偏好 / 记忆 / 系统状态</p>
        </div>

        <!-- ============ 基础设置 ============ -->
        <section class="card p-4 space-y-3">
          <h2 class="text-body font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
            <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            基础设置
          </h2>
          <div>
            <label class="text-label text-slate-600 dark:text-slate-400 block mb-1">API 端点</label>
            <input
              v-model="apiBase"
              type="text"
              class="w-full px-3 py-2 rounded-md border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-lg text-body text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
              placeholder="留空 = 同源（推荐）；或填 http://服务器IP:8000"
            />
            <p class="text-caption text-slate-400 mt-1">留空走同源反向代理；仅前后端不同域时才需要填写完整地址。</p>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="text-label text-slate-600 dark:text-slate-400 block mb-1">搜索模式</label>
              <select
                v-model="searchMode"
                class="w-full px-3 py-2 rounded-md border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-lg text-body text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
              >
                <option value="hybrid">混合搜索（推荐）</option>
                <option value="document">仅本地文档</option>
              </select>
            </div>
            <div>
              <label class="text-label text-slate-600 dark:text-slate-400 block mb-1">回答风格</label>
              <select
                v-model="style"
                class="w-full px-3 py-2 rounded-md border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-lg text-body text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
              >
                <option value="detailed">详细（推荐）</option>
                <option value="concise">简洁</option>
                <option value="formal">正式</option>
                <option value="casual">口语化</option>
              </select>
            </div>
            <div>
              <label class="text-label text-slate-600 dark:text-slate-400 block mb-1">语言</label>
              <select
                v-model="language"
                class="w-full px-3 py-2 rounded-md border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-lg text-body text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
              >
                <option value="zh">中文</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
          <button
            @click="handleSave"
            class="w-full py-2 rounded-md bg-accent hover:bg-accent/90 text-white text-body font-medium transition-colors"
          >
            保存设置
          </button>
        </section>

        <!-- ============ 短期记忆（当前会话） ============ -->
        <section class="card p-4 space-y-3">
          <h2 class="text-body font-semibold text-slate-800 dark:text-slate-200 flex items-center justify-between">
            <span class="flex items-center gap-1.5">
              <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              短期记忆（当前会话）
            </span>
            <button @click="loadSessionMemory" class="text-label text-accent hover:underline">刷新</button>
          </h2>
          <p class="text-caption text-slate-400">同一 thread 内的连续对话摘要，自动更新、超长自动压缩，供后续追问保持上下文。</p>
          <div v-if="sessionSummary" class="p-2.5 rounded-md bg-white/50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700 text-label text-slate-600 dark:text-slate-300 whitespace-pre-wrap max-h-40 overflow-y-auto">{{ sessionSummary }}</div>
          <p v-else class="text-caption text-slate-400">暂无会话摘要。完成一次研究后会自动生成。</p>
          <div class="flex items-center gap-2">
            <button
              @click="handleResetSessionMemory"
              class="text-label text-red-500 hover:text-red-600 transition-colors"
            >
              清空当前会话记忆
            </button>
            <span v-if="sessionTurns > 0" class="text-caption text-slate-400 num ml-auto">{{ sessionTurns }} 轮</span>
          </div>
        </section>

        <!-- ============ 长期记忆（跨会话） ============ -->
        <section class="card p-4 space-y-3">
          <h2 class="text-body font-semibold text-slate-800 dark:text-slate-200 flex items-center justify-between">
            <span class="flex items-center gap-1.5">
              <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12V5a2 2 0 00-2-2H6a2 2 0 00-2 2v13a2 2 0 002 2h6"/><path d="M12 12v7"/><path d="M15 15l-3 3-3-3"/></svg>
              长期记忆（跨会话）
            </span>
            <button @click="loadMemories" class="text-label text-accent hover:underline">刷新</button>
          </h2>
          <p class="text-caption text-slate-400">研究过的股票、说「记住…」的偏好会自动保存；也可手动添加或编辑。</p>

          <!-- 添加表单 -->
          <div v-if="showAdd" class="space-y-2 p-2.5 rounded-md bg-indigo-50/60 dark:bg-indigo-500/5 border border-indigo-100 dark:border-indigo-500/20">
            <div class="flex gap-2">
              <select v-model="newKind" class="shrink-0 px-2 py-1.5 rounded border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 text-label text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent">
                <option value="preference">偏好</option>
                <option value="fact">事实</option>
                <option value="watch_stock">关注股票</option>
              </select>
              <input
                v-model="newContent"
                placeholder="例如：偏好简洁结论先行的回答风格"
                class="flex-1 min-w-0 px-2.5 py-1.5 rounded border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 text-label text-slate-700 dark:text-slate-300 placeholder:text-slate-400 focus:outline-none focus:border-accent"
                @keydown.enter="handleAddMemory"
              />
            </div>
            <div class="flex gap-2 justify-end">
              <button @click="showAdd = false" class="px-3 py-1 rounded-md text-label text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors">取消</button>
              <button @click="handleAddMemory" class="px-3 py-1 rounded-md bg-accent text-white text-label hover:bg-accent/90 transition-colors">添加</button>
            </div>
          </div>

          <!-- 列表 -->
          <p v-if="!memories.length && !showAdd" class="text-caption text-slate-400">暂无记忆。</p>
          <ul v-else class="space-y-2 max-h-56 overflow-y-auto">
            <li
              v-for="m in memories"
              :key="m.key"
              class="flex items-start justify-between gap-2 px-2.5 py-2 rounded-md bg-white/50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/60"
            >
              <!-- 编辑态 -->
              <div v-if="editing.key === m.key" class="flex-1 min-w-0 space-y-1.5">
                <select v-model="editing.kind" class="px-2 py-1 rounded border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 text-label text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent">
                  <option value="preference">偏好</option>
                  <option value="fact">事实</option>
                  <option value="watch_stock">关注股票</option>
                </select>
                <input
                  v-model="editing.content"
                  class="w-full px-2 py-1 rounded border border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 text-label text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
                  @keydown.enter="handleEditMemory(m.key)"
                />
                <div class="flex gap-2">
                  <button @click="handleEditMemory(m.key)" class="text-label text-accent hover:underline">保存</button>
                  <button @click="editing.key = ''" class="text-label text-slate-400 hover:underline">取消</button>
                </div>
              </div>
              <!-- 展示态 -->
              <template v-else>
                <div class="min-w-0">
                  <span class="text-[10px] uppercase tracking-wide px-1 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-accent/80 mr-1.5">{{ KIND_LABEL[m.kind] || m.kind }}</span>
                  <span class="text-body text-slate-700 dark:text-slate-300 break-all">{{ m.content }}</span>
                </div>
                <div class="shrink-0 flex gap-2 text-label">
                  <button @click="startEdit(m)" class="text-slate-400 hover:text-accent transition-colors">编辑</button>
                  <button @click="handleDeleteMemory(m)" class="text-red-400 hover:text-red-600 transition-colors">删除</button>
                </div>
              </template>
            </li>
          </ul>

          <button
            v-if="!showAdd"
            @click="showAdd = true"
            class="w-full py-1.5 rounded-md border border-dashed border-slate-300 dark:border-slate-600 text-label text-slate-500 dark:text-slate-400 hover:border-accent/50 hover:text-accent transition-colors"
          >
            + 添加记忆
          </button>
        </section>

        <!-- ============ 系统状态 ============ -->
        <section class="card p-4 space-y-2">
          <h2 class="text-body font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
            <svg class="w-4 h-4 text-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>
            系统状态
          </h2>
          <div class="grid grid-cols-2 gap-2 text-label">
            <div class="p-2.5 rounded-md bg-white/50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/60">
              <div class="text-slate-400">数据源</div>
              <div class="text-body text-slate-700 dark:text-slate-300 mt-0.5 truncate" :title="status.data_source">{{ status.data_source || '检测中…' }}</div>
            </div>
            <div class="p-2.5 rounded-md bg-white/50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/60">
              <div class="text-slate-400">数据在线</div>
              <div class="mt-0.5 flex items-center gap-1.5 text-body">
                <span class="w-2 h-2 rounded-full" :class="statusDot" />
                <span class="text-slate-700 dark:text-slate-300">{{ status.data_online ? '在线' : '离线' }}</span>
              </div>
            </div>
            <div class="p-2.5 rounded-md bg-white/50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/60">
              <div class="text-slate-400">LLM 模型</div>
              <div class="text-body mt-0.5" :class="status.llm_degraded ? 'text-amber-500' : 'text-slate-700 dark:text-slate-300'">
                {{ status.llm_degraded ? '降级中' : '正常' }}
              </div>
            </div>
            <div class="p-2.5 rounded-md bg-white/50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-700/60">
              <div class="text-slate-400">版本</div>
              <div class="text-body text-slate-700 dark:text-slate-300 mt-0.5 num">IRIS v0.1.0</div>
            </div>
          </div>
        </section>

        <!-- ============ 危险区 ============ -->
        <section class="card p-4 flex items-center justify-between">
          <div>
            <div class="text-body font-medium text-slate-800 dark:text-slate-200">重置会话</div>
            <p class="text-caption text-slate-400 mt-0.5">清除当前 thread_id，开启全新上下文（不影响长期记忆）</p>
          </div>
          <button
            @click="handleResetSession"
            class="shrink-0 px-3 py-1.5 rounded-md border border-red-200 dark:border-red-800 text-label text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            重置
          </button>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useAppStore } from '../stores/app';
import { useToast } from '../composables/useToast';
import {
  listMemories,
  deleteMemory,
  createMemory,
  updateMemory,
  getMemory,
  resetMemory,
  getThreadId,
} from '../services/api';

const appStore = useAppStore();
const toast = useToast();

const KIND_LABEL = { preference: "偏好", fact: "事实", watch_stock: "关注股票" };

// === 基础设置 ===
const apiBase = ref(localStorage.getItem('iris_api_base') || '');
const searchMode = ref(localStorage.getItem('iris_search_mode') || 'hybrid');

// 回答偏好（与 streamChat 读取的 iris_preferences 同 key）
let savedPrefs = {};
try { savedPrefs = JSON.parse(localStorage.getItem('iris_preferences') || '{}'); } catch { /* ignore */ }
const style = ref(savedPrefs.style || 'detailed');
const language = ref(savedPrefs.language || 'zh');

const handleSave = () => {
  localStorage.setItem('iris_api_base', apiBase.value.trim());
  localStorage.setItem('iris_search_mode', searchMode.value);
  localStorage.setItem('iris_preferences', JSON.stringify({ style: style.value, language: language.value }));
  appStore.setPreferences({
    apiBase: apiBase.value.trim(),
    searchMode: searchMode.value,
    style: style.value,
    language: language.value,
  });
  toast.success('设置已保存，刷新页面后生效');
};

// === 短期记忆（会话摘要） ===
const sessionSummary = ref('');
const sessionTurns = ref(0);

async function loadSessionMemory() {
  try {
    const data = await getMemory(getThreadId());
    sessionSummary.value = data.summary || '';
    sessionTurns.value = data.turns || 0;
  } catch {
    sessionSummary.value = '';
    sessionTurns.value = 0;
  }
}

async function handleResetSessionMemory() {
  if (!confirm('确定清空当前会话的记忆摘要吗？报告内容不受影响。')) return;
  try {
    await resetMemory(getThreadId());
    sessionSummary.value = '';
    sessionTurns.value = 0;
    toast.success('会话记忆已清空');
  } catch {
    toast.error('清空失败');
  }
}

// === 长期记忆管理 ===
const memories = ref([]);
const showAdd = ref(false);
const newKind = ref('preference');
const newContent = ref('');
const editing = ref({ key: '', kind: 'fact', content: '' });

async function loadMemories() {
  try {
    const data = await listMemories();
    memories.value = data.items || [];
  } catch {
    toast.error('记忆加载失败');
  }
}

async function handleAddMemory() {
  const content = newContent.value.trim();
  if (!content) {
    toast.error('请输入记忆内容');
    return;
  }
  try {
    await createMemory(newKind.value, content);
    newContent.value = '';
    showAdd.value = false;
    await loadMemories();
    toast.success('记忆已添加');
  } catch {
    toast.error('添加失败');
  }
}

function startEdit(m) {
  editing.value = { key: m.key, kind: m.kind, content: m.content };
}

async function handleEditMemory(key) {
  const content = editing.value.content.trim();
  if (!content) {
    toast.error('记忆内容不能为空');
    return;
  }
  try {
    await updateMemory(key, editing.value.kind, content);
    editing.value.key = '';
    await loadMemories();
    toast.success('记忆已更新');
  } catch {
    toast.error('更新失败');
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

// === 系统状态 ===
const status = ref({ data_source: '', data_online: false, llm_degraded: false });
const statusDot = computed(() => {
  if (!status.value.data_source) return "bg-slate-300";
  return status.value.data_online ? "bg-emerald-500" : "bg-amber-500";
});

// === 会话重置 ===
const handleResetSession = () => {
  appStore.resetSession();
  toast.success('会话已重置');
};

onMounted(async () => {
  loadMemories();
  loadSessionMemory();
  try {
    const res = await fetch('/api/status');
    if (res.ok) status.value = await res.json();
  } catch {
    // 后端不可用时静默
  }
});
</script>
