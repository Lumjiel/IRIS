<template>
  <header class="h-12 border-b border-gray-200 bg-white/80 backdrop-blur flex items-center px-4 gap-3 shrink-0">
    <button @click="$emit('toggleSidebar')" class="lg:hidden p-1 text-gray-400 hover:text-gray-600">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-gray-700 truncate">{{ currentQuery || 'IRIS 智能调研' }}</p>
    </div>
    <div v-if="isLoading" class="flex items-center gap-1.5 text-[11px] text-blue-500">
      <div class="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
      调研中...
    </div>
  </header>
</template>

<script setup>
defineProps({
    currentQuery: { type: String, default: '' },
    isLoading: Boolean,
});

defineEmits(['toggleSidebar']);
</script>
