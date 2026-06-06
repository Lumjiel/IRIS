<template>
  <div class="h-screen flex bg-gray-50 overflow-hidden">

    <!-- 侧边栏 -->
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 transition-transform duration-300" :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 fixed lg:relative z-30 h-full'">
      <!-- Logo -->
      <div class="px-5 py-4 border-b border-gray-100">
        <h1 class="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">IRIS</h1>
        <p class="text-[10px] text-gray-400 mt-0.5">智能调研系统</p>
      </div>

      <!-- 新建调研 -->
      <div class="px-3 pt-3">
        <button @click="newChat" class="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          新建调研
        </button>
      </div>

      <!-- Tab 切换 -->
      <div class="flex border-b border-gray-100 mt-2 mx-3">
        <button v-for="tab in [{key:'kb',label:'知识库'},{key:'materials',label:'素材库'},{key:'history',label:'历史'}]" :key="tab.key" @click="activeTab = tab.key; if(tab.key==='materials') loadMaterials()" class="flex-1 py-2 text-[11px] font-bold transition-colors relative" :class="activeTab === tab.key ? 'text-blue-600' : 'text-gray-400'">
          {{ tab.label }}
          <div v-if="activeTab === tab.key" class="absolute bottom-0 left-1/4 right-1/4 h-0.5 bg-blue-500 rounded-full"></div>
        </button>
      </div>

      <!-- Tab 内容 -->
      <div class="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        <!-- 知识库 -->
        <template v-if="activeTab === 'kb'">
          <div class="border-2 border-dashed rounded-xl p-3 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-all" :class="uploadedFiles.length > 0 ? 'border-green-300 bg-green-50/30' : 'border-gray-200'" @click="$refs.fileInput.click()">
            <input ref="fileInput" type="file" multiple accept=".pdf" class="hidden" @change="handleFileSelect" />
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
          <div class="flex items-center gap-2 px-2 py-1.5 text-[11px] text-gray-400">
            <span class="flex-1 text-center bg-gray-100 rounded-lg py-1" :class="searchMode === 'hybrid' ? 'text-purple-600 font-bold' : ''">混合模式</span>
          </div>
        </template>

        <!-- 素材库 -->
        <template v-if="activeTab === 'materials'">
          <div v-if="materials.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无素材<br><span class="text-[10px]">调研完成后点击「💾 保存素材库」</span></div>
          <div v-for="m in materials" :key="m.filename" class="group px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors cursor-pointer" @click="viewMaterial(m)">
            <div class="flex items-center justify-between">
              <p class="text-[11px] font-medium text-gray-700 truncate flex-1">{{ m.filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '') }}</p>
              <button @click.stop="deleteMaterialItem(m.filename)" class="text-[10px] text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all px-1">✕</button>
            </div>
            <p class="text-[10px] text-gray-400 mt-0.5">{{ m.filename.split('-').slice(0, 3).join('-') }} · {{ formatSize(m.size) }}</p>
          </div>
        </template>

        <!-- 历史 -->
        <template v-if="activeTab === 'history'">
          <div v-if="history.length === 0" class="text-center text-[11px] text-gray-300 py-8">暂无历史</div>
          <div v-for="s in history" :key="s.id" @click="viewHistory(s)" class="px-3 py-2 rounded-lg cursor-pointer transition-colors text-[11px]" :class="activeHistoryId === s.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-600'">
            <p class="truncate font-medium">{{ s.query }}</p>
            <p class="text-[10px] text-gray-400 mt-0.5">{{ formatTime(s.timestamp) }}</p>
          </div>
        </template>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="flex-1 flex flex-col min-w-0">

      <!-- 顶栏 -->
      <header class="h-12 border-b border-gray-200 bg-white/80 backdrop-blur flex items-center px-4 gap-3 shrink-0">
        <button @click="sidebarOpen = !sidebarOpen" class="lg:hidden p-1 text-gray-400 hover:text-gray-600">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-700 truncate">{{ currentQuery || 'IRIS 智能调研' }}</p>
        </div>
        <div v-if="isLoading" class="flex items-center gap-1.5 text-[11px] text-blue-500">
          <div class="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
          调研中...
        </div>
      </header>

      <!-- 消息区域 -->
      <div ref="chatContainer" class="flex-1 overflow-y-auto" @scroll="handleScroll">

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
              <button @click="loadAiNews" class="text-[11px] text-gray-400 hover:text-blue-500 transition-colors">换一批</button>
            </div>
            <!-- 分类 -->
            <div class="flex gap-1.5 mb-3 flex-wrap">
              <button v-for="cat in aiNewsCategories" :key="cat.key" @click="aiNewsCategory = cat.key" class="px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-200" :class="aiNewsCategory === cat.key ? 'bg-gray-900 text-white shadow-md' : 'bg-white text-gray-500 hover:bg-gray-100 border border-gray-200'">
                {{ cat.label }}
              </button>
            </div>
            <!-- 卡片列表 -->
            <div class="space-y-2 h-64 overflow-y-auto pr-1 scrollbar-none">
              <div v-for="item in filteredAiNews" :key="item.id" @click="useAiNews(item.title)" class="group p-3.5 bg-white rounded-xl border border-gray-100 cursor-pointer hover:border-blue-200 hover:shadow-md hover:shadow-blue-50 transition-all duration-300">
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
            <!-- 助手头像 -->
            <div v-if="msg.role !== 'user'" class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0 shadow-sm mt-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
            </div>

            <div class="max-w-[85%] min-w-0" :class="msg.role === 'user' ? 'order-1' : ''">
              <!-- 用户消息 -->
              <div v-if="msg.role === 'user'" class="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md text-sm shadow-sm">
                {{ msg.content }}
              </div>

              <!-- 流式消息：状态累积 + 实时文本 -->
              <div v-else-if="msg.type === 'stream'" class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
                <!-- 状态时间线 -->
                <div v-if="msg.statuses && msg.statuses.length" class="px-4 pt-3 pb-1 space-y-1.5">
                  <div v-for="(s, i) in msg.statuses" :key="i">
                    <div class="flex items-center gap-2 text-[11px]">
                      <span class="w-4 h-4 rounded-full flex items-center justify-center shrink-0" :class="s.active ? 'bg-blue-100' : 'bg-green-50'">
                        <span v-if="s.active" class="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                        <span v-else class="text-green-500 text-[9px]">✓</span>
                      </span>
                      <span :class="s.active ? 'text-blue-600 font-medium' : 'text-gray-400'">{{ s.text }}</span>
                    </div>
                    <!-- 详情列表（搜索方向等） -->
                    <div v-if="s.items && s.items.length" class="ml-6 mt-0.5 space-y-0.5">
                      <div v-for="(item, j) in s.items" :key="j" class="text-[10px] text-gray-400 leading-relaxed">→ {{ item }}</div>
                    </div>
                    <!-- 单行详情（审查意见等） -->
                    <div v-if="s.detail" class="ml-6 mt-0.5 text-[10px] text-gray-400 leading-relaxed">{{ s.detail }}</div>
                  </div>
                </div>
                <!-- 流式文本 -->
                <div v-if="msg.streamText" class="px-4 pb-3 pt-1">
                  <div class="text-[13px] text-gray-700 leading-relaxed whitespace-pre-line border-l-2 border-blue-200 pl-3">{{ msg.streamText }}</div>
                </div>
                <!-- 光标 -->
                <div v-if="msg.active" class="px-4 pb-3">
                  <span class="inline-block w-0.5 h-4 bg-blue-500 animate-pulse align-middle"></span>
                </div>
              </div>

              <!-- 报告消息（Markdown 渲染） -->
              <div v-else-if="msg.type === 'report'" class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
                <div class="px-4 py-2.5 border-b border-gray-50 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    </span>
                    <span class="text-xs font-bold text-gray-700">研究报告</span>
                  </div>
                  <div class="flex items-center gap-1">
                    <button @click="copyReport(msg)" class="text-[10px] text-gray-400 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors">📋 复制</button>
                    <button @click="downloadReport(msg)" class="text-[10px] text-gray-400 hover:text-purple-500 px-2 py-1 rounded-lg hover:bg-purple-50 transition-colors">⬇️ 下载</button>
                    <button @click="saveToLibrary(msg)" class="text-[10px] text-white bg-gradient-to-r from-blue-500 to-purple-500 px-2.5 py-1 rounded-full hover:shadow-md transition-all">💾 保存素材库</button>
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

              <!-- 其他（步骤等） -->
              <div v-else class="bg-white border border-gray-100 rounded-2xl px-4 py-3 shadow-sm">
                <div class="text-sm text-gray-700 prose prose-sm max-w-none" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="border-t border-gray-200 bg-white px-4 py-3 shrink-0">
        <div class="max-w-3xl mx-auto">
          <div class="flex items-end gap-2 bg-gray-50 rounded-2xl border border-gray-200 focus-within:border-blue-300 focus-within:ring-2 focus-within:ring-blue-100 transition-all px-4 py-2">
            <textarea
              ref="inputBox"
              v-model="query"
              @keydown.enter.exact.prevent="sendMessage"
              class="flex-1 bg-transparent resize-none text-sm text-gray-700 placeholder-gray-400 focus:outline-none leading-relaxed"
              :rows="1"
              :placeholder="isLoading ? '调研中...' : '输入研究主题...'"
              :disabled="isLoading"
              @input="autoResize"
            ></textarea>
            <button
              v-if="isLoading"
              @click="stopResearch"
              class="shrink-0 w-9 h-9 rounded-xl bg-red-500 hover:bg-red-600 text-white flex items-center justify-center transition-colors shadow-sm"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            </button>
            <button
              v-else
              @click="sendMessage"
              :disabled="!query.trim()"
              class="shrink-0 w-9 h-9 rounded-xl bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
          <p class="text-[10px] text-gray-300 text-center mt-1.5">IRIS 可能会犯错，请核实重要信息</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue';
