<template>
  <div ref="chatContainer" class="flex-1 overflow-y-auto">
    <!-- 空状态 -->
    <div v-if="messages.length === 0 && !isLoading" class="h-full flex flex-col items-center justify-center px-4">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20 mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
      </div>
      <h2 class="text-lg font-semibold text-gray-800 mb-1">有什么想调研的？</h2>
      <p class="text-sm text-gray-400 mb-6">输入主题开始深度调研，或试试下方灵感</p>

      <!-- 推文灵感 -->
      <div class="w-full max-w-xl">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-lg bg-gradient-to-br from-orange-400 to-pink-500 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            </div>
            <span class="text-sm font-semibold text-gray-700">推文灵感</span>
          </div>
          <button @click="$emit('loadAiNews')" class="text-[11px] text-gray-400 hover:text-blue-500 transition-colors">换一批</button>
        </div>
        <div class="flex gap-1.5 mb-3 flex-wrap">
          <button v-for="cat in aiNewsCategories" :key="cat.key" @click="aiNewsCategory = cat.key" class="px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-200" :class="aiNewsCategory === cat.key ? 'bg-gray-900 text-white shadow-md' : 'bg-white text-gray-500 hover:bg-gray-100 border border-gray-200'">
            {{ cat.label }}
          </button>
        </div>
        <div class="space-y-2 h-64 overflow-y-auto pr-1 scrollbar-none">
          <div v-for="item in filteredAiNews" :key="item.id" @click="$emit('useAiNews', item.title)" class="group p-3.5 bg-white rounded-xl border border-gray-100 cursor-pointer hover:border-blue-200 hover:shadow-md hover:shadow-blue-50 transition-all duration-300">
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <p class="text-[13px] font-medium text-gray-800 leading-snug line-clamp-2 group-hover:text-blue-600 transition-colors">{{ item.title }}</p>
                <div class="flex items-center gap-2 mt-2">
                  <span v-if="item.category" class="text-[10px] font-medium px-2 py-0.5 rounded-full" :class="{'bg-blue-50 text-blue-600':item.category==='ai-models','bg-emerald-50 text-emerald-600':item.category==='ai-products','bg-amber-50 text-amber-600':item.category==='industry','bg-purple-50 text-purple-600':item.category==='paper','bg-cyan-50 text-cyan-600':item.category==='tip'}">{{ catLabel(item.category) }}</span>
                  <span class="text-[10px] text-gray-400">{{ item.source }}</span>
                </div>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-gray-300 group-hover:text-blue-400 shrink-0 mt-1 transition-all duration-200 group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div v-else class="max-w-3xl mx-auto py-6 px-4 space-y-4">
      <div v-for="msg in messages" :key="msg.id" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
        <div v-if="msg.role !== 'user'" class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0 shadow-sm mt-1">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
        </div>

        <div class="max-w-[85%] min-w-0" :class="msg.role === 'user' ? 'order-1' : ''">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md text-sm shadow-sm">
            {{ msg.content }}
          </div>

          <!-- 流式消息 -->
          <div v-else-if="msg.type === 'stream'" class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
            <div v-if="msg.statuses && msg.statuses.length" class="px-4 pt-3 pb-1 space-y-1.5">
              <div v-for="(s, i) in msg.statuses" :key="i">
                <div class="flex items-center gap-2 text-[11px]">
                  <span class="w-4 h-4 rounded-full flex items-center justify-center shrink-0" :class="s.active ? 'bg-blue-100' : 'bg-green-50'">
                    <span v-if="s.active" class="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                    <span v-else class="text-green-500 text-[9px]">✓</span>
                  </span>
                  <span :class="s.active ? 'text-blue-600 font-medium' : 'text-gray-400'">{{ s.text }}</span>
                </div>
                <div v-if="s.items && s.items.length" class="ml-6 mt-0.5 space-y-0.5">
                  <div v-for="(item, j) in s.items" :key="j" class="text-[10px] text-gray-400 leading-relaxed">→ {{ item }}</div>
                </div>
                <div v-if="s.detail" class="ml-6 mt-0.5 text-[10px] text-gray-400 leading-relaxed">{{ s.detail }}</div>
              </div>
            </div>
            <div v-if="msg.streamText" class="px-4 pb-3 pt-1">
              <div class="text-[13px] text-gray-700 leading-relaxed whitespace-pre-line border-l-2 border-blue-200 pl-3">{{ msg.streamText }}</div>
            </div>
            <div v-if="msg.active" class="px-4 pb-3">
              <span class="inline-block w-0.5 h-4 bg-blue-500 animate-pulse align-middle"></span>
            </div>
          </div>

          <!-- 报告消息 -->
          <div v-else-if="msg.type === 'report'" class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
            <div class="px-4 py-2.5 border-b border-gray-50 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-5 h-5 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                </span>
                <span class="text-xs font-bold text-gray-700">研究报告</span>
              </div>
              <div class="flex items-center gap-1">
                <button @click="$emit('copyReport', msg)" class="text-[10px] text-gray-400 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors">📋 复制</button>
                <button @click="$emit('downloadReport', msg)" class="text-[10px] text-gray-400 hover:text-purple-500 px-2 py-1 rounded-lg hover:bg-purple-50 transition-colors">⬇️ 下载</button>
                <button @click="$emit('saveToLibrary', msg)" class="text-[10px] text-white bg-gradient-to-r from-blue-500 to-purple-500 px-2.5 py-1 rounded-full hover:shadow-md transition-all">💾 保存素材库</button>
              </div>
            </div>
            <div class="prose prose-sm max-w-none p-5 leading-relaxed" v-html="renderMarkdown(msg.content)"></div>
          </div>

          <!-- 错误消息 -->
          <div v-else-if="msg.type === 'error'" class="bg-red-50 border border-red-100 rounded-2xl px-4 py-3 shadow-sm">
            <div class="flex items-center gap-2">
              <span class="text-sm">⚠️</span>
              <span class="text-xs text-red-600">{{ msg.content }}</span>
            </div>
          </div>

          <!-- 其他 -->
          <div v-else class="bg-white border border-gray-100 rounded-2xl px-4 py-3 shadow-sm">
            <div class="text-sm text-gray-700 prose prose-sm max-w-none" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { renderMarkdown } from '../utils/markdown';

const props = defineProps({
    messages: { type: Array, default: () => [] },
    isLoading: Boolean,
    aiNews: { type: Array, default: () => [] },
});

defineEmits(['loadAiNews', 'useAiNews', 'copyReport', 'downloadReport', 'saveToLibrary']);

const aiNewsCategory = ref('');

const aiNewsCategories = [
    { key: '', label: '全部' },
    { key: 'ai-models', label: '模型' },
    { key: 'ai-products', label: '产品' },
    { key: 'industry', label: '行业' },
    { key: 'paper', label: '论文' },
    { key: 'tip', label: '技巧' },
];

const filteredAiNews = computed(() => {
    const items = aiNewsCategory.value ? props.aiNews.filter(i => i.category === aiNewsCategory.value) : props.aiNews;
    return items.slice(0, 8);
});

const catLabel = (cat) => {
    const m = { 'ai-models': '模型', 'ai-products': '产品', 'industry': '行业', 'paper': '论文', 'tip': '技巧' };
    return m[cat] || '';
};
</script>
