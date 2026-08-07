<template>
  <div data-chat-scroll class="flex-1 overflow-y-auto">
    <!-- 空状态 -->
    <div v-if="messages.length === 0 && !isLoading" class="h-full flex flex-col items-center justify-center px-4">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20 mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
      </div>
      <h2 class="text-lg font-semibold text-gray-800 mb-1">有什么想调研的？</h2>
      <p class="text-sm text-gray-400 mb-6">输入主题开始深度调研，或试试下方灵感</p>

      <!-- 最近新闻 -->
      <div class="w-full max-w-xl">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-lg bg-gradient-to-br from-orange-400 to-pink-500 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            </div>
            <span class="text-sm font-semibold text-gray-700">最近新闻</span>
          </div>
          <button @click="$emit('loadAiNews')" class="text-[11px] text-gray-400 hover:text-blue-500 transition-colors">换一批</button>
        </div>
        <div class="flex gap-1.5 mb-3 flex-wrap">
          <button v-for="cat in aiNewsCategories" :key="cat.key" @click="aiNewsCategory = cat.key" class="px-3 py-1 rounded-full text-[11px] font-medium transition-all duration-200" :class="aiNewsCategory === cat.key ? 'bg-gray-900 text-white shadow-md' : 'bg-white text-gray-500 hover:bg-gray-100 border border-gray-200'">
            {{ cat.label }}
          </button>
        </div>
        <div class="space-y-2 h-64 overflow-y-auto pr-1 scrollbar-none">
          <div v-for="item in filteredAiNews" :key="item.id" @click="$emit('useAiNews', item.title)" class="group p-3.5 bg-white rounded-xl border border-gray-100 cursor-pointer hover:border-blue-200 hover:shadow-md hover:shadow-blue-50 transition-all duration-300">
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
        <div v-if="msg.role !== 'user'" class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shrink-0 shadow-sm mt-1">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
        </div>

        <div class="max-w-[85%] min-w-0" :class="msg.role === 'user' ? 'order-1' : ''">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'">
            <div class="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md text-sm shadow-sm">
              {{ msg.content }}
            </div>
            <div v-if="msg.files && msg.files.length" class="flex items-center gap-1 mt-1 ml-1">
              <svg class="w-3 h-3 text-red-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span v-for="(f, i) in msg.files" :key="i" class="text-[10px] text-gray-400">{{ f }}</span>
            </div>
          </div>

          <!-- 流式消息 -->
          <div v-else-if="msg.type === 'stream'" class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
            <!-- 意图徽章 -->
            <div v-if="msg.intent" class="px-4 pt-3 flex items-center gap-2 flex-wrap">
              <span class="text-[10px] px-2 py-0.5 rounded-full font-medium" :class="intentBadgeClass(msg.intent)">{{ intentLabel(msg.intent) }}</span>
              <span v-if="msg.intentConfidence != null" class="text-[10px] text-gray-400">置信度 {{ Math.round(msg.intentConfidence * 100) }}%</span>
              <span v-if="msg.entities && msg.entities.length" class="text-[10px] text-gray-400">· {{ msg.entities.join('、') }}</span>
            </div>
            <!-- ReAct 工具轨迹 -->
            <div v-if="msg.toolTrace && msg.toolTrace.length" class="px-4 pt-2 pb-1">
              <div class="flex flex-wrap gap-1">
                <span v-for="(t, ti) in msg.toolTrace" :key="ti" class="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full" :class="t.status === 'done' ? 'bg-emerald-50 text-emerald-600 border border-emerald-100' : 'bg-amber-50 text-amber-600 border border-amber-100 animate-pulse'">
                  🛠️ {{ t.tool }}
                </span>
              </div>
            </div>
            <!-- 研究进度指示器 -->
            <div v-if="msg.active && currentPhase > 0" class="px-4 pt-3 pb-1">
              <div class="flex items-center gap-3">
                <div class="flex gap-1">
                  <span class="transition-all duration-300" :class="currentPhase >= 1 ? (currentPhase === 1 ? 'text-blue-600 scale-110' : 'text-blue-500') : 'text-gray-300'">🔍</span>
                  <span class="transition-all duration-300" :class="currentPhase >= 2 ? (currentPhase === 2 ? 'text-purple-600 scale-110 animate-pulse' : 'text-purple-500') : 'text-gray-300'">📊</span>
                  <span class="transition-all duration-300" :class="currentPhase >= 3 ? (currentPhase === 3 ? 'text-amber-600 scale-110 animate-pulse' : 'text-amber-500') : 'text-gray-300'">✍️</span>
                  <span class="transition-all duration-300" :class="currentPhase >= 4 ? 'text-green-600 scale-110' : 'text-gray-300'">✅</span>
                </div>
                <span class="text-[11px] text-gray-600 font-medium">{{ phaseText }}</span>
                <span v-if="phaseElapsed" class="text-[10px] text-gray-400">{{ phaseElapsed }}</span>
                <span v-if="totalElapsed && currentPhase >= 2" class="text-[10px] text-gray-300">· 总计 {{ totalElapsed }}</span>
              </div>
            </div>
            <div v-if="msg.statuses && msg.statuses.length" class="px-4 pt-3 pb-1 space-y-1.5">
              <div v-for="(s, i) in msg.statuses" :key="i">
                <div class="flex items-center gap-2 text-[11px]" :class="s.detail && s.detail.includes('审查') ? '' : ''">
                  <span class="w-4 h-4 rounded-full flex items-center justify-center shrink-0" :class="s.active ? (s.detail ? 'bg-red-100' : 'bg-blue-100') : 'bg-green-50'">
                    <span v-if="s.active" class="w-1.5 h-1.5 rounded-full animate-pulse" :class="s.detail ? 'bg-red-500' : 'bg-blue-500'"></span>
                    <span v-else class="text-green-500 text-[9px]">✓</span>
                  </span>
                  <span :class="s.active ? (s.detail ? 'text-red-600 font-medium' : 'text-blue-600 font-medium') : 'text-gray-400'">{{ s.text }}</span>
                </div>
                <!-- 搜索方向卡片 -->
                <div v-if="s.items && s.items.length" class="ml-6 mt-1 flex flex-wrap gap-1">
                  <span v-for="(item, j) in s.items" :key="j" class="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">{{ item }}</span>
                </div>
                <!-- 子任务卡片（Orchestrator-Worker 规划） -->
                <div v-if="s.subtasks && s.subtasks.length" class="ml-6 mt-1.5 grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  <div v-for="(st, si) in s.subtasks" :key="si" class="px-2.5 py-1.5 rounded-lg bg-purple-50 border border-purple-100">
                    <p class="text-[10px] font-medium text-purple-700 truncate">{{ st.subtask }}</p>
                    <div class="mt-0.5 flex flex-wrap gap-1">
                      <span v-for="(query, qi) in st.queries" :key="qi" class="text-[9px] px-1 py-px rounded bg-white text-gray-500 border border-gray-100">{{ query }}</span>
                    </div>
                  </div>
                </div>
                <!-- 审查意见（红色警告） -->
                <div v-if="s.detail" class="ml-6 mt-1 px-2.5 py-1.5 rounded-lg text-[10px] leading-relaxed" :class="s.detail.includes('审查') ? 'bg-red-50 text-red-600 border border-red-100' : 'text-gray-400'">
                  {{ s.detail }}
                </div>
              </div>
            </div>
            <div v-if="msg.streamText" class="px-4 pb-3 pt-1">
              <div class="prose prose-sm max-w-none leading-relaxed" v-html="renderMarkdown(msg.streamText)"></div>
              <span v-if="msg.active" class="inline-block w-2 h-4 bg-blue-500 align-middle rounded-[1px] stream-cursor"></span>
            </div>
            <div v-else-if="msg.active" class="px-4 pb-3 flex items-center gap-1.5">
              <span class="flex gap-0.5">
                <span class="w-1 h-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay:0ms"></span>
                <span class="w-1 h-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay:150ms"></span>
                <span class="w-1 h-1 rounded-full bg-blue-400 animate-bounce" style="animation-delay:300ms"></span>
              </span>
              <span class="text-[11px] text-gray-400">{{ phaseText || '思考中...' }}</span>
            </div>
          </div>

          <!-- 报告消息 -->
          <div v-else-if="msg.type === 'report'" class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
            <div class="px-4 py-2.5 border-b border-gray-50 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-5 h-5 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                </span>
                <span class="text-xs font-bold text-gray-700">研究报告</span>
              </div>
              <div class="flex items-center gap-1">
                <button @click="$emit('copyReport', msg)" class="text-[10px] text-gray-400 hover:text-blue-500 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors">📋 复制</button>
                <button @click="$emit('downloadReport', msg)" class="text-[10px] text-gray-400 hover:text-purple-500 px-2 py-1 rounded-lg hover:bg-purple-50 transition-colors">⬇️ 下载</button>
                <button @click="$emit('downloadPdf', msg)" class="text-[10px] text-gray-400 hover:text-red-500 px-2 py-1 rounded-lg hover:bg-red-50 transition-colors">📥 PDF</button>
                <button @click="$emit('saveToLibrary', msg)" class="text-[10px] text-white bg-gradient-to-r from-blue-500 to-purple-500 px-2.5 py-1 rounded-full hover:shadow-md transition-all">💾 保存素材库</button>
              </div>
            </div>

            <!-- 研究轨迹（多轮时显示） -->
            <div v-if="msg.rounds && msg.rounds.length > 1" class="border-b border-gray-50">
              <button @click="msg._trajectoryExpanded = !msg._trajectoryExpanded" class="w-full px-4 py-2 flex items-center gap-2 text-[11px] text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 transition-transform" :class="msg._trajectoryExpanded ? 'rotate-90' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                <span>研究轨迹 · {{ msg.rounds.length }} 轮</span>
              </button>
              <Transition name="slide">
                <div v-if="msg._trajectoryExpanded" class="px-4 pb-3">
                  <div class="relative pl-4">
                    <!-- 竖线 -->
                    <div class="absolute left-[7px] top-1 bottom-1 w-px bg-gray-200"></div>
                    <div v-for="(r, ri) in msg.rounds" :key="ri" class="relative mb-2 last:mb-0">
                      <!-- 节点圆点 -->
                      <div class="absolute -left-4 top-0.5 w-3.5 h-3.5 rounded-full border-2 border-white flex items-center justify-center" :class="ri === msg.rounds.length - 1 ? 'bg-blue-500' : 'bg-gray-300'">
                        <span class="text-[7px] text-white font-bold">{{ r.number }}</span>
                      </div>
                      <div class="ml-1">
                        <span class="text-[10px] font-medium" :class="ri === msg.rounds.length - 1 ? 'text-blue-600' : 'text-gray-500'">第 {{ r.number }} 轮</span>
                        <div class="mt-0.5 flex flex-wrap gap-1">
                          <span v-for="(d, di) in r.directions" :key="di" class="text-[10px] px-1.5 py-0.5 rounded bg-gray-50 text-gray-500 border border-gray-100">{{ d }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </Transition>
            </div>

            <div class="prose prose-sm max-w-none p-5 leading-relaxed" v-html="renderMarkdown(msg.content)"></div>
          </div>

          <!-- Human-in-the-loop 决策卡片 -->
          <div v-else-if="msg.hitl" class="bg-indigo-50 border border-indigo-200 rounded-2xl px-4 py-3.5 shadow-sm">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-5 h-5 rounded-lg bg-indigo-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              </span>
              <span class="text-[11px] font-bold text-indigo-700">需要你决定下一步</span>
            </div>
            <p class="text-[12px] text-indigo-900 whitespace-pre-line leading-relaxed mb-3">{{ msg.hitl.question }}</p>
            <div class="flex flex-wrap gap-2">
              <button @click="$emit('sendHitlChoice', '重试')" class="px-3 py-1.5 text-[11px] rounded-lg bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100 transition-colors">🔄 重试搜索</button>
              <button @click="$emit('sendHitlChoice', '就用当前内容定稿')" class="px-3 py-1.5 text-[11px] rounded-lg bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100 transition-colors">✅ 就用当前内容</button>
            </div>
            <div class="mt-2 flex gap-2">
              <input v-model="hitlDirection" @keyup.enter="sendRedirect" type="text" placeholder="输入新的调研方向..." class="flex-1 px-3 py-1.5 text-[11px] border border-indigo-200 rounded-lg focus:outline-none focus:border-indigo-400" />
              <button @click="sendRedirect" :disabled="!hitlDirection.trim()" class="px-3 py-1.5 text-[11px] rounded-lg bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-100 transition-colors disabled:opacity-40">🧭 换方向</button>
            </div>
          </div>

          <!-- 澄清消息 -->
          <div v-else-if="msg.type === 'clarify'" class="bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 shadow-sm">
            <div class="flex items-start gap-2">
              <span class="text-sm mt-0.5">🤔</span>
              <div>
                <p class="text-[10px] font-medium text-amber-600 mb-1">需要澄清</p>
                <p class="text-sm text-amber-800 leading-relaxed">{{ msg.content }}</p>
              </div>
            </div>
          </div>

          <!-- 错误消息 -->
          <div v-else-if="msg.type === 'error'" class="bg-red-50 border border-red-100 rounded-2xl px-4 py-3 shadow-sm">
            <div class="flex items-center gap-2">
              <span class="text-sm">⚠️</span>
              <span class="text-xs text-red-600">{{ msg.content }}</span>
            </div>
          </div>

          <!-- 其他 -->
          <div v-else class="bg-white border border-gray-100 rounded-2xl px-4 py-3 shadow-sm">
            <div class="text-sm text-gray-700 prose prose-sm max-w-none" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { renderMarkdown } from '../utils/markdown';

const props = defineProps({
    messages: { type: Array, default: () => [] },
    isLoading: Boolean,
    aiNews: { type: Array, default: () => [] },
    skills: { type: Array, default: () => [] },
});

const hitlDirection = ref('');
const sendRedirect = () => {
    if (!hitlDirection.value.trim()) return;
    emit('sendHitlChoice', 'redirect', hitlDirection.value.trim());
    hitlDirection.value = '';
};

const emit = defineEmits(['loadAiNews', 'useAiNews', 'copyReport', 'downloadReport', 'downloadPdf', 'saveToLibrary', 'ttsReport', 'useSkill', 'switchTab', 'sendHitlChoice']);

// 研究进度阶段
const activeStreamMsg = computed(() => {
    if (!props.isLoading) return null;
    return [...props.messages].reverse().find(m => m.type === 'stream' && m.active);
});
const currentPhase = computed(() => activeStreamMsg.value?.currentPhase ?? 0);
const phaseText = computed(() => {
    const t = { 0: '准备中...', 1: '搜索中', 2: '分析中', 3: '撰写中', 4: '完成' };
    return t[currentPhase.value] || '';
});

// 意图徽章
const intentLabel = (i) => ({
    research: '深度调研', chat: '对话', sql: 'SQL', tool_call: '工具调用',
    refine: '报告修订', clarify: '需澄清',
}[i] || i);
const intentBadgeClass = (i) => ({
    research: 'bg-blue-50 text-blue-600 border border-blue-100',
    chat: 'bg-gray-100 text-gray-600 border border-gray-100',
    sql: 'bg-cyan-50 text-cyan-600 border border-cyan-100',
    tool_call: 'bg-amber-50 text-amber-600 border border-amber-100',
    refine: 'bg-purple-50 text-purple-600 border border-purple-100',
    clarify: 'bg-red-50 text-red-600 border border-red-100',
}[i] || 'bg-gray-100 text-gray-600 border border-gray-100');

// 阶段计时
const phaseTimestamps = ref({});
watch(currentPhase, (phase, oldPhase) => {
    if (phase > 0 && phase !== oldPhase) {
        phaseTimestamps.value[phase] = Date.now();
    }
});
const phaseElapsed = computed(() => {
    const phase = currentPhase.value;
    if (phase <= 1) return '';
    const start = phaseTimestamps.value[phase];
    if (!start) return '';
    const secs = Math.floor((Date.now() - start) / 1000);
    return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m${secs % 60}s`;
});
const totalElapsed = computed(() => {
    const start = phaseTimestamps.value[1];
    if (!start) return '';
    const secs = Math.floor((Date.now() - start) / 1000);
    return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m${secs % 60}s`;
});

// 定时刷新耗时显示
const tick = ref(0);
let tickInterval = null;
watch(() => props.isLoading, (v) => {
    if (v && !tickInterval) tickInterval = setInterval(() => tick.value++, 1000);
    else if (!v && tickInterval) { clearInterval(tickInterval); tickInterval = null; }
});

const aiNewsCategory = ref('');

const aiNewsCategories = [
    { key: '', label: '全部' },
    { key: 'ai-models', label: '模型' },
    { key: 'ai-products', label: '产品' },
    { key: 'industry', label: '行业' },
    { key: 'paper', label: '论文' },
    { key: 'tip', label: '技巧' },
];

const filteredAiNews = computed(() => {
    const items = aiNewsCategory.value ? props.aiNews.filter(i => i.category === aiNewsCategory.value) : props.aiNews;
    return items.slice(0, 8);
});

const catLabel = (cat) => {
    const m = { 'ai-models': '模型', 'ai-products': '产品', 'industry': '行业', 'paper': '论文', 'tip': '技巧' };
    return m[cat] || '';
};
</script>

<style scoped>
@keyframes streamCursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.stream-cursor { animation: streamCursorBlink 1s step-end infinite; }

.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; overflow: hidden; }
.slide-enter-from, .slide-leave-to { max-height: 0; opacity: 0; padding-top: 0; padding-bottom: 0; }
.slide-enter-to, .slide-leave-from { max-height: 300px; opacity: 1; }

