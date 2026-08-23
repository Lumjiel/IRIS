<template>
  <svg :viewBox="`0 0 ${width} ${height}`" class="w-full" preserveAspectRatio="none">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.25" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <!-- 渐变面积：走势下方淡出填充 -->
    <path v-if="areaPath" :d="areaPath" :fill="`url(#${gid})`" stroke="none" />
    <!-- 平滑主线：Catmull-Rom → 三次贝塞尔 -->
    <path
      v-if="linePath"
      :d="linePath"
      fill="none"
      :stroke="color"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <!-- 收盘点：末端小圆点强调最新价 -->
    <circle v-if="lastPoint" :cx="lastPoint[0]" :cy="lastPoint[1]" r="2" :fill="color" />
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

// 每实例唯一渐变 id，避免多卡片同屏时 defs 冲突
const gid = `spark-${Math.random().toString(36).slice(2, 9)}`;

// 归一化坐标点（顶部留 2px、底部留 2px 呼吸空间）
const pts = computed(() => {
  const arr = props.data.filter(n => typeof n === 'number' && !isNaN(n));
  if (arr.length < 2) return [];
  const min = Math.min(...arr);
  const max = Math.max(...arr);
  const range = max - min || 1;
  const w = props.width;
  const h = props.height;
  return arr.map((v, i) => [
    (i / (arr.length - 1)) * w,
    h - ((v - min) / range) * (h - 4) - 2,
  ]);
});

/** Catmull-Rom 样条转三次贝塞尔，折线变平滑曲线 */
function smoothPath(points) {
  if (points.length < 3) {
    return 'M' + points.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L');
  }
  let d = `M${points[0][0].toFixed(1)},${points[0][1].toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
  }
  return d;
}

const linePath = computed(() => (pts.value.length >= 2 ? smoothPath(pts.value) : ''));

// 面积 = 主线闭合到基线，配渐变做淡出填充
const areaPath = computed(() => {
  if (!linePath.value) return '';
  const first = pts.value[0];
  const last = pts.value[pts.value.length - 1];
  return `${linePath.value} L${last[0].toFixed(1)},${props.height} L${first[0].toFixed(1)},${props.height} Z`;
});

const lastPoint = computed(() => (pts.value.length >= 2 ? pts.value[pts.value.length - 1] : null));
</script>
