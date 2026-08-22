<template>
  <div class="card p-4">
    <div class="flex items-baseline justify-between mb-3">
      <span class="text-label text-slate-500">关键财务</span>
      <span class="num text-label text-slate-400">{{ reportPeriod }}</span>
    </div>

    <div class="grid grid-cols-2 gap-3 text-body">
      <div>
        <span class="text-slate-500">营业总收入</span>
        <div class="num text-slate-900 mt-0.5">{{ revenue }}</div>
      </div>
      <div>
        <span class="text-slate-500">归母净利润</span>
        <div class="num text-slate-900 mt-0.5">{{ netProfit }}</div>
      </div>
      <div>
        <span class="text-slate-500">ROE</span>
        <div class="num text-slate-900 mt-0.5">{{ roe }}</div>
      </div>
      <div>
        <span class="text-slate-500">EPS</span>
        <div class="num text-slate-900 mt-0.5">{{ eps }}</div>
      </div>
      <div>
        <span class="text-slate-500">毛利率</span>
        <div class="num text-slate-900 mt-0.5">{{ grossMargin }}</div>
      </div>
      <div>
        <span class="text-slate-500">净利率</span>
        <div class="num text-slate-900 mt-0.5">{{ netMargin }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { formatBigInt, pick } from '../utils/format';

const props = defineProps({
  financial: { type: Object, default: () => ({}) },
});

const reportPeriod = computed(() => {
  const p = pick(props.financial, 'report_period');
  return p === '-' ? '—' : p;
});

const revenue = computed(() => formatBigInt(pick(props.financial, 'total_revenue')));
const netProfit = computed(() => formatBigInt(pick(props.financial, 'net_profit')));

const roe = computed(() => {
  const v = pick(props.financial, 'roe');
  if (v === '-') return '-';
  const n = Number(v);
  return isNaN(n) ? v : `${n.toFixed(2)}%`;
});

const eps = computed(() => {
  const v = pick(props.financial, 'eps');
  if (v === '-') return '-';
  const n = Number(v);
  return isNaN(n) ? v : n.toFixed(2);
});

const grossMargin = computed(() => {
  const v = pick(props.financial, 'gross_margin');
  if (v === '-') return '-';
  const n = Number(v);
  return isNaN(n) ? v : `${n.toFixed(2)}%`;
});

const netMargin = computed(() => {
  const v = pick(props.financial, 'net_margin');
  if (v === '-') return '-';
  const n = Number(v);
  return isNaN(n) ? v : `${n.toFixed(2)}%`;
});
</script>