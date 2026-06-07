<template>
  <header class="h-12 border-b border-gray-200 bg-white/80 backdrop-blur flex items-center px-4 gap-3 shrink-0">
    <button @click="$emit('toggleSidebar')" class="lg:hidden p-1 text-gray-400 hover:text-gray-600">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-gray-700 truncate">{{ currentQuery || 'IRIS 智能调研' }}</p>
    </div>

    <!-- 记忆状态指示器 -->
    <div v-if="memoryTurns > 0" class="relative" ref="memoryRoot">
      <button
        @click="memoryExpanded = !memoryExpanded"
        class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all"
        :class="memoryExpanded ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'"
      >
        <span>🧠</span>
        <span>{{ memoryTurns }} 轮上下文</span>
        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 transition-transform" :class="memoryExpanded ? 'rotate-180' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
      </button>

      <!-- 展开面板 -->
      <Transition name="fade">
        <div v-if="memoryExpanded" class="absolute right-0 top-full mt-1 w-80 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
          <div class="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
            <span class="text-[11px] font-semibold text-gray-600">对话记忆</span>
            <button @click.stop="$emit('resetMemory')" class="text-[10px] text-gray-400 hover:text-red-500 transition-colors">清空记忆</button>
          </div>
          <!-- 摘要长度指示条 -->
          <div class="px-3 pt-2">
            <div class="flex items-center justify-between mb-1">
              <span class="text-[10px] text-gray-400">摘要容量</span>
              <span class="text-[10px]" :class="summaryRatio > 0.8 ? 'text-amber-500' : 'text-gray-400'">{{ summaryLength }}/{{ summaryMax }}</span>
            </div>
            <div class="h-1 bg-gray-100 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all duration-300" :class="summaryRatio > 0.9 ? 'bg-red-400' : summaryRatio > 0.7 ? 'bg-amber-400' : 'bg-blue-400'" :style="{ width: Math.min(summaryRatio * 100, 100) + '%' }"></div>
            </div>
            <p v-if="summaryRatio > 0.8" class="text-[9px] text-amber-500 mt-1">接近压缩阈值，旧内容将被摘要压缩</p>
          </div>
          <div class="px-3 py-2 max-h-48 overflow-y-auto">
            <p class="text-[11px] text-gray-500 leading-relaxed whitespace-pre-line">{{ memorySummary || '暂无记忆' }}</p>
          </div>
        </div>
      </Transition>
    </div>

    <div v-if="isLoading" class="flex items-center gap-1.5 text-[11px] text-blue-500">
      <div class="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
      调研中...
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
    currentQuery: { type: String, default: '' },
    isLoading: Boolean,
    memoryTurns: { type: Number, default: 0 },
    memorySummary: { type: String, default: '' },
    summaryLength: { type: Number, default: 0 },
    summaryMax: { type: Number, default: 2000 },
});

defineEmits(['toggleSidebar', 'resetMemory']);

const summaryRatio = computed(() => props.summaryMax > 0 ? props.summaryLength / props.summaryMax : 0);

const memoryExpanded = ref(false);
const memoryRoot = ref(null);

// 点击外部关闭展开面板
const handleClickOutside = (e) => {
    if (memoryRoot.value && !memoryRoot.value.contains(e.target)) {
        memoryExpanded.value = false;
    }
};
onMounted(() => document.addEventListener('click', handleClickOutside));
onUnmounted(() => document.removeEventListener('click', handleClickOutside));
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
