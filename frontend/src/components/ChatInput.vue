<template>
  <div class="border-t border-gray-200 bg-white px-4 py-3 shrink-0">
    <div class="max-w-3xl mx-auto">
      <!-- 示例建议 -->
      <div v-if="!hasMessages" class="flex flex-wrap gap-2 mb-3">
        <span class="text-xs text-gray-400">💡 试试：</span>
        <button v-for="example in examples" :key="example"
          @click="$emit('update:modelValue', example)"
          class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600 hover:bg-blue-50 hover:text-blue-600 transition-colors">
          {{ example }}
        </button>
      </div>
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
      <!-- Skill 选择器 -->
      <div class="flex items-center gap-2 mb-2 px-1 min-h-[24px]">
        <span class="text-[10px] text-gray-400 shrink-0">🧩 Skill</span>
        <div v-if="activeSkill" class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200">
          <span class="text-[11px] font-medium text-indigo-600">{{ activeSkill }}</span>
          <button @click="$emit('clearSkill')" class="text-indigo-300 hover:text-indigo-600 text-[10px] leading-none">✕</button>
        </div>
        <button v-else @click="skillOpen = !skillOpen" class="px-2 py-0.5 rounded-full text-[10px] bg-gray-100 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 border border-transparent transition-colors">
          {{ skillOpen ? '收起' : '+ 指定' }}
        </button>
        <Transition name="fade">
          <div v-if="skillOpen" class="flex flex-wrap gap-1">
            <button v-for="s in skills" :key="s.name" @click="pickSkill(s.name)"
              class="px-2 py-0.5 rounded-full text-[10px] bg-white border border-gray-200 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors">
              {{ s.name }}
            </button>
          </div>
        </Transition>
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
import { ref, watch, nextTick } from 'vue';

defineProps({
    modelValue: { type: String, default: '' },
    isLoading: Boolean,
    uploadedFiles: { type: Array, default: () => [] },
    searchMode: { type: String, default: 'hybrid' },
    hasMessages: Boolean,
    skills: { type: Array, default: () => [] },
    activeSkill: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue', 'update:searchMode', 'send', 'stop', 'selectSkill', 'clearSkill']);

const inputBox = ref(null);
const skillOpen = ref(false);
const pickSkill = (name) => {
    emit('selectSkill', name);
    skillOpen.value = false;
};

const examples = [
    '公众号如何写爆款文章',
    'React vs Vue 技术选型',
    '2026年AI行业趋势分析',
    '数据库选型：PostgreSQL vs MySQL',
];

const autoResize = (e) => {
    const el = (e && e.target) || inputBox.value;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};

// 外部赋值（如点击灵感建议）时自动调高
watch(() => inputBox.value, (el) => {
    if (el) nextTick(() => autoResize({ target: el }));
});
</script>
