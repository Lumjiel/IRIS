<template>
  <div class="h-screen flex flex-col">
    <!-- 顶部搜索栏 -->
    <header class="border-b border-slate-200 bg-white px-6 py-3 flex items-center gap-4 shrink-0">
      <h1 class="text-base font-semibold text-slate-900">IRIS 投研助手</h1>
      <div class="flex-1 max-w-xl flex gap-2">
        <input
          v-model="query"
          type="text"
          placeholder="输入股票代码或名称，如 600519 / 贵州茅台"
          class="flex-1 px-3 py-2 rounded-md border border-slate-200 text-body focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/10"
          @keyup.enter="startResearch"
        />
        <button
          @click="startResearch"
          :disabled="isRunning || !query.trim()"
          class="px-4 py-2 rounded-md bg-accent text-white text-body font-medium hover:bg-accent/90 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <span v-if="isRunning">分析中…</span>
          <span v-else>开始分析</span>
        </button>
      </div>
      <!-- 示例 -->
      <div class="flex gap-1.5">
        <button
          v-for="ex in examples"
          :key="ex.code"
          @click="query = ex.code"
          class="px-2.5 py-1 rounded-md text-label text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors border border-slate-200"
        >
          {{ ex.name }}
        </button>
      </div>
    </header>

    <!-- 主体 -->
    <div class="flex-1 flex overflow-hidden">
      <!-- 左栏：数据面板 -->
      <aside class="w-80 border-r border-slate-200 bg-slate-50 p-4 space-y-4 overflow-y-auto shrink-0">
        <MarketDataCard v-if="quote" :quote="quote" :kline="kline" />
        <FinancialCard v-if="financial" :financial="financial" />
        <ResearchTimeline v-if="timelineEvents.length" :events="timelineEvents" />
      </aside>

      <!-- 右区：报告 -->
      <main class="flex-1 overflow-y-auto p-6 bg-white">
        <!-- 空状态 -->
        <div v-if="!report && !isRunning" class="h-full flex items-center justify-center text-slate-400">
          <div class="text-center">
            <div class="text-4xl mb-3">📊</div>
            <div class="text-body">输入股票代码，开始投研分析</div>
            <div class="text-label mt-1">数据来源：AKShare 东方财富（延时 15 分钟）</div>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-else-if="isRunning && !report" class="flex items-center justify-center h-full">
          <div class="text-center">
            <div class="text-3xl mb-3 animate-pulse">⏳</div>
            <div class="text-body text-slate-500">正在分析 {{ query }}…</div>
          </div>
        </div>

        <!-- 报告 -->
        <div v-else class="max-w-4xl mx-auto">
          <ReportViewer
            :content="report"
            :title="reportTitle"
            :subtitle="reportSubtitle"
            :streaming="isRunning"
          />
        </div>
      </main>
    </div>

    <!-- 底部操作栏 -->
    <ActionBar
      :report="report"
      :sources="dataSources"
      @copy="copyReport"
      @download="downloadReport"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import MarketDataCard from './components/MarketDataCard.vue';
import FinancialCard from './components/FinancialCard.vue';
import ResearchTimeline from './components/ResearchTimeline.vue';
import ReportViewer from './components/ReportViewer.vue';
import ActionBar from './components/ActionBar.vue';
import { streamChat } from './services/api';

const query = ref('600519');
const isRunning = ref(false);
const report = ref('');
const quote = ref(null);
const financial = ref(null);
const kline = ref([]);
const dataSources = ref([]);
const timelineEvents = ref([]);
const error = ref('');

const examples = [
  { code: '600196', name: '复星医药' },
  { code: '000001', name: '平安银行' },
  { code: '600519', name: '贵州茅台' },
  { code: '000333', name: '美的集团' },
  { code: '601318', name: '中国平安' },
];

const reportTitle = computed(() => {
  if (!quote.value?.name && !query.value) return '';
  return `${quote.value?.name || query.value}（${extractCode(query.value)}）投资分析报告`;
});
const reportSubtitle = computed(() => {
  const parts = [];
  if (quote.value?.data_source) parts.push(quote.value.data_source);
  if (financial.value?.data_source) parts.push(financial.value.data_source);
  return parts.join(' · ');
});

function extractCode(q) {
  if (!q) return '';
  const m = q.match(/(\d{6})/);
  return m ? m[1] : q;
}

async function fetchStockData(code) {
  const extract = async (url, key) => {
    try {
      const r = await fetch(url);
      return r.ok ? await r.json() : null;
    } catch { return null; }
  };
  const [q, f] = await Promise.all([
    extract(`/api/stock/${code}/quote`),
    extract(`/api/stock/${code}/financial`),
  ]);
  if (q) quote.value = { ...q.quote, data_source: q.data_source };
  if (f) financial.value = { ...f.indicators, data_source: f.data_source };
}

async function startResearch() {
  if (!query.value.trim() || isRunning.value) return;

  isRunning.value = true;
  report.value = '';
  quote.value = null;
  financial.value = null;
  kline.value = [];
  dataSources.value = [];
  timelineEvents.value = [];
  error.value = '';

  const code = extractCode(query.value);

  // 先拉行情 + 财务（并行）
  await fetchStockData(code);

  // SSE 研究流
  streamChat(
    `分析${query.value}的投资价值`,
    'hybrid',
    (ev) => {
      // 节点事件
      if (ev.step) {
        const cur = timelineEvents.value.find(e => e.step === ev.step);
        if (cur) {
          cur.status = ev.status || 'running';
          if (ev.data) cur.artifact = ev.data.plan || ev.data.search_results || ev.data.critique || null;
        } else {
          timelineEvents.value.push({
            step: ev.step,
            status: ev.status || 'running',
            artifact: ev.data?.plan || ev.data?.search_results || ev.data?.critique || null,
          });
        }
      }
      // 报告流
      if (ev.data?.final_report) {
        report.value = ev.data.final_report;
      } else if (ev.data?.token && !ev.data.final) {
        report.value += ev.data.token;
      }
    },
    () => {
      isRunning.value = false;
      // 标记所有已完成节点
      timelineEvents.value.forEach(e => { if (e.status === 'running') e.status = 'done'; });
    },
    (err) => {
      isRunning.value = false;
      error.value = err.message;
    }
  );
}

async function copyReport() {
  try { await navigator.clipboard.writeText(report.value); } catch {}
}

function downloadReport() {
  const blob = new Blob([report.value], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `投研报告_${query.value}_${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>