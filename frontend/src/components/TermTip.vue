<template>
  <span class="relative inline-block">
    <button
      type="button"
      class="term-tip"
      @click.stop="open = !open"
      :aria-expanded="open"
    >
      {{ term }}<sup v-if="open ? false : true" class="text-[9px] leading-none ml-0.5 text-slate-400">?</sup>
    </button>
    <transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0 scale-95"
    >
      <span
        v-if="open"
        role="tooltip"
        class="absolute z-30 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 px-3 py-2 rounded-lg bg-slate-800 text-slate-100 text-caption leading-relaxed shadow-lg text-left normal-case"
      >
        {{ explanation }}
      </span>
    </transition>
  </span>
</template>

<script setup>
/**
 * 指标白话解释气泡：点击术语弹出一句小白能懂的解释。
 *
 * 产品定位（docs/HITHINK_INTEGRATION_PLAN.md 同系列决策）：
 * IRIS 的用户被设定为"非专业投资人"，所有指标可点击看白话解释——
 * 辅助了解市场信息，而非辅助投资决策。
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  /** 术语名，需在 TERMS 字典中 */
  term: { type: String, required: true },
});

/** 白话解释字典：一句话 + 一个直觉例子，刻意不用专业术语嵌套 */
const TERMS = {
  涨跌幅: "现在的价格比昨天收盘价变动了多少。+3% 就是比昨天涨了百分之三，A 股习惯红涨绿跌。",
  今开: "今天股市开盘（上午 9:30）时的第一笔成交价格。",
  最高: "今天成交过的最贵的一笔价格。",
  最低: "今天成交过的最便宜的一笔价格。",
  昨收: "昨天收盘时的最后价格，是计算今天涨跌的基准。",
  成交量: "今天一共换手了多少股。数字越大说明这只股票今天交易越活跃。",
  成交额: "今天买卖加起来的总金额。比如「45.5 亿」就是今天有 45.5 亿元在这只股票上转手。",
  市盈率PE: "股价 ÷ 每股年利润，可以粗略理解为「按现在的盈利水平，多少年回本」。20 倍就是约 20 年，越低相对越便宜。",
  市净率PB: "股价 ÷ 每股净资产。低于 1 意味着市值比公司账面净资产还低。",
  换手率: "今天有多少比例的流通股换了主人。越高说明交易越热闹，也可能波动更大。",
  总市值: "把公司所有股票按现价算一遍的总价钱，代表市场给这家公司的整体定价。",
};

const open = ref(false);
const explanation = computed(
  () => TERMS[props.term] || `${props.term}：暂无解释`,
);

function onDocClick() {
  open.value = false;
}

onMounted(() => document.addEventListener("click", onDocClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocClick));
</script>

<style scoped>
.term-tip {
  @apply underline decoration-dotted decoration-slate-300 dark:decoration-slate-600 underline-offset-4 cursor-help;
}
</style>
