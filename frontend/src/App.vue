<template>
  <div class="h-screen flex flex-col">
    <!-- 顶栏 -->
    <header class="h-12 border-b border-slate-200 bg-white px-4 flex items-center gap-3 shrink-0">
      <span class="text-sm font-semibold text-slate-900">IRIS 投研助手</span>
      <span class="text-label text-slate-400">基于 LangGraph 多智能体协同</span>
    </header>

    <!-- 消息列表 -->
    <main ref="scrollEl" class="flex-1 overflow-y-auto">
      <div class="max-w-3xl mx-auto py-6 px-4 space-y-4">
        <!-- 空状态 -->
        <div v-if="messages.length === 0" class="h-full flex items-center justify-center text-slate-400">
          <div class="text-center">
            <svg class="w-16 h-16 mx-auto mb-4 text-accent/20" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="8" y="32" width="8" height="24" rx="2"/>
              <rect x="20" y="20" width="8" height="36" rx="2"/>
              <rect x="32" y="28" width="8" height="28" rx="2"/>
              <rect x="44" y="12" width="8" height="44" rx="2"/>
            </svg>
            <div class="text-body">输入股票代码或研究主题，开始投研分析</div>
            <div class="text-label mt-1">也可以直接聊天，例如「你好」或「最近什么值得看」</div>
          </div>
        </div>

        <!-- 消息 -->
        <div v-for="msg in messages" :key="msg.id" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
          <!-- AI 头像 -->
          <div v-if="msg.role !== 'user'" class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shrink-0 text-white text-xs font-bold mt-1 shadow-soft ai-avatar">IR</div>

          <div class="max-w-[85%] min-w-0" :class="msg.role === 'user' ? 'order-1' : ''">
            <!-- 用户消息 -->
            <div v-if="msg.role === 'user'">
              <div class="bg-accent text-white px-4 py-2.5 rounded-2xl rounded-br-md text-body user-bubble relative">{{ msg.content }}</div>
            </div>

            <!-- AI 消息：CHAT -->
            <div v-else-if="msg.type === 'chat'" class="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
              <div class="text-body text-slate-700 leading-relaxed">{{ msg.content }}</div>
            </div>

            <!-- AI 消息：RESEARCH / REFINE -->
            <div v-else-if="msg.type === 'research' || msg.type === 'refine'" class="space-y-3">
              <!-- 行情卡 -->
              <MarketDataCard v-if="msg.quote" :quote="msg.quote" :kline="msg.kline || []" />
              <!-- 财务卡 -->
              <FinancialCard v-if="msg.financial" :financial="msg.financial" />
              <!-- 时间线 -->
              <ResearchTimeline v-if="msg.events && msg.events.length" :events="msg.events" />
              <!-- 报告 -->
              <ReportViewer v-if="msg.report" :content="msg.report" :streaming="msg.streaming" />
            </div>

            <!-- AI 消息：加载中 -->
            <div v-else-if="msg.type === 'loading'" class="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
              <div class="flex items-center gap-2 text-body text-slate-500">
                <span class="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
                {{ msg.content || '思考中…' }}
              </div>
            </div>

            <!-- AI 消息：错误 -->
            <div v-else-if="msg.type === 'error'" class="bg-red-50 border border-red-200 rounded-2xl rounded-bl-md px-4 py-3">
              <div class="text-body text-red-600">{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 底部输入 -->
    <footer class="border-t border-slate-200 bg-white px-4 py-3 shrink-0">
      <div class="max-w-3xl mx-auto">
        <div class="flex items-end gap-2 bg-slate-50 rounded-lg border border-slate-200 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-colors duration-200 px-4 py-2">
          <textarea
            ref="inputBox"
            v-model="input"
            @input="autoResize($event)"
            @keydown.enter.exact.prevent="sendMessage"
            class="flex-1 bg-transparent resize-none text-body text-slate-700 placeholder-slate-400 focus:outline-none leading-relaxed"
            :rows="1"
            placeholder="输入股票代码或研究主题，回车发送..."
          />
          <button
            @click="sendMessage"
            :disabled="!input.trim() || isLoading"
            class="shrink-0 w-9 h-9 rounded-md bg-accent hover:bg-accent/90 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
        </div>
        <p class="text-label text-slate-400 text-center mt-1.5">IRIS 可能会犯错，请核实重要信息</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';
import MarketDataCard from './components/MarketDataCard.vue';
import FinancialCard from './components/FinancialCard.vue';
import ResearchTimeline from './components/ResearchTimeline.vue';
import ReportViewer from './components/ReportViewer.vue';
import { streamChat } from './services/api';

const input = ref('');
const isLoading = ref(false);
const messages = ref([]);
const scrollEl = ref(null);
const inputBox = ref(null);

let msgId = 0;
const newMsg = (role, type, content, extra = {}) => {
  const m = { id: ++msgId, role, type, content, ...extra };
  messages.value.push(m);
  nextTick(scrollToBottom);
  return m;
};

const scrollToBottom = () => {
  const el = scrollEl.value;
  if (el) el.scrollTop = el.scrollHeight;
};

const autoResize = (e) => {
  const el = e?.target || inputBox.value;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};

async function sendMessage() {
  const q = input.value.trim();
  if (!q || isLoading.value) return;

  newMsg('user', 'text', q);
  input.value = '';
  isLoading.value = true;

  // loading 占位
  const loadingMsg = newMsg('assistant', 'loading', '思考中…');

  let currentIntent = null;

  streamChat(
    q,
    'hybrid',
    (ev) => {
      // 意图事件（首事件）
      if (ev.step === 'intent') {
        currentIntent = ev.data?.intent || 'chat';
        loadingMsg.type = currentIntent === 'chat' ? 'chat' : 'loading';
        loadingMsg.content = currentIntent === 'research' ? '正在启动研究…' : currentIntent === 'refine' ? '正在修订报告…' : '思考中…';
        return;
      }

      // 节点事件（研究/修订路径）
      if (ev.step && ev.step !== 'intent' && currentIntent !== 'chat') {
        if (!loadingMsg.events) loadingMsg.events = [];
        const existing = loadingMsg.events.find(e => e.step === ev.step);
        if (existing) {
          existing.status = ev.status || 'running';
          if (ev.data) existing.artifact = ev.data.plan || ev.data.search_results || ev.data.critique || null;
        } else if (ev.step !== 'chat') {
          loadingMsg.events.push({
            step: ev.step,
            status: ev.status || 'running',
            artifact: ev.data?.plan || ev.data?.search_results || ev.data?.critique || null,
          });
        }
      }

      // 报告内容
      if (ev.data?.final_report) {
        loadingMsg.report = ev.data.final_report;
        loadingMsg.type = currentIntent;
      } else if (ev.data?.chat_response) {
        loadingMsg.content = ev.data.chat_response;
        loadingMsg.type = 'chat';
      } else if (ev.data?.token && !ev.data.final) {
        if (currentIntent === 'chat') {
          loadingMsg.content = (loadingMsg.content === '思考中…' ? '' : loadingMsg.content) + ev.data.token;
        } else {
          loadingMsg.streaming = true;
          // 研究路径：token 来自 writer/refiner，积累到 report
          if (!loadingMsg.report) loadingMsg.report = '';
          loadingMsg.report += ev.data.token;
        }
      }

      // 行情数据
      if (ev.data?.quote) loadingMsg.quote = { ...ev.data.quote, data_source: ev.data.data_source };
      if (ev.data?.financial) loadingMsg.financial = { ...ev.data.financial, data_source: ev.data.data_source };
    },
    () => {
      isLoading.value = false;
      loadingMsg.streaming = false;
      if (loadingMsg.events) {
        loadingMsg.events.forEach(e => { if (e.status === 'running') e.status = 'done'; });
      }
      if (loadingMsg.type === 'loading') loadingMsg.type = 'chat';
    },
    (err) => {
      isLoading.value = false;
      loadingMsg.type = 'error';
      loadingMsg.content = err?.message || '请求失败，请重试';
    }
  );
}
</script>

<style scoped>
/* 用户气泡尾：右下角小尖角 */
.user-bubble::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: -5px;
  width: 10px;
  height: 10px;
  background: #4F46E5;
  clip-path: polygon(0 0, 100% 100%, 0 100%);
}

/* AI 头像：微交互 */
.ai-avatar {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.ai-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);
}
</style>