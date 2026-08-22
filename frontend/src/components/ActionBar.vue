<template>
  <div class="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-6 py-3 flex items-center gap-3">
    <div class="text-label text-slate-500 flex-1 truncate">
      数据来源：<span v-if="sources.length" class="dark:text-slate-300">{{ sources.join('、') }}</span>
      <span v-else>—</span>
    </div>

    <button @click="$emit('copy')" class="btn-secondary flex items-center gap-1.5" :disabled="!report">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
      复制
    </button>

    <button @click="$emit('download')" class="btn-secondary flex items-center gap-1.5" :disabled="!report">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      下载
    </button>

    <button @click="$emit('save')" class="btn-secondary flex items-center gap-1.5" :disabled="!report">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
      保存
    </button>

    <button @click="$emit('toggleTheme')" class="btn-secondary" title="切换主题">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
    </button>
  </div>
</template>

<script setup>
defineProps({
  report: { type: String, default: '' },
  sources: { type: Array, default: () => [] },
});

defineEmits(['copy', 'download', 'save', 'toggleTheme']);
</script>

<style scoped>
.btn-secondary {
  @apply flex items-center gap-1.5 px-3 py-1.5 rounded-md text-label font-medium
         text-slate-600 hover:bg-slate-100 hover:text-slate-900
         dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200
         disabled:opacity-30 disabled:cursor-not-allowed
         transition-colors duration-200 border border-slate-200;
}
</style>