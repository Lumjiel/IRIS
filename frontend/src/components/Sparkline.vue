<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
    <polyline
      fill="none"
      :stroke="color"
      :stroke-width="strokeWidth"
      :points="points"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: { type: Array, default: () => [] },
  width: { type: Number, default: 120 },
  height: { type: Number, default: 32 },
  strokeWidth: { type: Number, default: 1.5 },
  color: { type: String, default: '#94a3b8' },
});

const points = computed(() => {
  const arr = props.data.filter(n => typeof n === 'number' && !isNaN(n));
  if (arr.length < 2) return '';
  const min = Math.min(...arr);
  const max = Math.max(...arr);
  const range = max - min || 1;
  const w = props.width;
  const h = props.height;
  return arr.map((v, i) => {
    const x = (i / (arr.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
});
</script>