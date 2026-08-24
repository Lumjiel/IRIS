<template>
  <div v-if="items.length" class="overflow-hidden bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg">
    <div class="flex items-center h-8">
      <span class="shrink-0 px-2.5 text-label text-amber-500 dark:text-amber-400 border-r border-slate-200 dark:border-slate-700 flex items-center gap-1">
        <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/></svg>
        热点
      </span>
      <div class="flex-1 overflow-hidden relative">
        <div class="ticker-track flex items-center gap-6 px-3 whitespace-nowrap">
          <a
            v-for="(item, i) in loopItems"
            :key="i"
            :href="item.url || '#'"
            :target="item.url ? '_blank' : null"
            :rel="item.url ? 'noopener' : null"
            class="text-caption text-slate-600 dark:text-slate-300 hover:text-accent transition-colors"
            :class="{ 'cursor-default': !item.url }"
            @click.prevent="item.url ? null : $event.preventDefault()"
          >
            {{ item.title || item.name || '热点资讯' }}
          </a>
        </div>
      </div>
      <button
        @click="paused = !paused"
        class="shrink-0 px-2 h-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 border-l border-slate-200 dark:border-slate-700 transition-colors"
        :title="paused ? '继续滚动' : '暂停'"
      >
        <svg v-if="paused" class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        <svg v-else class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
/**
 * NewsTicker — 输入框上方的热点新闻横滚条。
 * 复用已有的 fetchAihotNews() 代理端点（api.js 已封装）。
 * 自动滚动 + 悬停暂停 + 点击跳转原文。
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { fetchAihotNews } from "../services/api";

const items = ref([]);
const paused = ref(false);
let timer = null;

const loopItems = computed(() => [...items.value, ...items.value]);

async function load() {
  try {
    const data = await fetchAihotNews(12);
    const list = data?.items || data?.data || [];
    if (list.length) items.value = list.map((it) => ({
      title: it.title || it.name || it.headline || "",
      url: it.url || it.link || null,
    })).filter((it) => it.title);
  } catch {
    // 新闻非核心功能，静默降级
  }
}

onMounted(() => {
  load();
  timer = setInterval(load, 5 * 60 * 1000);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.ticker-track {
  animation: ticker 40s linear infinite;
  animation-play-state: running;
}
.ticker-track:hover,
.ticker-track:hover ~ * {
  animation-play-state: paused;
}
button:hover ~ .ticker-track {
  animation-play-state: running;
}
button:hover ~ .ticker-track,
.ticker-track:has(+ button:hover) {
  animation-play-state: paused;
}
@keyframes ticker {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
</style>
