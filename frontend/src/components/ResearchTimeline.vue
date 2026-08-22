<template>
  <div class="card p-4">
    <div class="text-label text-slate-500 mb-3">研究进程</div>

    <ol class="relative pl-4">
      <li v-for="(node, idx) in nodes" :key="node.key" class="relative pb-3 last:pb-0">
        <!-- 竖线 -->
        <span
          v-if="idx < nodes.length - 1"
          class="absolute left-[4px] top-2 bottom-0 w-px"
          :class="node.status === 'done' ? 'bg-emerald-400' : 'bg-slate-200'"
        />

        <!-- 节点圆点 -->
        <span
          class="absolute left-0 top-1 w-2 h-2 rounded-full flex items-center justify-center"
          :class="dotCls(node.status)"
        >
          <svg v-if="node.status === 'done'" class="w-1.5 h-1.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          <span v-else-if="node.status === 'running'" class="w-1 h-1 bg-white rounded-full animate-pulse" />
        </span>

        <!-- 节点内容 -->
        <div class="ml-4">
          <div class="flex items-center justify-between">
            <span :class="['text-body font-medium', textCls(node.status)]">{{ node.label }}</span>
            <span v-if="node.status === 'done'" class="text-label text-slate-400">{{ node.elapsed }}</span>
          </div>
          <p v-if="node.status === 'error'" class="text-label text-red-600 mt-0.5">{{ node.error }}</p>
          <!-- 中间产物（已完成节点可展开） -->
          <button
            v-if="node.status === 'done' && node.artifact"
            @click="node._expanded = !node._expanded"
            class="text-label text-accent mt-1 flex items-center gap-1"
          >
            <svg class="w-3 h-3 transition-transform" :class="node._expanded ? 'rotate-90' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg>
            查看中间产物
          </button>
          <div v-if="node._expanded && node.artifact" class="mt-2 p-3 bg-slate-50 rounded-md text-label text-slate-700 space-y-1">
            <div v-for="(line, i) in node.artifact" :key="i">→ {{ line }}</div>
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>

<script setup>
/**
 * ResearchTimeline — SSE 真实节点驱动
 * 节点 = 后端真实 8 节点（router→refiner），不做假动画
 */
import { computed } from 'vue';

const NODE_MAP = {
  router:        { label: '意图识别',  order: 0 },
  planner:       { label: '搜索规划',  order: 1 },
  researcher:    { label: '文档检索',  order: 2 },
  search_agent:  { label: '网络调研',  order: 3 },
  data_collector:{ label: '数据采集',  order: 4 },
  writer:        { label: '报告撰写',  order: 5 },
  reviewer:      { label: '质量审核',  order: 6 },
  refiner:       { label: '报告修订',  order: 7 },
};

const props = defineProps({
  // { step: 'planner'|'researcher'|..., status: 'running'|'done'|'error', artifact: string[], elapsed: string, error: string }
  events: { type: Array, default: () => [] },
});

const nodes = computed(() => {
  return Object.entries(NODE_MAP)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([key, { label }]) => {
      const ev = props.events.find(e => e.step === key);
      return {
        key,
        label,
        status: ev?.status || 'waiting',
        artifact: ev?.artifact || null,
        elapsed: ev?.elapsed || '',
        error: ev?.error || '',
        _expanded: false,
      };
    });
});

const dotCls = s => s === 'done' ? 'bg-emerald-500' : s === 'running' ? 'bg-accent animate-pulse' : s === 'error' ? 'bg-red-500' : 'border-2 border-slate-300 bg-transparent';
const textCls = s => s === 'done' ? 'text-slate-900' : s === 'running' ? 'text-accent font-semibold' : s === 'error' ? 'text-red-600' : 'text-slate-400';
</script>