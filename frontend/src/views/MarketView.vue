<template>
  <div class="h-screen flex flex-col bg-slate-50 dark:bg-slate-900">
    <!-- 顶栏 -->
    <header class="sticky top-0 z-20 border-b border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-800/90 backdrop-blur">
      <div class="max-w-2xl mx-auto px-3 h-12 flex items-center gap-2">
        <router-link
          to="/"
          class="p-1.5 -ml-1.5 rounded-md text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors"
          aria-label="返回对话"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </router-link>
        <h1 class="text-body font-medium text-slate-900 dark:text-slate-100">行情</h1>
        <span v-if="tradingNow" class="flex items-center gap-1 text-label text-slate-500 dark:text-slate-400 ml-auto">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"/>实时
        </span>
        <span v-else class="text-label text-slate-400 ml-auto">已收盘</span>
      </div>
    </header>

    <main ref="scrollEl" class="flex-1 overflow-y-auto">
      <div class="max-w-2xl mx-auto px-3 py-3 space-y-4 pb-8">
        <!-- 指数横滑条 -->
        <div v-if="indexes.length" class="flex gap-2 overflow-x-auto scrollbar-none -mx-3 px-3 pb-1">
          <div
            v-for="idx in indexes"
            :key="idx.code"
            class="card shrink-0 px-3.5 py-2 min-w-[9rem]"
          >
            <div class="text-label text-slate-500 dark:text-slate-400">{{ idx.name }}</div>
            <div class="num text-data-lg mt-0.5" :class="changeInfo(idx).colorClass">
              {{ formatPrice(idx['最新价']) }}
            </div>
            <div class="num text-label" :class="changeInfo(idx).colorClass">
              {{ changeInfo(idx).display }}
            </div>
          </div>
        </div>

        <!-- 自选股 -->
        <section>
          <div class="flex items-center justify-between mb-2">
            <h2 class="text-label text-slate-500 dark:text-slate-400">自选股</h2>
            <button
              @click="refresh(true)"
              class="text-label text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors flex items-center gap-1"
              :disabled="loading"
            >
              <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-2.64-6.36M21 3v6h-6"/></svg>
              刷新
            </button>
          </div>

          <!-- 空状态：快捷添加 -->
          <div v-if="watchlist.list.length === 0" class="card p-4 text-center space-y-3">
            <p class="text-body text-slate-500 dark:text-slate-400">还没有自选股，点一个试试：</p>
            <div class="flex flex-wrap justify-center gap-2">
              <button
                v-for="s in PRESETS"
                :key="s.code"
                @click="addPreset(s)"
                class="px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-600 text-caption text-slate-600 dark:text-slate-300 hover:border-slate-400 dark:hover:border-slate-400 transition-colors"
              >
                + {{ s.name }} {{ s.code }}
              </button>
            </div>
          </div>

          <!-- 个股卡片列表：移动单列 / 桌面双列 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
            <button
              v-for="s in stocks"
              :key="s.stock_code"
              @click="toggleExpand(s.stock_code)"
              class="card p-3.5 text-left w-full hover:shadow-md active:scale-[0.99] transition-all"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0">
                  <div class="text-body font-medium text-slate-900 dark:text-slate-100 truncate">
                    {{ s.name || s.stock_code }}
                  </div>
                  <div class="text-label text-slate-400 num">{{ s.stock_code }}</div>
                </div>
                <span
                  class="shrink-0 p-1 rounded-md text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                  role="button"
                  aria-label="移除自选"
                  @click.stop="removeStock(s.stock_code)"
                >
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </span>
              </div>
              <div class="flex items-baseline justify-between mt-2">
                <span class="num text-data-xl text-slate-900 dark:text-slate-50">{{ formatPrice(s['最新价']) }}</span>
                <span class="num text-body font-medium px-2 py-0.5 rounded-md" :class="badgeClass(s)">
                  {{ changeInfo(s).display }}
                </span>
              </div>

              <!-- 展开明细 -->
              <div v-if="expanded === s.stock_code" class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                <div class="grid grid-cols-2 gap-x-3 gap-y-2 text-caption">
                  <div v-for="field in DETAIL_FIELDS" :key="field.key">
                    <TermTip :term="field.key" />
                    <div class="num text-body text-slate-900 dark:text-slate-100 mt-0.5">
                      {{ field.format === 'big' ? formatBigInt(s[field.label]) : formatPrice(s[field.label]) }}
                    </div>
                  </div>
                </div>
              </div>
            </button>
          </div>

          <!-- 添加输入 -->
          <form @submit.prevent="addByInput" class="mt-2 flex gap-2">
            <input
              v-model="inputText"
              placeholder="输入代码添加，如 600519 或 600519 贵州茅台"
              class="flex-1 min-w-0 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-body text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400"
            />
            <button
              type="submit"
              class="shrink-0 px-4 py-2 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 text-body font-medium hover:opacity-85 active:scale-95 transition-all"
            >
              添加
            </button>
          </form>
          <p v-if="inputError" class="text-caption text-red-500 mt-1.5">{{ inputError }}</p>
        </section>

        <!-- 错误提示（fail-open：部分失败不遮蔽正常数据） -->
        <div v-if="errors.length" class="card p-3 border-amber-300 dark:border-amber-700">
          <div class="text-caption text-amber-600 dark:text-amber-400">
            {{ errors.length }} 只股票获取失败：
            <span class="num">{{ errors.map(e => e.code).join('、') }}</span>
          </div>
        </div>

        <!-- 免责声明 -->
        <footer class="pt-2 pb-4 text-center space-y-1">
          <p class="text-caption text-slate-400">
            数据来源：<template v-for="(src, i) in dataSources" :key="src">{{ src }}<span v-if="i < dataSources.length - 1"> / </span></template>
            <template v-if="updatedAt"> · 更新于 {{ updatedTimeText }}</template>
          </p>
          <p class="text-caption text-slate-400">仅供学习参考，不构成投资建议</p>
        </footer>
      </div>
    </main>
  </div>
