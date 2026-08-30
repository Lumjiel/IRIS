<template>
  <div class="h-screen flex flex-row">
    <!-- ============ 桌面侧边栏（lg 以上常驻） ============ -->
    <div class="hidden lg:block shrink-0">
      <ChatSidebar
        :history="recentHistory"
        @analyze="startPreset"
        @new-thread="handleNewThread"
        @replay="handleReplay"
        @watch-added="toast.success(`已添加自选股 ${$event.name}`)"
        @watch-removed="toast.success('已移出自选股')"
      />
    </div>

    <!-- ============ 移动端抽屉侧栏（lg 以下） ============ -->
    <Transition name="drawer">
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-40 lg:hidden bg-slate-900/40 backdrop-blur-sm"
        @click.self="sidebarOpen = false"
      >
        <div class="absolute inset-y-0 left-0 shadow-xl">
          <ChatSidebar
            :history="recentHistory"
            @analyze="sidebarOpen = false; startPreset($event)"
            @new-thread="sidebarOpen = false; handleNewThread()"
            @replay="sidebarOpen = false; handleReplay($event)"
            @watch-added="toast.success(`已添加自选股 ${$event.name}`)"
            @watch-removed="toast.success('已移出自选股')"
          />
        </div>
      </div>
    </Transition>

    <!-- ============ 主区 ============ -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 顶栏 -->
      <header class="h-12 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 flex items-center justify-between gap-3 shrink-0">
        <div class="flex items-center gap-3 min-w-0">
          <!-- 移动端：打开抽屉侧栏 -->
          <button
            class="lg:hidden p-1.5 -ml-1.5 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            aria-label="打开侧栏"
            @click="sidebarOpen = true"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
          <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-soft shrink-0">IR</div>
          <span class="text-sm font-semibold text-slate-900 dark:text-slate-100 shrink-0">IRIS 投研助手</span>
          <span class="text-label text-slate-400 dark:text-slate-500 hidden lg:inline truncate">LangGraph 多智能体协同 · AKShare 真实数据</span>
        </div>
      </header>

      <!-- 财经资讯横滚条（顶栏下方通栏，加载失败静默降级） -->
      <NewsTicker class="shrink-0" />

      <!-- 消息列表 -->
      <main ref="scrollEl" class="flex-1 overflow-y-auto">
        <!-- ============ 空状态：功能引导中心 ============ -->
        <div v-if="messages.length === 0" class="min-h-full flex items-center justify-center py-10 px-4">
          <div class="w-full max-w-2xl">
            <!-- 品牌区 -->
            <div class="text-center mb-8">
              <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-soft">
                <svg class="w-9 h-9 text-white" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3">
                  <rect x="8" y="34" width="8" height="22" rx="2"/>
                  <rect x="20" y="22" width="8" height="34" rx="2"/>
                  <rect x="32" y="30" width="8" height="26" rx="2"/>
                  <rect x="44" y="14" width="8" height="42" rx="2"/>
                </svg>
              </div>
              <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">今天想研究点什么？</h1>
              <p class="text-label text-slate-500 dark:text-slate-400 mt-2">输入股票代码或主题，IRIS 的多智能体团队将为你完成「检索 → 分析 → 撰写」全流程</p>
            </div>

            <!-- 功能卡片 -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
              <button
                v-for="p in PRESETS"
                :key="p.title"
                @click="startPreset(p.prompt)"
                class="text-left p-4 rounded-card border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-accent/60 hover:shadow-soft hover:-translate-y-0.5 transition-all duration-200 group"
              >
                <div class="flex items-start gap-3">
                  <div class="w-9 h-9 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center text-accent shrink-0 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/20 transition-colors" v-html="p.icon"></div>
                  <div class="min-w-0">
                    <div class="text-body font-semibold text-slate-900 dark:text-slate-100 group-hover:text-accent transition-colors">{{ p.title }}</div>
                    <div class="text-label text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">{{ p.desc }}</div>
                  </div>
                </div>
              </button>
            </div>

            <!-- 热门标的 -->
            <div class="text-center">
              <div class="text-label text-slate-400 dark:text-slate-500 mb-2.5">热门标的</div>
              <div class="flex flex-wrap justify-center gap-2">
                <button
                  v-for="s in HOT_STOCKS"
                  :key="s.code"
                  @click="startPreset(`分析${s.name}（${s.code}）的投资价值`)"
                  class="px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-label text-slate-600 dark:text-slate-300 hover:border-accent/60 hover:text-accent transition-colors"
                >
                  {{ s.name }} · {{ s.code }}
                </button>
              </div>
            </div>

            <!-- 最近研究（有历史时） -->
            <div v-if="recentHistory.length" class="mt-8">
              <div class="text-label text-slate-400 dark:text-slate-500 mb-2.5 text-center">最近研究</div>
              <div class="space-y-1.5">
                <button
                  v-for="h in recentHistory"
                  :key="h.id"
                  @click="handleReplay(h)"
                  class="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-left"
                >
                  <span class="text-body text-slate-700 dark:text-slate-300 truncate">{{ h.query || '未命名会话' }}</span>
                  <span class="text-label text-slate-400 shrink-0 ml-3">{{ formatTime(h.timestamp) }}</span>
                </button>
              </div>
            </div>

            <p class="text-center text-label text-slate-400 dark:text-slate-500 mt-8">
              IRIS 由多个 AI 智能体协同工作 · 报告仅供参考，不构成投资建议
            </p>
          </div>
        </div>

        <!-- ============ 消息流 ============ -->
        <div v-else class="max-w-3xl mx-auto py-6 px-4 space-y-4">
          <div v-for="msg in messages" :key="msg.id" class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
            <!-- AI 头像 -->
            <div v-if="msg.role !== 'user'" class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shrink-0 text-white text-xs font-bold mt-1 shadow-soft ai-avatar">IR</div>

            <div class="max-w-[85%] min-w-0 md:max-w-[75%]" :class="msg.role === 'user' ? 'order-1' : ''">
              <!-- 用户消息 -->
              <div v-if="msg.role === 'user'">
                <div class="bg-accent text-white px-4 py-2.5 rounded-2xl rounded-br-md text-body user-bubble relative dark:bg-indigo-600">{{ msg.content }}</div>
              </div>

              <!-- AI 消息：CHAT -->
              <div v-else-if="msg.type === 'chat'" class="space-y-2">
                <div class="bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
                  <div class="text-body text-slate-700 dark:text-slate-300 leading-relaxed">{{ msg.content }}</div>
                </div>
                <!-- 闲聊路径也展示过程（记忆注入 + 对话节点） -->
                <ProcessBar
                  v-if="msg.events && msg.events.length"
                  :events="msg.events"
                  :intent="msg.intent"
                  :done="true"
                />
              </div>

              <!-- AI 消息：RESEARCH / REFINE -->
              <div v-else-if="msg.type === 'research' || msg.type === 'refine'" class="space-y-3">
                <MarketDataCard v-if="msg.quote" :quote="msg.quote" :kline="msg.kline || []" />
                <FinancialCard v-if="msg.financial" :financial="msg.financial" />
                <ProcessBar
                  :events="msg.events || []"
                  :intent="msg.intent"
                  :done="!msg.streaming"
                  :data-source="msg.quote?.data_source || ''"
                />
                <!-- 研报正文（流式渲染） -->
                <ReportViewer
                  v-if="msg.report"
                  :content="msg.report"
                  :streaming="!!msg.streaming"
                />
                <ActionBar
                  v-if="msg.report && !msg.streaming && msg.type !== 'loading'"
                  :report="msg.report"
                  :sources="msg.quote?.data_source ? [msg.quote.data_source] : []"
                  @copy="handleCopy(msg)"
                  @download="handleDownload(msg)"
                  @save="handleSave(msg)"
                />
              </div>

              <!-- AI 消息：加载中 -->
              <div v-else-if="msg.type === 'loading'" class="bg-white border border-slate-200 dark:bg-slate-800 dark:border-slate-700 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
                <div class="flex items-center gap-2 text-body text-slate-500 dark:text-slate-400">
                  <span class="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
                  {{ msg.content || '思考中…' }}
                </div>
                <!-- 骨架屏：研究流程耗时数分钟，shimmer 块降低等待焦虑 -->
                <!-- 研究流程节点时间线：intent 为 research/refine 时 type 仍是 loading，
                     必须在 loading 分支内渲染，否则整个流程期间看不到任何 agent 进度 -->
                <ProcessBar
                  :events="msg.events || []"
                  :intent="msg.intent"
                  :done="false"
                  class="mt-3"
                />
                <!-- 骨架屏：研究流程耗时数分钟，shimmer 块降低等待焦虑（有时间线时隐藏） -->
                <div v-if="!(msg.events && msg.events.length)" class="mt-3 space-y-2.5" aria-hidden="true">
                  <div class="skeleton-line h-3 rounded bg-slate-100 dark:bg-slate-700/60 w-full"></div>
                  <div class="skeleton-line h-3 rounded bg-slate-100 dark:bg-slate-700/60 w-5/6"></div>
                  <div class="skeleton-line h-14 rounded-lg bg-slate-100 dark:bg-slate-700/60 w-full"></div>
                </div>
              </div>

              <!-- AI 消息：错误 -->
              <div v-else-if="msg.type === 'error'" class="bg-red-50 border border-red-200 dark:bg-red-900/20 dark:border-red-800 rounded-2xl rounded-bl-md px-4 py-3">
                <div class="text-body text-red-600 dark:text-red-400">{{ msg.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <!-- 底部输入 -->
      <footer class="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3 shrink-0">
        <div class="max-w-3xl mx-auto">
          <div class="flex items-end gap-2 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-colors duration-200 px-4 py-2">
            <textarea
              ref="inputBox"
              v-model="input"
              @input="autoResize($event)"
              @keydown.enter.exact.prevent="handleSend"
              class="flex-1 bg-transparent resize-none text-body text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none leading-relaxed"
              :rows="1"
              placeholder="输入股票代码或研究主题，回车发送..."
            />
            <button
              @click="handleSend"
              :disabled="!input.trim() || isLoading"
              class="shrink-0 w-10 h-10 rounded-md bg-accent hover:bg-accent/90 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
          <p class="text-label text-slate-400 dark:text-slate-500 text-center mt-1.5">IRIS 可能会犯错，请核实重要信息</p>
        </div>
      </footer>
    </div>
  </div>

  <!-- Toast 反馈 -->
  <Toast :message="toast.message" :type="toast.type" />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import ChatSidebar from "../components/ChatSidebar.vue";
import MarketDataCard from "../components/MarketDataCard.vue";
import FinancialCard from "../components/FinancialCard.vue";
import ProcessBar from "../components/ProcessBar.vue";
import NewsTicker from "../components/NewsTicker.vue";
import ReportViewer from "../components/ReportViewer.vue";
import ActionBar from "../components/ActionBar.vue";
import Toast from "../components/Toast.vue";
import { useChat } from "../composables/useChat";
import { useToast } from "../composables/useToast";
import { useAppStore } from "../stores/app";
import { getHistory } from "../services/history";
import { saveReport } from "../services/api";

// --- Store ---
const appStore = useAppStore();

// --- 移动端抽屉侧栏 ---
const sidebarOpen = ref(false);

// --- 聊天 & Toast composables ---
const { messages, isLoading, scrollEl, sendMessage, newThread } = useChat();
const toast = useToast();

// --- 空状态引导数据 ---
const PRESETS = [
  {
    title: "个股深度研报",
    desc: "行情 / 财务 / 新闻，生成六章节完整报告",
    prompt: "分析复星医药（600196）的投资价值，生成深度研报",
    icon: `<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
  },
  {
    title: "智能问答",
    desc: "和市场数据直接对话，随时追问细节",
    prompt: "今天 A 股市场整体表现如何？有哪些热点板块？",
    icon: `<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
  },
  {
    title: "行业纵览",
    desc: "行业板块数据整理与竞争格局分析",
    prompt: "分析新能源汽车行业现状与投资机会",
    icon: `<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18"/><path d="M5 21V7l8-4v18"/><path d="M19 21V11l-6-4"/></svg>`,
  },
  {
    title: "热点速递",
    desc: "个股新闻与公告聚合，捕捉市场动向",
    prompt: "最近一周有哪些值得关注的财经热点事件？",
    icon: `<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  },
];

const HOT_STOCKS = [
  { name: "贵州茅台", code: "600519" },
  { name: "复星医药", code: "600196" },
  { name: "宁德时代", code: "300750" },
  { name: "中国平安", code: "601318" },
  { name: "平安银行", code: "000001" },
];

// --- 近期历史（供侧边栏 + 空状态） ---
const recentHistory = ref([]);
const loadHistory = () => {
  recentHistory.value = getHistory().slice(0, 20);
};

// --- 输入 ---
const input = ref("");
const inputBox = ref(null);
const autoResize = (e) => {
  const el = e?.target || inputBox.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
};

// --- 发送 ---
const handleSend = () => {
  const q = input.value.trim();
  if (!q || isLoading.value) return;
  input.value = "";
  sendMessage(q, "hybrid");
};

/** 点击预设卡片 / 热门标的 / 自选股 → 直接发起分析 */
const startPreset = (prompt) => {
  if (isLoading.value) return;
  sendMessage(prompt, "hybrid");
};

/** 回放历史会话（重新跑该 query） */
const handleReplay = (h) => {
  if (isLoading.value || !h?.query) return;
  startPreset(h.query);
};

/** 新会话 */
const handleNewThread = () => {
  newThread();
  toast.success("已开启新会话");
};

// --- 生命周期 ---
onMounted(() => {
  loadHistory();
});

// --- 时间格式化 ---
const formatTime = (ts) => {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
  return d.toLocaleDateString();
};

// --- ActionBar 操作 ---
const handleCopy = (msg) => {
  if (!msg?.report) return;
  navigator.clipboard.writeText(msg.report)
    .then(() => toast.success("已复制到剪贴板"))
    .catch(() => toast.error("复制失败"));
};
const handleDownload = (msg) => {
  if (!msg?.report) return;
  const blob = new Blob([msg.report], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ts = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const code = msg.quote?.code || msg.quote?.stock_code || "report";
  a.download = `投研报告_${code}_${ts}.md`;
  a.click();
  URL.revokeObjectURL(url);
  toast.success("报告已下载");
};
const handleSave = async (msg) => {
  if (!msg?.report) return;
  try {
    // 文件名用股票代码或通用名，服务端会做字符过滤 + 日期前缀
    const name = msg.quote?.stock_code ? `分析${msg.quote.stock_code}` : "投研报告";
    await saveReport(name, msg.report);
    toast.success("报告已保存到创作目录");
  } catch {
    toast.error("保存失败，请稍后重试");
  }
};
</script>

<style scoped>
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
.ai-avatar {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.ai-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);
}

/* 移动端抽屉：滑入滑出 */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.2s ease;
}
.drawer-enter-active > div,
.drawer-leave-active > div {
  transition: transform 0.25s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from > div,
.drawer-leave-to > div {
  transform: translateX(-100%);
}
</style>