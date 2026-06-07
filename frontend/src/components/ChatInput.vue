<template>
  <div class="border-t border-gray-200 bg-white px-4 py-3 shrink-0">
    <div class="max-w-3xl mx-auto">
      <!-- 文件信息 + 搜索模式 -->
      <div v-if="uploadedFiles.length > 0" class="flex items-center gap-2 mb-2 px-1">
        <div class="flex items-center gap-1.5 text-[11px] text-gray-500">
          <svg class="w-3.5 h-3.5 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>{{ uploadedFiles.length }} 个文档</span>
        </div>
        <div class="flex items-center gap-1 ml-auto">
          <button @click="$emit('update:searchMode', 'hybrid')" class="px-2.5 py-0.5 rounded-full text-[10px] font-medium transition-colors" :class="searchMode === 'hybrid' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-400 hover:text-gray-600'">混合</button>
          <button @click="$emit('update:searchMode', 'document')" class="px-2.5 py-0.5 rounded-full text-[10px] font-medium transition-colors" :class="searchMode === 'document' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-400 hover:text-gray-600'">仅文档</button>
        </div>
      </div>
      <!-- 输入框 -->
      <div class="flex items-end gap-2 bg-gray-50 rounded-2xl border border-gray-200 focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100 transition-all px-4 py-2">
        <textarea
          ref="inputBox"
          :value="modelValue"
          @input="$emit('update:modelValue', $event.target.value); autoResize($event)"
          @keydown.enter.exact.prevent="$emit('send')"
          class="flex-1 bg-transparent resize-none text-sm text-gray-700 placeholder-gray-400 focus:outline-none leading-relaxed"
          :rows="1"
          :placeholder="isLoading ? '调研中...' : '输入研究主题...'"
          :disabled="isLoading"
        ></textarea>
        <button
          v-if="isLoading"
          @click="$emit('stop')"
          class="shrink-0 w-9 h-9 rounded-xl bg-red-500 hover:bg-red-600 text-white flex items-center justify-center transition-colors shadow-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button>
        <button
          v-else
          @click="$emit('send')"
          :disabled="!modelValue.trim()"
          class="shrink-0 w-9 h-9 rounded-xl bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
      <p class="text-[10px] text-gray-300 text-center mt-1.5">IRIS 可能会犯错，请核实重要信息</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
    modelValue: { type: String, default: '' },
    isLoading: Boolean,
    uploadedFiles: { type: Array, default: () => [] },
    searchMode: { type: String, default: 'hybrid' },
});

defineEmits(['update:modelValue', 'update:searchMode', 'send', 'stop']);

const autoResize = (e) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};
</script>
