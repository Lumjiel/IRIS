<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 transition-transform duration-300" :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 fixed lg:relative z-30 h-full'">
    <div class="px-5 py-4 border-b border-gray-100">
      <h1 class="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">IRIS</h1>
      <p class="text-[10px] text-gray-400 mt-0.5">智能调研系统</p>
    </div>

    <div class="px-3 pt-3 flex gap-2">
      <button @click="$emit('newChat')" class="flex-1 flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建调研
      </button>
      <button v-if="memoryTurns > 0" @click="$emit('clearMemory')" class="shrink-0 px-2.5 py-2.5 rounded-xl border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-colors" title="清空对话记忆">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
      </button>
    </div>

    <!-- 记忆状态（有上下文时显示） -->
    <div v-if="memoryTurns > 0" class="mx-3 mt-2 px-3 py-1.5 bg-blue-50 rounded-lg flex items-center gap-1.5">
      <span class="text-[10px]">🧠</span>
      <span class="text-[10px] text-blue-600 font-medium">{{ memoryTurns }} 轮调研上下文</span>
    </div>

    <div class="flex border-b border-gray-100 mt-2 mx-3">
      <button v-for="tab in tabs" :key="tab.key" @click="activeTab = tab.key; if(tab.key==='materials') $emit('loadMaterials')" class="flex-1 py-2 text-[11px] font-bold transition-colors relative" :class="activeTab === tab.key ? 'text-blue-600' : 'text-gray-400'">
        {{ tab.label }}
        <div v-if="activeTab === tab.key" class="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-blue-500 rounded-full"></div>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-3 py-2 space-y-1">
      <!-- 知识库 -->
      <template v-if="activeTab === 'kb'">
        <div class="border-2 border-dashed rounded-xl p-3 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-all" :class="uploadedFiles.length > 0 ? 'border-green-300 bg-green-50/30' : 'border-gray-200'" @click="$refs.fileInput.click()">
          <input ref="fileInput" type="file" multiple accept=".pdf" class="hidden" @change="(e) => $emit('fileSelect', e)" />
          <div v-if="uploadedFiles.length === 0">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 mx-auto text-gray-300 mb-1" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <p class="text-[11px] text-gray-400">上传 PDF 文档</p>
          </div>
          <div v-else class="space-y-1">
            <div v-for="(f, i) in uploadedFiles" :key="i" class="flex items-center gap-2 text-[11px] text-gray-600">
              <svg class="w-3 h-3 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              <span class="truncate">{{ f.name }}</span>
            </div>
          </div>
        </div>
      </template>

      <!-- 素材库 -->
      <template v-if="activeTab === 'materials'">
        <div v-if="materials.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无素材<br><span class="text-[10px]">调研完成后点击「💾 保存素材库」</span></div>
        <div v-for="m in materials" :key="m.filename" class="group px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer" @click="$emit('viewMaterial', m)">
          <div class="flex items-center justify-between">
            <p class="text-[11px] font-medium text-gray-700 truncate flex-1">{{ m.filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '') }}</p>
            <button @click.stop="$emit('deleteMaterial', m.filename)" class="text-[10px] text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all px-1">✕</button>
          </div>
          <p class="text-[10px] text-gray-400 mt-0.5">{{ m.filename.split('-').slice(0, 3).join('-') }} · {{ formatSize(m.size) }}</p>
        </div>
      </template>

      <!-- 历史 -->
      <template v-if="activeTab === 'history'">
        <div v-if="history.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无历史</div>
        <div v-for="s in history" :key="s.id" @click="$emit('viewHistory', s)" class="px-3 py-2 rounded-lg cursor-pointer transition-colors text-[11px]" :class="activeHistoryId === s.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-600'">
          <p class="truncate font-medium">{{ s.query }}</p>
          <p class="text-[10px] text-gray-400 mt-0.5">{{ formatTime(s.timestamp) }}</p>
        </div>
      </template>

      <!-- 设置 -->
      <template v-if="activeTab === 'settings'">
        <div class="space-y-3 py-1">
          <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold">写作风格</p>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="s in styleOptions" :key="s.value" @click="updatePref('style', s.value)" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.style === s.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">{{ s.label }}</button>
          </div>

          <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold mt-3">报告语言</p>
          <div class="flex gap-1.5">
            <button v-for="l in langOptions" :key="l.value" @click="updatePref('language', l.value)" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.language === l.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">{{ l.label }}</button>
          </div>

          <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold mt-3">默认搜索模式</p>
          <div class="flex gap-1.5">
            <button @click="updatePref('searchMode', 'hybrid')" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.searchMode === 'hybrid' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">混合模式</button>
            <button @click="updatePref('searchMode', 'document')" class="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors" :class="preferences.searchMode === 'document' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500 hover:text-gray-700'">仅文档</button>
          </div>

          <div class="mt-4 pt-3 border-t border-gray-100">
            <p class="text-[10px] text-gray-400 uppercase tracking-wider font-bold">记忆管理</p>
            <p class="text-[10px] text-gray-400 mt-1">对话摘要会自动保存，用于多轮对话上下文理解。</p>
            <button @click="$emit('clearMemory')" class="mt-2 w-full text-[10px] text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg py-1.5 transition-colors">清除对话记忆</button>
          </div>
        </div>
      </template>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue';

defineProps({
    sidebarOpen: Boolean,
    uploadedFiles: { type: Array, default: () => [] },
    materials: { type: Array, default: () => [] },
    history: { type: Array, default: () => [] },
    activeHistoryId: { type: [String, Number, null], default: null },
    memoryTurns: { type: Number, default: 0 },
});

defineEmits(['newChat', 'fileSelect', 'loadMaterials', 'viewMaterial', 'deleteMaterial', 'viewHistory', 'clearMemory', 'updatePreference']);

const activeTab = ref('kb');
const tabs = [
    { key: 'kb', label: '知识库' },
    { key: 'materials', label: '素材库' },
    { key: 'history', label: '历史' },
    { key: 'settings', label: '设置' },
];

// === 用户偏好 ===
const STORAGE_KEY = 'iris_preferences';
const preferences = ref(JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'));
if (!preferences.value.style) preferences.value.style = 'detailed';
if (!preferences.value.language) preferences.value.language = 'zh';
if (!preferences.value.searchMode) preferences.value.searchMode = 'hybrid';

const styleOptions = [
    { value: 'detailed', label: '详细' },
    { value: 'concise', label: '简洁' },
    { value: 'formal', label: '正式' },
    { value: 'casual', label: '通俗' },
];
const langOptions = [
    { value: 'zh', label: '中文' },
    { value: 'en', label: 'English' },
];

const updatePref = (key, value) => {
    preferences.value[key] = value;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences.value));
};

const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
};

const formatTime = (ts) => {
    const d = new Date(ts);
    const diff = Date.now() - ts;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
};
</script>
