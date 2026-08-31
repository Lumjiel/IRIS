<template>
  <aside class="w-64 shrink-0 h-full flex flex-col border-r border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl">
    <!-- 新建会话 -->
    <div class="p-3">
      <button
        @click="$emit('new-thread')"
        class="w-full flex items-center gap-2 px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-body font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 hover:border-accent/40 transition-colors"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建会话
      </button>

      <!-- 自选股 -->
      <div class="mt-4">
        <div class="flex items-center justify-between px-2 mb-1.5">
          <span class="text-label text-slate-400 dark:text-slate-500">自选股</span>
          <button
            @click="addingWatch = !addingWatch"
            class="p-1 rounded text-slate-400 hover:text-accent transition-colors"
            title="添加自选股"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>

        <!-- 添加输入 -->
        <div v-if="addingWatch" class="mb-2 flex gap-1.5">
          <input
            v-model="watchInput"
            @keydown.enter="addWatch"
            placeholder="代码或 名称+代码"
            class="flex-1 min-w-0 px-2 py-1 rounded border border-slate-200/70 dark:border-slate-600/60 bg-white/60 dark:bg-slate-900/60 text-label text-slate-700 dark:text-slate-300 focus:outline-none focus:border-accent"
          />
          <button
            @click="addWatch"
            class="px-2 py-1 rounded bg-accent text-white text-label hover:bg-accent/90 transition-colors"
          >添加</button>
        </div>

        <div v-if="watchlist.list.length" class="space-y-0.5">
          <button
            v-for="s in watchlist.list"
            :key="s.code"
            @click="$emit('analyze', `${s.name}（${s.code}）的投资价值`)"
            class="group w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors text-left"
          >
            <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            <span class="flex-1 min-w-0">
              <span class="block text-body text-slate-700 dark:text-slate-300 truncate">{{ s.name }}</span>
              <span class="block text-label text-slate-400">{{ s.code }}</span>
            </span>
            <svg
              class="w-3.5 h-3.5 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              @click.stop="removeWatch(s.code)"
            ><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <p v-else class="px-2 text-label text-slate-400">暂无自选股</p>
      </div>
    </div>

    <!-- 会话历史 -->
    <div class="flex-1 overflow-y-auto px-3 pb-2">
      <div class="text-label text-slate-400 dark:text-slate-500 px-2 mb-1.5">会话历史</div>
      <div v-if="groupedHistory.length === 0" class="px-2 text-label text-slate-400">暂无历史</div>
      <div v-for="group in groupedHistory" :key="group.label" class="mb-3">
        <div class="text-label text-slate-400 dark:text-slate-500 px-2 mb-1">{{ group.label }}</div>
        <div class="space-y-0.5">
          <button
            v-for="h in group.items"
            :key="h.id"
            @click="$emit('replay', h)"
            class="group w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors text-left"
          >
            <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <span class="flex-1 min-w-0 text-body text-slate-600 dark:text-slate-400 truncate group-hover:text-slate-900 dark:group-hover:text-slate-200 transition-colors">{{ h.query || '未命名会话' }}</span>
            <svg
              class="w-3.5 h-3.5 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              @click.stop="$emit('delete-history', h)"
            ><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 底部：系统状态 + 入口 -->
    <div class="border-t border-slate-200 dark:border-slate-700 p-3 space-y-2">
      <!-- 数据源状态 -->
      <div class="px-1 flex items-center gap-2">
        <span class="w-2 h-2 rounded-full shrink-0" :class="statusDot" />
        <span class="text-label text-slate-500 dark:text-slate-400 truncate">{{ statusText }}</span>
        <span v-if="status.llm_degraded" class="text-label text-amber-500 shrink-0" title="LLM 主模型降级中">LLM 降级</span>
      </div>

      <div class="flex items-center gap-1">
        <router-link
          to="/market"
          class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-label text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>
          行情
        </router-link>
        <router-link
          to="/history"
          class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-label text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          历史
        </router-link>
        <router-link
          to="/settings"
          class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-label text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
        >
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
          设置
        </router-link>
        <button
          @click="appStore.toggleDark()"
          class="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-label text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
          :title="appStore.dark ? '切换浅色' : '切换深色'"
        >
          <svg v-if="appStore.dark" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          模式
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useWatchlist } from "../composables/useWatchlist";
import { useAppStore } from "../stores/app";
import { getStockName } from "../services/finance";

const props = defineProps({
  history: { type: Array, default: () => [] },
});
const emit = defineEmits(["analyze", "new-thread", "replay", "watch-added", "watch-removed", "delete-history"]);

const appStore = useAppStore();
const watchlist = useWatchlist();

// --- 添加自选股 ---
const addingWatch = ref(false);
const watchInput = ref("");

// 解析 "贵州茅台 600519" / "600519" / "贵州茅台(600519)"
function parseWatchInput(raw) {
  const codeMatch = raw.match(/(\d{6})/);
  if (!codeMatch) return null;
  const code = codeMatch[1];
  const name = raw
    .replace(/[\d()（）\s]/g, "")
    .replace(/[（(]\d{6}[)）]/g, "")
    .trim() || code;
  return { code, name };
}

async function addWatch() {
  const parsed = parseWatchInput(watchInput.value.trim());
  if (!parsed) return;
  // 只输代码时自动补全名称（失败保留代码显示）
  if (parsed.name === parsed.code) {
    parsed.name = await getStockName(parsed.code);
  }
  if (watchlist.add(parsed)) {
    emit("watch-added", parsed);
  }
  watchInput.value = "";
  addingWatch.value = false;
}

function removeWatch(code) {
  watchlist.remove(code);
  emit("watch-removed", code);
}

// --- 会话历史分组（今天 / 昨天 / 更早）---
const groupedHistory = computed(() => {
  const today = new Date().setHours(0, 0, 0, 0);
  const yesterday = today - 86400000;
  const groups = [
    { label: "今天", items: [] },
    { label: "昨天", items: [] },
    { label: "更早", items: [] },
  ];
  for (const item of [...props.history].sort((a, b) => b.timestamp - a.timestamp)) {
    const t = item.timestamp || 0;
    if (t >= today) groups[0].items.push(item);
    else if (t >= yesterday) groups[1].items.push(item);
    else groups[2].items.push(item);
  }
  return groups.filter((g) => g.items.length > 0);
});

// --- 系统状态 ---
const status = ref({ data_source: "", data_online: false, llm_degraded: false });
const statusDot = computed(() => {
  if (!status.value.data_source) return "bg-slate-300";
  return status.value.data_online ? "bg-emerald-500" : "bg-amber-500";
});
const statusText = computed(() => {
  if (!status.value.data_source) return "数据层检测中…";
  if (status.value.data_online) {
    const src = status.value.data_source.replace("AKShare", "").replace(/[()（）]/g, "").trim();
    return `数据源：AKShare${src ? " " + src : ""}`;
  }
  return "数据源：内置模拟数据";
});

onMounted(async () => {
  try {
    const res = await fetch("/api/status");
    if (res.ok) status.value = await res.json();
  } catch {
    // 后端不可用时静默
  }
});
</script>