import { uploadFiles, streamChat, clearContext, fetchAihotNews, saveReport, listMaterials, deleteMaterial, getMaterial, getThreadId, setThreadId, newThreadId } from './services/api';
import { getHistory, saveSession, deleteSession, clearHistory, markAsUsed } from './services/history';
import MarkdownIt from 'markdown-it';
import mk from 'markdown-it-katex';

// Markdown 渲染器
const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
md.use(mk);
md.renderer.rules.heading_open = (tokens, idx) => {
    const token = tokens[idx];
    const content = tokens[idx + 1].content;
    const id = content.replace(/[^\w一-鿿]/g, '-').toLowerCase();
    return `<${token.tag} id="${id}">`;
};

const renderMarkdown = (text) => {
    if (!text) return '';
    let raw = text.replace(/\\\[/g, '$$$').replace(/\\\]/g, '$$$');
    raw = raw.replace(/\\\(/g, '$').replace(/\\\)/g, '$');
    return md.render(raw);
};

// === 状态 ===
const query = ref('');
const messages = ref([]);
const isLoading = ref(false);
const currentQuery = ref('');
const chatContainer = ref(null);
const inputBox = ref(null);
const sidebarOpen = ref(false);
const activeTab = ref('kb');
const searchMode = ref('hybrid');
const uploadedFiles = ref([]);
const history = ref([]);
const activeHistoryId = ref(null);
const aiNews = ref([]);
const aiNewsCategory = ref('');
const materials = ref([]);
const aiNewsCategories = [
    { key: '', label: '全部' },
    { key: 'ai-models', label: '模型' },
    { key: 'ai-products', label: '产品' },
    { key: 'industry', label: '行业' },
    { key: 'paper', label: '论文' },
    { key: 'tip', label: '技巧' },
];

