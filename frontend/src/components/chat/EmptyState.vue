<template>
  <div class="min-h-full flex items-center justify-center py-10 px-4">
    <div class="w-full max-w-2xl">
      <!-- 品牌区 -->
      <div class="text-center mb-8">
        <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-soft">
          <svg class="w-9 h-9 text-white" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3">
            <rect x="8" y="34" width="8" height="22" rx="2"/>
            <rect x="20" y="22" width="8" height="34" rx="2"/>
            <rect x="32" y="30" width="8" height="26" rx="2"/>
            <rect x="44" y="14" width="8" height="42" rx="2"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">今天想研究点什么？</h1>
        <p class="text-label text-slate-500 dark:text-slate-400 mt-2">输入股票代码或主题，IRIS 的多智能体团队将为你完成「检索 → 分析 → 撰写」全流程</p>
      </div>

      <!-- 功能卡片 -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
        <button
          v-for="p in presets"
          :key="p.title"
          @click="$emit('preset-click', p.prompt)"
          class="text-left p-4 rounded-card border border-white/60 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl hover:border-accent/60 hover:shadow-soft hover:-translate-y-0.5 transition-all duration-200 group"
        >
          <div class="flex items-start gap-3">
            <div class="w-9 h-9 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center text-accent shrink-0 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/20 transition-colors" v-html="p.icon"></div>
            <div class="min-w-0">
              <div class="text-body font-semibold text-slate-900 dark:text-slate-100 group-hover:text-accent transition-colors">{{ p.title }}</div>
              <div class="text-label text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">{{ p.desc }}</div>
            </div>
          </div>
        </button>
      </div>

      <!-- 热门标的 -->
      <div class="text-center">
        <div class="text-label text-slate-400 dark:text-slate-500 mb-2.5">
          热门标的<template v-if="hotSource"><span class="text-slate-300 dark:text-slate-600"> · {{ hotSource }}</span></template>
        </div>
        <div class="flex flex-wrap justify-center gap-2">
          <button
            v-for="s in hotStocks"
            :key="s.code"
            @click="$emit('hot-click', `分析${s.name}（${s.code}）的投资价值`)"
            class="px-3 py-1.5 rounded-full border border-white/60 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl text-label text-slate-600 dark:text-slate-300 hover:border-accent/60 hover:text-accent transition-colors"
          >
            {{ s.name }} · {{ s.code }}
          </button>
        </div>
      </div>

      <!-- 最近研究（有历史时） -->
      <div v-if="recentHistory.length" class="mt-8">
        <div class="text-label text-slate-400 dark:text-slate-500 mb-2.5 text-center">最近研究</div>
        <div class="space-y-1.5">
          <button
            v-for="h in recentHistory"
            :key="h.id"
            @click="$emit('replay', h)"
            class="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-100/70 dark:hover:bg-slate-800/60 transition-colors text-left"
          >
            <span class="text-body text-slate-700 dark:text-slate-300 truncate">{{ h.query || '未命名会话' }}</span>
            <span class="text-label text-slate-400 shrink-0 ml-3">{{ formatTime(h.timestamp) }}</span>
          </button>
        </div>
      </div>

      <p class="text-center text-label text-slate-400 dark:text-slate-500 mt-8">
        IRIS 由多个 AI 智能体协同工作 · 报告仅供参考，不构成投资建议
      </p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  presets: { type: Array, default: () => [] },
  hotStocks: { type: Array, default: () => [] },
  hotSource: { type: String, default: "" },
  recentHistory: { type: Array, default: () => [] },
});
defineEmits(["preset-click", "hot-click", "replay"]);

const formatTime = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  return d.toLocaleDateString();
};
</script>
