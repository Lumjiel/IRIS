<template>
  <div class="h-screen flex flex-row">
    <!-- ============ 桌面侧边栏（lg 以上常驻） ============ -->
    <div class="hidden lg:block shrink-0">
      <ChatSidebar
        :history="recentHistory"
        @analyze="startPreset"
        @new-thread="handleNewThread"
        @replay="handleReplay"
        @delete-history="handleDeleteHistory"
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
            @delete-history="sidebarOpen = false; handleDeleteHistory($event)"
            @watch-added="toast.success(`已添加自选股 ${$event.name}`)"
            @watch-removed="toast.success('已移出自选股')"
          />
        </div>
      </div>
    </Transition>

    <!-- ============ 主区 ============ -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 顶栏 -->
      <ChatHeader @open-drawer="sidebarOpen = true" />

      <!-- 财经资讯横滚条（顶栏下方通栏，加载失败静默降级） -->
      <NewsTicker class="shrink-0" />

      <!-- 消息列表 -->
      <main ref="scrollEl" class="flex-1 overflow-y-auto">
        <!-- 空状态：功能引导中心 -->
        <EmptyState
          v-if="messages.length === 0"
          :presets="PRESETS"
          :hot-stocks="HOT_STOCKS"
          :hot-source="hotSource"
          :recent-history="recentHistory"
          @preset-click="startPreset"
          @hot-click="startPreset"
          @replay="handleReplay"
        />

        <!-- 消息流 -->
        <div v-else class="max-w-3xl mx-auto py-6 px-4 space-y-4">
          <MessageBubble
            v-for="msg in messages"
            :key="msg.id"
            :msg="msg"
            :is-last-report="isLastReport(msg)"
            :follow-up-value="followUp"
            @copy="handleCopy"
            @download="handleDownload"
            @save="handleSave"
            @update:follow-up-value="followUp = $event"
            @follow-send="handleFollowUpSend"
          />
        </div>
      </main>

      <!-- 底部输入 -->
      <ChatInput
        ref="chatInputRef"
        v-model="input"
        :disabled="isLoading"
        :uploading="uploading"
        @send="handleSend"
      />
    </div>
  </div>

  <!-- Toast 反馈 -->
  <Toast :message="toast.message" :type="toast.type" />
</template>

<script setup>
import { ref, onMounted } from "vue";
import ChatSidebar from "../components/ChatSidebar.vue";
import ChatHeader from "../components/chat/ChatHeader.vue";
import EmptyState from "../components/chat/EmptyState.vue";
import MessageBubble from "../components/chat/MessageBubble.vue";
import ChatInput from "../components/chat/ChatInput.vue";
import NewsTicker from "../components/NewsTicker.vue";
import Toast from "../components/Toast.vue";
import { useChat } from "../composables/useChat";
import { useToast } from "../composables/useToast";
import { useAppStore } from "../stores/app";
import { getHistory, deleteSession } from "../services/history";
import { saveReport, setThreadId, uploadFiles } from "../services/api";
import { getMarketHot } from "../services/finance";

// --- Store ---
const appStore = useAppStore();

// --- 移动端抽屉侧栏 ---
const sidebarOpen = ref(false);

// --- 聊天 & Toast composables ---
const { messages, isLoading, scrollEl, sendMessage, newThread, restoreMessages } = useChat();
const toast = useToast();

// --- 报告追问（FollowUpInput 单例输入） ---
const followUp = ref("");
const isLastReport = (msg) => {
  if (msg.type !== "research" && msg.type !== "refine") return false;
  if (!msg.report || msg.streaming) return false;
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i];
    if (m.role === "assistant" && (m.type === "research" || m.type === "refine") && m.report) {
      return m.id === msg.id;
    }
  }
  return false;
};
const handleFollowUpSend = () => {
  const q = followUp.value.trim();
  if (!q || isLoading.value) return;
  followUp.value = "";
  sendMessage(q, "hybrid");
};

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

// 热门标的：优先后端实时榜单（东财人气榜/涨幅回退），失败用静态兜底
const HOT_FALLBACK = [
  { name: "贵州茅台", code: "600519" },
  { name: "复星医药", code: "600196" },
  { name: "宁德时代", code: "300750" },
  { name: "中国平安", code: "601318" },
  { name: "平安银行", code: "000001" },
];
const HOT_STOCKS = ref(HOT_FALLBACK);
const hotSource = ref("");

const loadHotStocks = async () => {
  try {
    const data = await getMarketHot(6);
    if (data?.items?.length) {
      HOT_STOCKS.value = data.items.map((s) => ({ name: s.name, code: s.code }));
      hotSource.value = data.source || "";
    }
  } catch {
    // 榜单接口不可用时保留静态兜底
  }
};

// --- 近期历史（供侧边栏 + 空状态） ---
const recentHistory = ref([]);
const loadHistory = () => {
  recentHistory.value = getHistory().slice(0, 20);
};

// --- 输入 ---
const input = ref("");
const chatInputRef = ref(null);
const uploading = ref(false);

// --- 发送（支持携带 PDF 附件：先上传入库知识库，再拼接分析提示） ---
const handleSend = async (files) => {
  if (isLoading.value || uploading.value) return;
  let q = input.value.trim();
  if (files && files.length) {
    uploading.value = true;
    try {
      await uploadFiles(files);
      const names = files.map((f) => f.name).join("、");
      const hint = q ? `${q}\n\n` : "";
      q = `${hint}请分析我刚上传的文档：${names}（已入库知识库，请结合文档内容进行研究）`;
    } catch {
      toast.error("上传失败，请确认文件是有效的 PDF");
      uploading.value = false;
      return;
    }
    uploading.value = false;
  }
  if (!q) return;
  input.value = "";
  chatInputRef.value?.clearFiles();
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

/** 删除历史会话（tombstone 防复活，见 services/history.js） */
const handleDeleteHistory = (h) => {
  if (!h?.id) return;
  if (!confirm(`确定删除会话「${h.query || '未命名会话'}」吗？`)) return;
  deleteSession(h.id);
  loadHistory();
  toast.success('会话已删除');
};

/** 新会话 */
const handleNewThread = () => {
  newThread();
  toast.success("已开启新会话");
};

/** 恢复 HistoryView 跳转过来的会话（threadId + 消息） */
const restoreSession = () => {
  try {
    const raw = sessionStorage.getItem("iris_restore_session");
    if (!raw) return;
    sessionStorage.removeItem("iris_restore_session");
    const s = JSON.parse(raw);
    if (s?.threadId) setThreadId(s.threadId);
    if (s?.messages?.length) {
      restoreMessages(s.messages);
      toast.success(`已恢复会话：${s.query || ""}`);
    }
  } catch {
    // 恢复失败静默，不影响正常使用
  }
};

// --- 生命周期 ---
onMounted(() => {
  loadHistory();
  loadHotStocks();
  restoreSession();
});

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
