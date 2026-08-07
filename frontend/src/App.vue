<template>
  <div class="h-screen flex bg-gray-50 overflow-hidden">
    <ChatSidebar
      :sidebarOpen="sidebarOpen"
      :uploadedFiles="chat.uploadedFiles.value"
      :materials="materials"
      :history="chat.history.value"
      :activeHistoryId="chat.activeHistoryId.value"
      :stats="chat.stats.value"
      :avgTime="chat.avgTime.value"
      @newChat="chat.newChat"
      @fileSelect="(e) => chat.handleFileSelect(e, showToast)"
      @loadMaterials="loadMaterials"
      @viewMaterial="viewMaterial"
      @deleteMaterial="deleteMaterialItem"
      @viewHistory="chat.viewHistory"
    />

    <div class="flex-1 flex flex-col min-w-0">
      <ChatHeader
        :currentQuery="chat.currentQuery.value"
        :isLoading="chat.isLoading.value"
        :activeSkill="chat.activeSkill.value"
        @toggleSidebar="sidebarOpen = !sidebarOpen"
      />

      <ChatMessages
        :messages="chat.messages.value"
        :isLoading="chat.isLoading.value"
        :aiNews="aiNews"
        :skills="sidebarSkills"
        @loadAiNews="loadAiNews"
        @useAiNews="(title) => { chat.query.value = title; }"
        @copyReport="chat.copyReport"
        @downloadReport="chat.downloadReport"
        @downloadPdf="chat.downloadPdf"
        @saveToLibrary="(msg) => chat.saveToLibrary(msg, showToast)"
        @ttsReport="chat.ttsReport"
        @useSkill="(skill) => { chat.activeSkill.value = skill.name; chat.query.value = ''; }"
        @switchTab="(tab) => { sidebarOpen = true; }"
        @sendHitlChoice="(choice) => chat.sendHitlChoice(choice)"
      />

      <ChatInput
        v-model="chat.query.value"
        :isLoading="chat.isLoading.value"
        :uploadedFiles="chat.uploadedFiles.value"
        :searchMode="chat.searchMode.value"
        :hasMessages="chat.messages.value.length > 0"
        :skills="sidebarSkills"
        :activeSkill="chat.activeSkill.value"
        @update:searchMode="(v) => chat.searchMode.value = v"
        @selectSkill="(name) => chat.activeSkill.value = name"
        @clearSkill="chat.clearSkill"
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
import { fetchAihotNews, listMaterials, deleteMaterial, getMaterial, listSkills } from './services/api';
import { getHistory } from './services/history';
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
const sidebarSkills = ref([]);

// === Toast ===
const toastMsg = ref('');
const toastType = ref('success');
let toastTimer = null;
const showToast = (msg, type = 'success') => {
    if (toastTimer) clearTimeout(toastTimer);
    toastMsg.value = msg;
    toastType.value = type;
    toastTimer = setTimeout(() => { toastMsg.value = ''; }, 3000);
};

// === Skills ===
const loadSkills = async () => {
    try { const d = await listSkills(); sidebarSkills.value = d.skills || []; } catch { sidebarSkills.value = []; }
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
    loadSkills();
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
