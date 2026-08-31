<template>
  <div class="px-4 py-3 border-t border-slate-200/70 dark:border-slate-700/60 bg-white/40 dark:bg-slate-800/40 backdrop-blur-lg rounded-b-2xl">
    <div class="flex items-end gap-2 bg-white/60 dark:bg-slate-900/60 backdrop-blur-lg rounded-lg border border-slate-200/70 dark:border-slate-700/60 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-colors duration-200 px-4 py-2">
      <textarea
        ref="inputBox"
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value); autoResize($event)"
        @keydown.enter.exact.prevent="$emit('send')"
        class="flex-1 bg-transparent resize-none text-body text-slate-700 placeholder-slate-400 focus:outline-none leading-relaxed"
        :rows="1"
        placeholder="基于本报告继续追问..."
      />
      <button
        @click="$emit('send')"
        :disabled="!modelValue.trim()"
        class="shrink-0 w-9 h-9 rounded-md bg-accent hover:bg-accent/90 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';

defineProps({
  modelValue: { type: String, default: '' },
});

defineEmits(['update:modelValue', 'send']);

const inputBox = ref(null);

const autoResize = (e) => {
  const el = (e && e.target) || inputBox.value;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};

watch(() => inputBox.value, (el) => {
  if (el) nextTick(() => autoResize({ target: el }));
});
</script>