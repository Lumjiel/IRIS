<template>
  <div class="h-screen flex bg-gray-50 overflow-hidden">
    <ChatSidebar
      :sidebarOpen="sidebarOpen"
      :uploadedFiles="chat.uploadedFiles.value"
      :searchMode="chat.searchMode.value"
      :materials="materials"
      :history="chat.history.value"
      :activeHistoryId="chat.activeHistoryId.value"
      @newChat="chat.newChat"
      @fileSelect="(e) => chat.handleFileSelect(e, showToast)"
      @update:searchMode="(v) => chat.searchMode.value = v"
      @loadMaterials="loadMaterials"
      @viewMaterial="viewMaterial"
      @deleteMaterial="deleteMaterialItem"
      @viewHistory="chat.viewHistory"
    />

    <div class="flex-1 flex flex-col min-w-0">
      <ChatHeader
        :currentQuery="chat.currentQuery.value"
        :isLoading="chat.isLoading.value"
        @toggleSidebar="sidebarOpen = !sidebarOpen"
      />

      <ChatMessages
        :messages="chat.messages.value"
        :isLoading="chat.isLoading.value"
        :aiNews="aiNews"
        @loadAiNews="loadAiNews"
        @useAiNews="(title) => { chat.query.value = title; }"
        @copyReport="chat.copyReport"
        @downloadReport="chat.downloadReport"
        @saveToLibrary="(msg) => chat.saveToLibrary(msg, showToast)"
      />

      <ChatInput
        v-model="chat.query.value"
        :isLoading="chat.isLoading.value"
        @send="() => chat.sendMessage(showToast)"
        @stop="chat.stopResearch"
      />
    </div>

    <!-- Toast -->
    <Transition name="fade">
      <div v-if="toastMsg" class="fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-sm shadow-lg z-50" :class="toastType === 'error' ? 'bg-red-500 text-white' : 'bg-gray-800 text-white'">
        {{ toastMsg }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { fetchAihotNews, listMaterials, deleteMaterial, getMaterial } from './services/api';
import { getHistory } from './services/history';
import { getThreadId } from './services/api';
import { useChat } from './composables/useChat';
import ChatSidebar from './components/ChatSidebar.vue';
import ChatHeader from './components/ChatHeader.vue';
import ChatMessages from './components/ChatMessages.vue';
import ChatInput from './components/ChatInput.vue';

const chatContainer = ref(null);
const chat = useChat(chatContainer);

const sidebarOpen = ref(false);
const aiNews = ref([]);
const materials = ref([]);

// === Toast ===
const toastMsg = ref('');
const toastType = ref('success');
const showToast = (msg, type = 'success') => {
    toastMsg.value = msg;
    toastType.value = type;
    setTimeout(() => { toastMsg.value = ''; }, 3000);
};

// === AI 新闻 ===
const loadAiNews = async () => {
    try {
        const data = await fetchAihotNews(20);
        aiNews.value = data.items || [];
    } catch { aiNews.value = []; }
};

// === 素材库 ===
const loadMaterials = async () => {
    try {
        const data = await listMaterials();
        materials.value = data.items || [];
    } catch { materials.value = []; }
};

const viewMaterial = async (m) => {
    chat.messages.value = [];
    chat.currentQuery.value = m.filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '');
    chat.addMessage('user', 'text', `查看素材：${chat.currentQuery.value}`);
    try {
        const data = await getMaterial(m.filename);
        chat.addMessage('assistant', 'report', data.content);
    } catch {
        chat.addMessage('assistant', 'error', '读取素材失败');
    }
    chat.scrollToBottom();
};

const deleteMaterialItem = async (filename) => {
    try {
        await deleteMaterial(filename);
        materials.value = materials.value.filter(m => m.filename !== filename);
        showToast('已删除', 'success');
    } catch { showToast('删除失败', 'error'); }
};

// === 生命周期 ===
const handleKeydown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        chat.sendMessage(showToast);
    }
};

onMounted(() => {
    chat.history.value = getHistory();
    loadAiNews();

    const currentThreadId = getThreadId();
    const recentSession = chat.history.value.find(s => s.threadId === currentThreadId);
    if (recentSession) chat.viewHistory(recentSession);

    document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown);
});
</script>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