/* 报告 Markdown 渲染样式 */
:deep(.prose table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.8125rem;
}
:deep(.prose thead th) {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
}
:deep(.prose tbody td) {
  border: 1px solid #e5e7eb;
  padding: 0.5rem 0.75rem;
  color: #4b5563;
}
:deep(.prose tbody tr:nth-child(even)) {
  background: #f9fafb;
}
:deep(.prose pre) {
  background: #1e293b;
  color: #e2e8f0;
  border-radius: 0 0.5rem 0.5rem 0.5rem;
  padding: 1rem;
  overflow-x: auto;
  font-size: 0.8125rem;
  line-height: 1.6;
  margin-top: 0;
}
:deep(.code-block) {
  margin: 1rem 0;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #1e293b;
}
:deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #0f172a;
  padding: 0.375rem 0.75rem;
}
:deep(.code-block-lang) {
  font-size: 0.6875rem;
  color: #94a3b8;
  font-family: ui-monospace, monospace;
}
:deep(.code-block-copy) {
  font-size: 0.6875rem;
  color: #94a3b8;
  background: transparent;
  border: 1px solid #334155;
  padding: 0.125rem 0.5rem;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: all 0.15s;
}
:deep(.code-block-copy:hover) {
  color: #e2e8f0;
  border-color: #64748b;
  background: #1e293b;
}
:deep(.code-block pre) {
  border-radius: 0;
  margin: 0;
}
:deep(.prose code) {
  font-size: 0.8125rem;
}
:deep(.prose :not(pre) > code) {
  background: #f1f5f9;
  color: #e11d48;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
}
:deep(.prose blockquote) {
  border-left: 3px solid #93c5fd;
  background: #eff6ff;
  padding: 0.75rem 1rem;
  margin: 1rem 0;
  border-radius: 0 0.5rem 0.5rem 0;
  color: #1e40af;
  font-size: 0.875rem;
}
:deep(.prose sup) {
  color: #6366f1;
  font-weight: 600;
}
:deep(.citation-ref) {
  color: #6366f1;
  font-weight: 600;
  text-decoration: none;
  border-bottom: 1px dashed #c7d2fe;
  padding: 0 1px;
  cursor: pointer;
  transition: color 0.15s;
}
:deep(.citation-ref:hover) {
  color: #4338ca;
  border-bottom-color: #6366f1;
}
:deep(.prose hr) {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 1.5rem 0;
}
</style>
