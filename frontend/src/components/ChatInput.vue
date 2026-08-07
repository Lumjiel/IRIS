<template>
  <div class="border-t border-gray-200 bg-white px-4 py-3 shrink-0">
    <div class="max-w-3xl mx-auto">
      <!-- 工具栏：上传文档 + 工具 + 搜索模式 -->
      <div class="flex items-center gap-2 mb-2 px-1">
        <button @click="$refs.fileInput.click()" class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          上传文档
        </button>
        <input ref="fileInput" type="file" multiple accept=".pdf" class="hidden" @change="(e) => $emit('fileSelect', e)" />

        <button @click="toolOpen = !toolOpen" class="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
          工具
        </button>
        <div class="ml-auto flex items-center gap-1">
          <button @click="$emit('update:searchMode', 'hybrid')" class="px-2.5 py-0.5 rounded-full text-[10px] font-medium transition-colors" :class="searchMode === 'hybrid' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-400 hover:text-gray-600'">混合</button>
          <button @click="$emit('update:searchMode', 'document')" class="px-2.5 py-0.5 rounded-full text-[10px] font-medium transition-colors" :class="searchMode === 'document' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-400 hover:text-gray-600'">仅文档</button>
        </div>
      </div>

      <!-- 工具下拉 -->
      <Transition name="fade">
        <div v-if="toolOpen" class="mb-2 px-1">
          <div class="flex flex-wrap gap-1.5">
            <button v-for="t in tools" :key="t.name" @click="pickTool(t)" class="px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors" :class="activeTool === t.name ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'">{{ t.name }}</button>
          </div>
          <div v-if="activeTool" class="mt-2 flex gap-1.5">
            <input v-model="toolQuery" @keyup.enter="runTool" type="text" :placeholder="`输入 ${activeTool} 的查询...`" class="flex-1 px-2.5 py-1.5 text-[11px] border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400" />
            <button @click="runTool" :disabled="runningTool" class="px-3 py-1.5 text-[11px] text-white rounded-lg" :class="runningTool ? 'bg-gray-300' : 'bg-blue-500 hover:bg-blue-600'">{{ runningTool ? '执行中...' : '执行' }}</button>
          </div>
          <div v-if="toolResult" class="mt-1.5 px-2.5 py-2 text-[11px] text-gray-600 bg-gray-50 rounded-lg border border-gray-100 max-h-40 overflow-y-auto whitespace-pre-wrap">{{ toolResult }}</div>
        </div>
      </Transition>

      <!-- 已选文件 -->
      <div v-if="uploadedFiles.length > 0" class="flex items-center gap-1.5 mb-2 px-1">
        <span class="text-[11px] text-gray-500">📄 {{ uploadedFiles.length }} 个文档：</span>
        <span v-for="(f, i) in uploadedFiles" :key="i" class="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-500">{{ f.name }}</span>
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
import { ref, watch, nextTick, onMounted } from 'vue';
import { listTools, executeTool } from '../services/api';

defineProps({
    modelValue: { type: String, default: '' },
    isLoading: Boolean,
    uploadedFiles: { type: Array, default: () => [] },
    searchMode: { type: String, default: 'hybrid' },
    hasMessages: Boolean,
    skills: { type: Array, default: () => [] },
    activeSkill: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue', 'update:searchMode', 'send', 'stop', 'fileSelect', 'selectSkill', 'clearSkill']);

const inputBox = ref(null);
const tools = ref([]);
const toolOpen = ref(false);
const activeTool = ref('');
const toolQuery = ref('');
const runningTool = ref(false);
const toolResult = ref('');

const loadTools = async () => {
    try { const d = await listTools(); tools.value = d.tools || []; } catch { tools.value = []; }
};
const pickTool = (t) => { activeTool.value = t.name; toolResult.value = ''; };
const runTool = async () => {
    if (!activeTool.value || !toolQuery.value.trim() || runningTool.value) return;
    runningTool.value = true; toolResult.value = '';
    try {
        const d = await executeTool(activeTool.value, toolQuery.value.trim());
        toolResult.value = d.result || JSON.stringify(d, null, 2);
    } catch (e) { toolResult.value = '执行失败: ' + (e.message || ''); }
    runningTool.value = false;
};

onMounted(loadTools);

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

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>