<template>
  <div class="border-t border-gray-200 bg-white px-4 py-3 shrink-0">
    <div class="max-w-3xl mx-auto">
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
});

defineEmits(['update:modelValue', 'send', 'stop']);

const autoResize = (e) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};
</script>