const filteredAiNews = computed(() => {
    const items = aiNewsCategory.value ? aiNews.value.filter(i => i.category === aiNewsCategory.value) : aiNews.value;
    return items.slice(0, 8);
});

const catLabel = (cat) => {
    const m = { 'ai-models': '模型', 'ai-products': '产品', 'industry': '行业', 'paper': '论文', 'tip': '技巧' };
    return m[cat] || '';
};

// === 研究流 ===
let currentAbortController = null;
let msgIdCounter = 0;

const getMsgById = (id) => messages.value.find(m => m.id === id);

const addMessage = (role, type, content, extra = {}) => {
    const msg = { id: ++msgIdCounter, role, type, content, timestamp: Date.now(), status: 'done', streaming: false, ...extra };
    messages.value.push(msg);
    scrollToBottom();
    return msg;
};

const finishStatuses = (msgId) => {
    const msg = getMsgById(msgId);
    if (msg?.statuses) msg.statuses.forEach(s => s.active = false);
};

const scrollToBottom = () => {
    nextTick(() => {
        if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
    });
};

const handleScroll = () => {};

const autoResize = (e) => {
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};

// === 研究流程 ===
const sendMessage = async () => {
    const q = query.value.trim();
    if (!q || isLoading.value) return;

    addMessage('user', 'text', q);
    currentQuery.value = q;
    query.value = '';
    if (inputBox.value) inputBox.value.style.height = 'auto';

    isLoading.value = true;
    activeHistoryId.value = null;
    currentAbortController = new AbortController();

    if (uploadedFiles.value.length > 0) {
        try { await uploadFiles(uploadedFiles.value); } catch (e) {
            addMessage('assistant', 'error', `文件上传失败: ${e.message}`);
            isLoading.value = false; return;
        }
    } else {
        try { await clearContext(); } catch {}
    }

    const actualMode = uploadedFiles.value.length === 0 ? 'hybrid' : searchMode.value;

    // 创建流式消息：累积状态 + 流式文本
    const sMsg = addMessage('assistant', 'stream', '', {
        statuses: [{ text: '准备中...', active: true }],
        streamText: '',
        active: true,
    });
    let round = 0;  // 轮次追踪

    streamChat(
        q, actualMode,
        (data) => {
            const msg = getMsgById(sMsg.id);
            if (!msg) return;

            // ── 流式 token（即时渲染）──
            if (data.step === 'planner_token') {
                if (!data.data.final && data.data.token) {
                    msg.streamText += data.data.token;
                    scrollToBottom();
                }
                return;
            }
            if (data.step === 'writer_token') {
                if (!data.data.final && data.data.token) {
                    msg.streamText += data.data.token;
                    scrollToBottom();
                }
                return;
            }

            // ── 图节点事件（累积状态 + 详情）──
            if (data.step === 'planner') {
                round++;
                const plans = data.data.plan || [];
                const status = {
                    text: `第 ${round} 轮 · 拆解了 ${plans.length} 个搜索方向`,
                    active: true,
                    items: plans,
                };
                if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                msg.statuses.push(status);
                msg.streamText = '';
                scrollToBottom();
            }
            else if (data.step === 'researcher') {
                const results = data.data.search_results || [];
                // 提取来源名
                const sources = results.map(r => {
                    const m = r.match(/### .+?[（(]([^)）]+)[)）]/) || r.match(/### (.+)/);
                    return m ? m[1].trim() : null;
                }).filter(Boolean);
                if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                msg.statuses.push({
                    text: `检索到 ${sources.length || results.length} 个信息源`,
                    active: true,
                    items: sources.length ? sources : results.map((_, i) => `来源 ${i + 1}`),
                });
                msg.streamText = '';
                scrollToBottom();
            }
            else if (data.step === 'writer') {
                if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                msg.statuses.push({ text: '正在撰写报告...', active: true });
                if (data.data.final_report) msg.streamText = data.data.final_report;
                scrollToBottom();
            }
            else if (data.step === 'reviewer') {
                if (data.data.review_status === 'FAIL') {
                    const critique = data.data.critique || '需要补充信息';
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push({
                        text: `第 ${round} 轮审查未通过，启动第 ${round + 1} 轮`,
                        active: true,
                        detail: `审查意见：${critique.slice(0, 100)}${critique.length > 100 ? '...' : ''}`,
                    });
                    msg.streamText = '';
                } else {
                    if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                    msg.statuses.push({ text: '审查通过，报告完成 ✓', active: false });
                    finishStatuses(sMsg.id);
                    msg.type = 'report';
                    msg.content = msg.streamText || '';
                    msg.active = false;
                }
                scrollToBottom();
            }
            else if (data.step === 'refiner') {
                if (msg.statuses) msg.statuses.forEach(s => s.active = false);
                msg.statuses.push({ text: '修订完成 ✓', active: false });
                finishStatuses(sMsg.id);
                if (data.data.final_report) {
                    msg.type = 'report';
                    msg.content = data.data.final_report;
                    msg.active = false;
                }
                scrollToBottom();
            }
            else if (data.step === 'error') {
                finishStatuses(sMsg.id);
                msg.type = 'error';
                msg.content = data.data?.message || '研究过程中发生错误';
                msg.active = false;
                scrollToBottom();
            }
        },
        () => {
            isLoading.value = false;
            const msg = getMsgById(sMsg.id);
            if (msg) {
                finishStatuses(sMsg.id);
                msg.active = false;
                if (msg.type === 'stream' && msg.streamText) {
                    msg.type = 'report';
                    msg.content = msg.streamText;
                } else if (msg.type === 'stream' && !msg.streamText) {
                    msg.type = 'error';
                    msg.content = '未能生成报告，请重试';
                }
            }
            // 保存完整会话
            const finalReport = msg?.streamText || msg?.content || '';
            if (currentQuery.value) {
                saveSession({
                    query: currentQuery.value,
                    report: finalReport,
                    mode: actualMode,
                    threadId: getThreadId(),
                    messages: messages.value.map(m => ({
                        role: m.role, type: m.type, content: m.content,
                        statuses: m.statuses, streamText: m.streamText,
                    })),
                });
                history.value = getHistory();
            }
        },
        (err) => {
            isLoading.value = false;
            addMessage('assistant', 'error', `请求失败: ${err?.message || '未知错误'}`);
            // 出错也要保存已有的消息
            if (currentQuery.value) {
                saveSession({
                    query: currentQuery.value,
                    report: '',
                    mode: actualMode,
                    threadId: getThreadId(),
                    messages: messages.value.map(m => ({
                        role: m.role, type: m.type, content: m.content,
                        statuses: m.statuses, streamText: m.streamText,
                    })),
                });
                history.value = getHistory();
            }
        },
        currentAbortController?.signal
    );
};

const stopResearch = () => {
    if (currentAbortController) currentAbortController.abort();
    isLoading.value = false;
};

// === 推文灵感 ===
const loadAiNews = async () => {
    try {
        const data = await fetchAihotNews(20);
        aiNews.value = data.items || [];
    } catch { aiNews.value = []; }
};

const useAiNews = (title) => {
    query.value = title;
    if (inputBox.value) inputBox.value.focus();
};

// === 素材库 ===
const loadMaterials = async () => {
    try {
        const data = await listMaterials();
        materials.value = data.items || [];
    } catch { materials.value = []; }
};

const viewMaterial = async (m) => {
    messages.value = [];
    currentQuery.value = m.filename.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '');
    addMessage('user', 'text', `查看素材：${currentQuery.value}`);
    try {
        const data = await getMaterial(m.filename);
        addMessage('assistant', 'report', data.content);
    } catch {
        addMessage('assistant', 'error', '读取素材失败');
    }
    scrollToBottom();
};