</template>

<script setup>
/**
 * 移动端优先行情页（桌面端 max-w-2xl 居中双列）。
 *
 * 工程决策（面试可讲）：
 * - 批量快照轮询而非逐股请求：一次 /api/market/snapshot 拉全部，省 API 配额
 * - 交易时段感知：收盘后停止轮询，仅加载时取一次最后快照
 * - fail-open：部分股票失败只显示错误条，不影响其余数据渲染
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { getMarketSnapshot } from "../services/finance";
import { useWatchlist } from "../composables/useWatchlist";
import { parseChange, formatPrice, formatBigInt } from "../utils/format";
import TermTip from "../components/TermTip.vue";

const POLL_MS = 15_000;

/** 预置示例股（首次进入空列表时一键添加） */
const PRESETS = [
  { code: "600519", name: "贵州茅台" },
  { code: "300750", name: "宁德时代" },
  { code: "000001", name: "平安银行" },
  { code: "600196", name: "复星医药" },
];

const DETAIL_FIELDS = [
  { key: "今开", label: "今开", format: "price" },
  { key: "最高", label: "最高", format: "price" },
  { key: "最低", label: "最低", format: "price" },
  { key: "昨收", label: "昨收", format: "price" },
  { key: "成交额", label: "成交额", format: "big" },
  { key: "涨跌幅", label: "涨跌幅", format: "price" },
];

const watchlist = useWatchlist();
const indexes = ref([]);
const stocks = ref([]);
const errors = ref([]);
const updatedAt = ref(0);
const loading = ref(false);
const expanded = ref("");
const inputText = ref("");
const inputError = ref("");
let timer = null;

/** A 股交易时段（周一至周五 9:15-11:35 / 12:55-15:05，含缓冲） */
function isTradingTime(d = new Date()) {
  const day = d.getDay();
  if (day === 0 || day === 6) return false;
  const m = d.getHours() * 60 + d.getMinutes();
  return (m >= 555 && m <= 695) || (m >= 775 && m <= 905);
}

const tradingNow = computed(() => isTradingTime());
const updatedAtTime = computed(() => new Date(updatedAt.value));

const updatedTimeText = computed(() =>
  updatedAtTime.value.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }),
);

const dataSources = computed(() => {
  const set = new Set();
  for (const s of stocks.value) if (s.data_source) set.add(s.data_source);
  for (const i of indexes.value) if (i.data_source) set.add(i.data_source);
  return [...set];
});

function changeInfo(q) {
  return parseChange(q?.["涨跌幅"]);
}

function badgeClass(q) {
  const d = changeInfo(q).direction;
  const base = "";
  if (d > 0) return `${base} bg-red-50 text-up dark:bg-red-500/10`;
  if (d < 0) return `${base} bg-emerald-50 text-down dark:bg-emerald-500/10`;
  return `${base} bg-slate-100 text-slate-500 dark:bg-slate-700/50`;
}

async function refresh(manual = false) {
  if (loading.value) return;
  loading.value = true;
  try {
    const codes = watchlist.list.value.map((w) => w.code);
    const data = await getMarketSnapshot(codes);
    indexes.value = data.indexes || [];
    // 用自选列表里用户存的名称补齐（行情接口不返回名称）
    const nameMap = Object.fromEntries(
      watchlist.list.value.map((w) => [w.code, w.name]),
    );
    stocks.value = (data.stocks || []).map((s) => ({
      ...s,
      name: nameMap[s.stock_code] && nameMap[s.stock_code] !== s.stock_code
        ? nameMap[s.stock_code]
        : s.name,
    }));
    errors.value = data.errors || [];
    updatedAt.value = data.updated_at || Date.now();
    if (manual) inputError.value = "";
  } catch (e) {
    if (manual) inputError.value = "行情服务暂不可用，请稍后重试";
  } finally {
    loading.value = false;
  }
}

function toggleExpand(code) {
  expanded.value = expanded.value === code ? "" : code;
}

function removeStock(code) {
  watchlist.remove(code);
  stocks.value = stocks.value.filter((s) => s.stock_code !== String(code));
}

function addPreset(s) {
  if (watchlist.add(s)) refresh();
}

function addByInput() {
  const raw = inputText.value.trim();
  const m = raw.match(/^(.{0,10}?)?\s*(\d{6})\s*(.*)$/);
  const code = raw.match(/(\d{6})/)?.[1];
  if (!code) {
    inputError.value = "请输入 6 位股票代码";
    return;
  }
  const rest = raw.replace(code, "").trim();
  const name = rest || code;
  if (watchlist.add({ code, name })) {
    refresh();
  }
  inputText.value = "";
  inputError.value = "";
}

function schedulePolling() {
  if (timer) clearInterval(timer);
  if (isTradingTime()) {
    timer = setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, POLL_MS);
  }
}

function onVisibility() {
  // 切回页面且在交易时段时立即刷新一次
  if (document.visibilityState === "visible" && isTradingTime()) refresh();
}

onMounted(() => {
  refresh();
  schedulePolling();
  document.addEventListener("visibilitychange", onVisibility);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  document.removeEventListener("visibilitychange", onVisibility);
});
</script>

<style scoped>
/* 隐藏横向滚动条（指数横滑条） */
.scrollbar-none::-webkit-scrollbar {
  display: none;
}
.scrollbar-none {
  scrollbar-width: none;
}
</style>
