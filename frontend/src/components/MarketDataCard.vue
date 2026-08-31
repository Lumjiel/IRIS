<template>
  <div class="card p-4">
    <div class="flex items-baseline justify-between mb-3">
      <span class="text-label text-slate-500">实时行情</span>
      <span class="num text-label text-slate-400">{{ data_source }}</span>
    </div>

    <div class="flex items-baseline gap-3 mb-1">
      <span class="num text-data-xl text-slate-900">¥{{ price }}</span>
      <span :class="changeBadge">{{ change }}</span>
    </div>

    <!-- Sparkline：30 日走势（无 K 线数据时隐藏，fail-open） -->
    <div v-if="klineData.length" class="my-3">
      <Sparkline :data="klineData" :width="240" :height="32" :color="sparkColor" />
    </div>

    <div class="grid grid-cols-2 gap-3 text-body">
      <div>
        <TermTip term="换手率" />
        <div class="num text-slate-900 mt-0.5">{{ turnover }}</div>
      </div>
      <div>
        <TermTip term="市盈率PE" />
        <div class="num text-slate-900 mt-0.5">{{ pe }}</div>
      </div>
      <div>
        <TermTip term="市净率PB" />
        <div class="num text-slate-900 mt-0.5">{{ pb }}</div>
      </div>
      <div>
        <TermTip term="总市值" />
        <div class="num text-slate-900 mt-0.5">{{ mktCap }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import Sparkline from './Sparkline.vue';
import TermTip from './TermTip.vue';
import { parseChange, formatPrice, formatBigInt, pick, formatYoY } from '../utils/format';

const props = defineProps({
  quote: { type: Object, default: () => ({}) },
  kline: { type: Array, default: () => [] },
});

const data_source = computed(() => props.quote?.data_source || '—');

const price = computed(() => formatPrice(pick(props.quote, 'latest', pick(props.quote, '最新价'))));

const changeInfo = computed(() => parseChange(pick(props.quote, 'change_pct', pick(props.quote, '涨跌幅'))));
const change = computed(() => changeInfo.value.display);
const changeBadge = computed(() => {
  const d = changeInfo.value.direction;
  const base = 'px-2 py-0.5 rounded-md font-medium';
  return d > 0
    ? `${base} bg-red-600 text-white`
    : d < 0
    ? `${base} bg-emerald-600 text-white`
    : `${base} bg-slate-200 text-slate-600`;
});

const sparkColor = computed(() => {
  const d = changeInfo.value.direction;
  return d > 0 ? '#DC2626' : d < 0 ? '#059669' : '#94a3b8';
});

const turnover = computed(() => {
  const v = pick(props.quote, 'turnover', pick(props.quote, '换手率'));
  return v === '-' ? '-' : v;
});

// 数值兜底：mock/异常数据可能给 NaN、"NaN"、空串等，统一显示 "-"
const toFixedOrDash = (v) => {
  const n = Number(v);
  return v == null || v === '-' || v === '' || !Number.isFinite(n) ? '-' : n.toFixed(2);
};

const pe = computed(() => {
  const v = pick(props.quote, 'pe', pick(props.quote, '市盈率-动态', pick(props.quote, '市盈率')));
  return toFixedOrDash(v);
});

const pb = computed(() => {
  const v = pick(props.quote, 'pb', pick(props.quote, '市净率'));
  return toFixedOrDash(v);
});

const mktCap = computed(() => formatBigInt(pick(props.quote, 'mkt_cap', pick(props.quote, '总市值'))));

// K线数据：数组 of 收盘价 number
const klineData = computed(() => {
  if (!Array.isArray(props.kline)) return [];
  return props.kline.map(d => {
    const close = d?.close ?? d?.收盘 ?? d;
    return typeof close === 'number' ? close : parseFloat(close);
  }).filter(n => !isNaN(n));
});
</script>