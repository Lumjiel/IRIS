<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 transition-transform duration-300" :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 fixed lg:relative z-30 h-full'">
    <div class="px-5 py-4 border-b border-gray-100">
      <h1 class="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">IRIS</h1>
      <p class="text-[10px] text-gray-400 mt-0.5">智能调研系统</p>
    </div>

    <div class="px-3 pt-3">
      <button @click="$emit('newChat')" class="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        新建调研
      </button>
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
        <div v-if="uploadedFiles.length > 0" class="flex items-center gap-1 px-2 py-1.5">
          <button @click="$emit('update:searchMode', 'hybrid')" class="flex-1 text-center text-[11px] rounded-lg py-1 transition-colors" :class="searchMode === 'hybrid' ? 'bg-purple-100 text-purple-700 font-bold' : 'bg-gray-100 text-gray-400 hover:text-gray-600'">混合模式</button>
          <button @click="$emit('update:searchMode', 'document')" class="flex-1 text-center text-[11px] rounded-lg py-1 transition-colors" :class="searchMode === 'document' ? 'bg-blue-100 text-blue-700 font-bold' : 'bg-gray-100 text-gray-400 hover:text-gray-600'">仅文档</button>
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
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue';

defineProps({
    sidebarOpen: Boolean,
    uploadedFiles: { type: Array, default: () => [] },
    searchMode: { type: String, default: 'hybrid' },
    materials: { type: Array, default: () => [] },
    history: { type: Array, default: () => [] },
    activeHistoryId: { type: [String, Number, null], default: null },
});

defineEmits(['newChat', 'fileSelect', 'update:searchMode', 'loadMaterials', 'viewMaterial', 'deleteMaterial', 'viewHistory']);

const activeTab = ref('kb');
const tabs = [
    { key: 'kb', label: '知识库' },
    { key: 'materials', label: '素材库' },
    { key: 'history', label: '历史' },
];

const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
};

const formatTime = (ts) => {
    const d = new Date(ts);
    const diff = Date.now() - ts;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
};
</script>