const deleteMaterialItem = async (filename) => {
    try {
        await deleteMaterial(filename);
        materials.value = materials.value.filter(m => m.filename !== filename);
        showToast('已删除', 'success');
    } catch { showToast('删除失败', 'error'); }
};

const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
};

// === 导出 ===
const copyReport = async (msg) => {
    try { await navigator.clipboard.writeText(msg.content); } catch {}
};

const downloadReport = (msg) => {
    const blob = new Blob([msg.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `IRIS-${currentQuery.value || 'report'}.md`;
    a.click();
    URL.revokeObjectURL(url);
};

const saveToLibrary = async (msg) => {
    try {
        await saveReport(currentQuery.value, msg.content);
        showToast('已保存到素材库', 'success');
    } catch { showToast('保存失败', 'error'); }
};

// === 历史 ===
const viewHistory = (session) => {
    messages.value = [];
    currentQuery.value = session.query;
    activeHistoryId.value = session.id;

    // 恢复 thread_id（多轮对话关键）
    if (session.threadId) {
        setThreadId(session.threadId);
    }

    // 恢复完整消息列表
    if (session.messages && session.messages.length > 0) {
        session.messages.forEach(m => {
            addMessage(m.role, m.type, m.content, {
                statuses: m.statuses,
                streamText: m.streamText,
                active: false,
            });
        });
    } else {
        // 兼容旧版历史（只有 query + report）
        addMessage('user', 'text', session.query);
        addMessage('assistant', 'report', session.report);
    }
    scrollToBottom();
};

const formatTime = (ts) => {
    const d = new Date(ts);
    const diff = Date.now() - ts;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return `${d.getMonth() + 1}/${d.getDate()}`;
};

const newChat = () => {
    messages.value = [];
    currentQuery.value = '';
    activeHistoryId.value = null;
    if (isLoading.value) stopResearch();
    // 生成新的 thread_id，下次发送走新会话
    newThreadId();
};

// === Toast ===
const toastMsg = ref('');
const toastType = ref('success');
const showToast = (msg, type = 'success') => {
    toastMsg.value = msg;
    toastType.value = type;
    setTimeout(() => { toastMsg.value = ''; }, 3000);
};

// === 生命周期 ===
onMounted(() => {
    history.value = getHistory();
    loadAiNews();

    // 刷新恢复：找到当前 thread_id 对应的最近会话
    const currentThreadId = getThreadId();
    const recentSession = history.value.find(s => s.threadId === currentThreadId);
    if (recentSession) {
        viewHistory(recentSession);
    }

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); sendMessage(); }
    });
});
</script>

