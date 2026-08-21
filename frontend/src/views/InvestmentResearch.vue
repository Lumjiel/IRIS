<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- 顶部导航 -->
    <div class="bg-white border-b px-6 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="text-xl font-bold text-blue-600">📊 IRIS 投研分析</span>
        <span class="text-xs text-gray-400">基于 LangGraph 多智能体协同</span>
      </div>
      <div class="text-xs text-gray-400">
        数据来源：AKShare 东方财富（延时 15 分钟）
      </div>
    </div>

    <div class="flex-1 flex overflow-hidden">
      <!-- 左侧输入区 -->
      <div class="w-80 bg-white border-r p-4 flex flex-col gap-4 overflow-y-auto">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">股票代码 / 名称</label>
          <input
            v-model="stockCode"
            type="text"
            placeholder="如: 600196 或 复星医药"
            class="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            @keyup.enter="startResearch"
          />
        </div>

        <button
          @click="startResearch"
          :disabled="isLoading || !stockCode.trim()"
          class="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
        >
          <span v-if="isLoading">分析中...</span>
          <span v-else>开始分析</span>
        </button>

        <!-- 快捷示例 -->
        <div>
          <div class="text-xs text-gray-500 mb-2">快捷示例</div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="example in examples"
              :key="example.code"
              @click="stockCode = example.code"
              class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition"
            >
              {{ example.name }}
            </button>
          </div>
        </div>

        <!-- 实时数据卡片 -->
        <div v-if="stockData.stock_info" class="border rounded-lg p-3 bg-blue-50">
          <div class="text-xs font-medium text-blue-700 mb-2">实时行情</div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span class="text-gray-500">最新价</span>
              <div class="font-medium" :class="stockData.quote?.涨跌幅?.startsWith('+') ? 'text-red-600' : 'text-green-600'">
                {{ stockData.quote?.最新价 || '-' }}
              </div>
            </div>
            <div>
              <span class="text-gray-500">涨跌幅</span>
              <div class="font-medium" :class="stockData.quote?.涨跌幅?.startsWith('+') ? 'text-red-600' : 'text-green-600'">
                {{ stockData.quote?.涨跌幅 || '-' }}
              </div>
            </div>
            <div>
              <span class="text-gray-500">换手率</span>
              <div class="font-medium">{{ stockData.quote?.换手率 || '-' }}</div>
            </div>
            <div>
              <span class="text-gray-500">总市值</span>
              <div class="font-medium">{{ stockData.quote?.总市值 || '-' }}</div>
            </div>
          </div>
        </div>

        <!-- 执行时间线 -->
        <div v-if="events.length > 0">
          <div class="text-xs text-gray-500 mb-2">执行时间线</div>
          <div class="space-y-1">
            <div
              v-for="(event, idx) in events"
              :key="idx"
              class="flex items-center gap-2 text-xs"
            >
              <span :class="event.done ? 'text-green-500' : 'text-blue-500'">
                {{ event.done ? '✅' : '⏳' }}
              </span>
              <span class="text-gray-600">{{ event.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧输出区 -->
      <div class="flex-1 flex flex-col overflow-hidden">
        <!-- 报告内容 -->
        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="!report && !isLoading" class="h-full flex items-center justify-center text-gray-400">
            <div class="text-center">
              <div class="text-4xl mb-3">📊</div>
              <div>输入股票代码，开始投研分析</div>
            </div>
          </div>

          <div v-else-if="isLoading && !report" class="flex items-center justify-center h-full">
            <div class="text-center">
              <div class="animate-spin text-3xl mb-3">⏳</div>
              <div class="text-gray-500">正在分析 {{ stockCode }}...</div>
            </div>
          </div>

          <div v-else class="max-w-4xl mx-auto">
            <!-- 渲染 Markdown 报告 -->
            <div class="prose prose-sm max-w-none" v-html="renderedReport"></div>
          </div>
        </div>

        <!-- 底部操作栏 -->
        <div v-if="report" class="border-t bg-white px-6 py-3 flex items-center justify-between">
          <div class="text-xs text-gray-400">
            数据来源：{{ dataSources.join('、') || '—' }}
          </div>
          <div class="flex gap-2">
            <button
              @click="copyReport"
              class="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition"
            >
              📋 复制
            </button>
            <button
              @click="downloadReport"
              class="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded transition"
            >
              💾 下载
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue';
import { renderMarkdown } from '../utils/markdown';
import { streamResearch, extractStockCode } from '../services/finance';
const stockCode = ref('600196');
const isLoading = ref(false);
const report = ref('');
const events = ref([]);
const stockData = ref({});
const dataSources = ref([]);
const abortController = ref(null);

const examples = [
  { code: '600196', name: '复星医药' },
  { code: '000001', name: '平安银行' },
  { code: '600519', name: '贵州茅台' },
  { code: '000333', name: '美的集团' },
  { code: '601318', name: '中国平安' },
];

const renderedReport = computed(() => {
  if (!report.value) return '';
  return renderMarkdown(report.value);
});

async function startResearch() {
  if (!stockCode.value.trim() || isLoading.value) return;

  isLoading.value = true;
  report.value = '';
  events.value = [];
  stockData.value = {};
  dataSources.value = [];

  const code = extractStockCode(stockCode.value) || stockCode.value;

  // 模拟时间线事件
  const timeline = [
    { name: '意图识别', done: false },
    { name: '搜索规划', done: false },
    { name: '网络调研', done: false },
    { name: '数据拉取', done: false },
    { name: '报告撰写', done: false },
    { name: '质量审查', done: false },
  ];
  events.value = [...timeline];

  // 逐步标记完成（模拟）
  let step = 0;
  const advanceStep = () => {
    if (step < events.value.length) {
      events.value[step].done = true;
      step++;
    }
  };

  abortController.value = new AbortController();

  try {
    // 先获取实时数据卡片
    try {
      const [infoRes, finRes, quoteRes] = await Promise.all([
        fetch(`/api/stock/${code}/info`).then(r => r.ok ? r.json() : null),
        fetch(`/api/stock/${code}/financial`).then(r => r.ok ? r.json() : null),
        fetch(`/api/stock/${code}/quote`).then(r => r.ok ? r.json() : null),
      ]);
      stockData.value = {
        stock_info: infoRes?.info,
        indicators: finRes?.indicators,
        quote: quoteRes?.quote,
      };
      if (infoRes?.data_source) dataSources.value.push(infoRes.data_source);
      advanceStep(); // 数据拉取
    } catch (e) {
      console.warn('实时数据获取失败', e);
    }

    advanceStep(); // 网络调研
    advanceStep(); // 搜索规划
    advanceStep(); // 意图识别

    // 流式获取报告
    await streamResearch(
      `分析${stockCode.value}的投资价值`,
      {
        onData: (data) => {
          if (data.step) {
            // 节点事件
            const existing = events.value.find(e => e.name === data.step);
            if (existing) existing.done = true;
          }
          if (data.content) {
            report.value += data.content;
          }
        },
        onDone: () => {
          isLoading.value = false;
          // 标记所有事件完成
          events.value.forEach(e => e.done = true);
        },
        onError: (err) => {
          if (err.name !== 'AbortError') {
            report.value += `\n\n[错误: ${err.message}]`;
          }
          isLoading.value = false;
        },
      },
      abortController.value.signal
    );
  } catch (e) {
    if (e.name !== 'AbortError') {
      report.value += `\n\n[错误: ${e.message}]`;
    }
    isLoading.value = false;
  }
}

function copyReport() {
  navigator.clipboard.writeText(report.value);
}

function downloadReport() {
  const blob = new Blob([report.value], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `投研报告_${stockCode.value}_${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

onUnmounted(() => {
  if (abortController.value) {
    abortController.value.abort();
  }
});
</script>

<style scoped>
.prose :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.875rem;
}
.prose :deep(th),
.prose :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.5rem 0.75rem;
  text-align: left;
}
.prose :deep(th) {
  background-color: #f9fafb;
  font-weight: 600;
}
.prose :deep(h2) {
  font-size: 1.25rem;
  font-weight: 700;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #3b82f6;
}
.prose :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}
.prose :deep(blockquote) {
  border-left: 4px solid #f59e0b;
  background-color: #fffbeb;
  padding: 0.75rem 1rem;
  margin: 1rem 0;
  border-radius: 0 0.375rem 0.375rem 0;
}
</style>
