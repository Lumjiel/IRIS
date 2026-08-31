<template>
  <header class="h-12 border-b border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl px-4 flex items-center justify-between gap-3 shrink-0">
    <div class="flex items-center gap-3 min-w-0">
      <!-- 移动端：打开抽屉侧栏 -->
      <button
        class="lg:hidden p-1.5 -ml-1.5 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        aria-label="打开侧栏"
        @click="$emit('open-drawer')"
      >
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-soft shrink-0">IR</div>
      <span class="text-sm font-semibold text-slate-900 dark:text-slate-100 shrink-0">IRIS 投研助手</span>
      <span class="text-label text-slate-400 dark:text-slate-500 hidden lg:inline truncate">LangGraph 多智能体协同 · AKShare 真实数据</span>
    </div>
  </header>
</template>

<script setup>
defineEmits(["open-drawer"]);
</script>