<style>
.prose { font-size: 0.875rem; line-height: 1.7; }
.prose h1 { font-size: 1.25rem; font-weight: 700; margin: 1.5rem 0 0.75rem; }
.prose h2 { font-size: 1.1rem; font-weight: 700; margin: 1.25rem 0 0.5rem; padding-left: 0.75rem; border-left: 3px solid #3b82f6; }
.prose h3 { font-size: 1rem; font-weight: 600; margin: 1rem 0 0.5rem; }
.prose p { margin: 0.5rem 0; }
.prose ul, .prose ol { padding-left: 1.5rem; margin: 0.5rem 0; }
.prose li { margin: 0.25rem 0; }
.prose blockquote { border-left: 3px solid #3b82f6; padding-left: 1rem; color: #6b7280; margin: 1rem 0; }
.prose code { background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.8em; }
.prose pre { background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 0.75rem; overflow-x: auto; margin: 1rem 0; }
.prose pre code { background: transparent; padding: 0; color: inherit; }
.prose table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.8rem; }
.prose th, .prose td { border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; text-align: left; }
.prose th { background: #f9fafb; font-weight: 600; }
.prose strong { font-weight: 700; color: #111827; }
.katex { font-size: 1em; }
.scrollbar-none { -ms-overflow-style: none; scrollbar-width: none; }
.scrollbar-none::-webkit-scrollbar { display: none; }

/* 流式消息过渡 */
.stream-enter-active { transition: all 0.3s ease; }
.stream-leave-active { transition: all 0.2s ease; }
.stream-enter-from { opacity: 0; transform: translateY(8px); }

/* 报告卡片 */
.report-card { transition: box-shadow 0.2s; }
.report-card:hover { box-shadow: 0 4px 24px rgba(0,0,0,0.06); }

/* 流式文本区域 */
.stream-body {
  font-size: 0.8125rem;
  line-height: 1.8;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
