<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 transition-transform duration-300" :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 fixed lg:relative z-30 h-full'">
    <div class="px-5 py-4 border-b border-gray-100">
      <h1 class="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">IRIS</h1>
      <p class="text-[10px] text-gray-400 mt-0.5">智能调研系统</p>
    </div>

    <div class="px-3 pt-3">
      <button @click="$emit('newChat')" class="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 text-sm text-white font-medium hover:opacity-90 transition-opacity shadow-sm">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建调研
      </button>
    </div>

    <!-- 历史对话 -->
    <div class="flex-1 overflow-y-auto px-3 py-3">
      <div v-if="history.length === 0" class="text-center text-[11px] text-gray-300 py-10">
        暂无历史对话<br><span class="text-[10px]">点击上方「新建调研」开始</span>
      </div>
      <div v-else class="space-y-1.5">
        <div v-for="s in history" :key="s.id" @click="$emit('viewHistory', s)"
          class="group px-3 py-2.5 rounded-xl border transition-all cursor-pointer"
          :class="activeHistoryId === s.id ? 'bg-blue-50 border-blue-100' : 'border-transparent hover:bg-gray-50 hover:border-gray-100'">
          <p class="text-[12px] font-medium truncate" :class="activeHistoryId === s.id ? 'text-blue-700' : 'text-gray-700'">{{ s.query }}</p>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-[10px] text-gray-400">{{ formatTime(s.timestamp) }}</span>
            <span v-if="s.messages" class="text-[9px] px-1.5 py-px rounded-full bg-gray-100 text-gray-400">{{ s.messages.filter(m => m.type === 'report').length }} 报告</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：账号管理 + 会话统计 -->
    <div class="border-t border-gray-200 mt-auto">
      <button @click="$emit('openAccount')" class="w-full px-4 py-2.5 flex items-center gap-2 text-[12px] text-gray-600 hover:bg-gray-50 transition-colors">
        <span class="w-7 h-7 rounded-full bg-gradient-to-br from-gray-500 to-gray-700 flex items-center justify-center text-white text-[11px] font-bold">IR</span>
        <span class="font-medium">账号管理</span>
        <svg class="w-4 h-4 ml-auto text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <div class="px-4 pb-3">
        <div class="text-[10px] text-gray-400 mb-1.5">📊 会话统计</div>
        <div class="grid grid-cols-2 gap-y-1 text-[11px]">
          <span class="text-gray-500">调研次数</span><span class="text-gray-700 font-medium">{{ stats.researchCount }}</span>
          <span class="text-gray-500">生成报告</span><span class="text-gray-700 font-medium">{{ stats.reportCount }}</span>
          <span class="text-gray-500">平均耗时</span><span class="text-gray-700 font-medium">{{ avgTime }}分钟</span>
          <span class="text-gray-500">引用来源</span><span class="text-gray-700 font-medium">{{ stats.sourceCount }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';

defineProps({
    sidebarOpen: Boolean,
    history: { type: Array, default: () => [] },
    activeHistoryId: { type: [String, Number, null], default: null },
    stats: { type: Object, default: () => ({ researchCount: 0, reportCount: 0, totalTime: 0, sourceCount: 0 }) },
    avgTime: { type: Number, default: 0 },
});

defineEmits(['newChat', 'viewHistory', 'openAccount']);

const formatTime = (ts) => {
    const d = new Date(ts); const diff = Date.now() - ts;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
};
</script>