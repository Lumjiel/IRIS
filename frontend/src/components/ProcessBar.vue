<template>
  <div class="card px-3 py-2">
    <!-- 紧凑过程链（常驻一行） -->
    <div class="flex items-center gap-1.5 flex-wrap min-h-[1.5rem]">
      <span class="text-label text-slate-400 shrink-0 mr-0.5">进程</span>

      <template v-if="steps.length">
        <span
          v-for="s in steps"
          :key="s.key"
          class="inline-flex items-center gap-1 text-caption px-1.5 py-0.5 rounded-md"
          :class="chipCls(s)"
        >
          <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="dotCls(s.status)">
            <span v-if="s.status === 'running'" class="block w-full h-full rounded-full bg-white animate-pulse" />
          </span>
          {{ s.short }}
          <span v-if="s.status === 'done' && s.elapsed" class="num opacity-60">{{ s.elapsed }}s</span>
        </span>
      </template>
      <span v-else class="text-caption text-slate-400">等待启动…</span>

      <button
        @click="expanded = !expanded"
        class="ml-auto shrink-0 inline-flex items-center gap-0.5 text-label text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
      >
        详情
        <svg class="w-3 h-3 transition-transform" :class="expanded ? 'rotate-90' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    </div>

    <!-- 溯源徽章行（完成后常驻，回答底部一行小字） -->
    <div v-if="done && steps.length" class="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
      <div class="flex items-center gap-x-3 gap-y-1 flex-wrap text-label text-slate-500 dark:text-slate-400">
        <span v-if="intentLabel" class="inline-flex items-center gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-accent"></span>{{ intentLabel }}
        </span>
        <span class="num">{{ steps.length }}节点</span>
        <span v-if="reviewRounds > 1" class="num">{{ reviewRounds }}轮审核</span>
        <span v-if="memoryCount > 0" class="inline-flex items-center gap-1">
          <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12V5a2 2 0 00-2-2H6a2 2 0 00-2 2v13a2 2 0 002 2h6"/><path d="M12 12v7"/><path d="M15 15l-3 3-3-3"/></svg>
          {{ memoryCount }}条记忆
        </span>
        <span v-if="dataSource">{{ dataSource }}</span>
        <span v-if="totalElapsed > 0" class="num">~{{ totalElapsed }}s</span>
      </div>
    </div>

    <!-- 展开后的垂直时间线（含中间产物） -->
    <div v-if="expanded && detailSteps.length" class="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
      <ol class="relative pl-4">
        <li v-for="(node, idx) in detailSteps" :key="node.key" class="relative pb-3 last:pb-0">
          <span v-if="idx < detailSteps.length - 1" class="absolute left-[4px] top-2 bottom-0 w-px"
                :class="node.status === 'done' ? 'bg-emerald-400' : 'bg-slate-200 dark:bg-slate-600'" />
          <span class="absolute left-0 top-1 w-2 h-2 rounded-full" :class="dotCls(node.status)">
            <svg v-if="node.status === 'done'" class="w-1.5 h-1.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <span v-else-if="node.status === 'running'" class="block w-full h-full rounded-full bg-accent animate-pulse" />
          </span>
          <div class="ml-4">
            <div class="flex items-center justify-between">
              <span :class="['text-body font-medium', textCls(node.status)]">{{ node.label }}</span>
              <span v-if="node.status === 'done' && node.elapsed" class="text-label text-slate-400 num">{{ node.elapsed }}s</span>
            </div>
            <p v-if="node.status === 'error'" class="text-label text-red-600 mt-0.5">{{ node.error }}</p>
            <div v-if="node.key === 'load_memories' && memoryItems.length" class="mt-1 space-y-0.5">
              <div v-for="(m, i) in memoryItems" :key="i" class="text-label text-slate-500 dark:text-slate-400">→ 💾 {{ m }}</div>
            </div>
            <button
              v-if="node.status === 'done' && node.artifact"
              @click="artOpen[node.key] = !artOpen[node.key]"
              class="text-label text-accent mt-1 flex items-center gap-1"
            >
              <svg class="w-3 h-3 transition-transform" :class="artOpen[node.key] ? 'rotate-90' : ''" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
              查看中间产物
            </button>
            <div v-if="artOpen[node.key] && node.artifact" class="mt-1.5 p-2.5 bg-white/50 dark:bg-slate-900/50 backdrop-blur rounded-md text-label text-slate-700 dark:text-slate-300 space-y-1">
              <div v-for="(line, i) in node.artifactLines" :key="i">→ {{ line }}</div>
            </div>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
/**
 * ProcessBar — Agent 过程可视化的统一入口。
 *
 * 两态设计：
 * - 运行中：一行紧凑节点链，真实反映后端 traced 节点的 start/done 事件流，
 *   当前节点高亮脉动——面试官发任何消息都能看到"分诊→记忆→干活→审核"全过程
 * - 完成后：收起为溯源徽章行（意图 / 节点数 / 审核轮数 / 记忆条数 / 数据源 / 总耗时），
 *   随消息持久化，历史回看也保留架构痕迹
 *
 * 事件契约：后端 emit_node_event 推送 {step, status: start|done, elapsed, data?}
 */
import { computed, reactive, ref } from "vue";

/** 真实节点表：order = 图中实际执行顺序；假节点 route_after_tools 不收录 */
const NODE_MAP = {
  load_memories:  { label: "记忆注入", short: "记忆", order: 0 },
  router:         { label: "意图识别", short: "意图", order: 1 },
  planner:        { label: "搜索规划", short: "规划", order: 2 },
  researcher:     { label: "文档检索", short: "检索", order: 3 },
  search_agent:   { label: "网络调研", short: "调研", order: 4 },
  search_tools:   { label: "工具调用", short: "工具", order: 5 },
  data_collector: { label: "数据采集", short: "数据", order: 6 },
  writer:         { label: "报告撰写", short: "撰写", order: 7 },
  reviewer:       { label: "质量审核", short: "审核", order: 8 },
  refiner:        { label: "报告修订", short: "修订", order: 9 },
  chat:           { label: "智能对话", short: "对话", order: 10 },
};

const INTENT_LABEL = { research: "深度研究", refine: "报告修订", chat: "智能对话" };

const props = defineProps({
  events: { type: Array, default: () => [] },
  intent: { type: String, default: "" },
  done: { type: Boolean, default: false },
  dataSource: { type: String, default: "" },
});

const expanded = ref(false);
const artOpen = reactive({});

function stepEvents(key) {
  return props.events.filter((e) => e.step === key);
}

function latestStatus(evs) {
  return [...evs].reverse().find((e) => e.status);
}

function pickArtifact(evs) {
  const d = evs.find((e) => e.data?.memories?.length || e.data?.plan?.length ||
    e.data?.search_results?.length || e.data?.critique);
  return d?.data ?? null;
}

const steps = computed(() => {
  const seen = new Set();
  for (const e of props.events) if (NODE_MAP[e.step]) seen.add(e.step);
  return [...seen].map((key) => {
    const evs = stepEvents(key);
    const st = latestStatus(evs) || {};
    const mem = key === "load_memories" ? pickArtifact(evs) : null;
    const art = pickArtifact(evs);
    const raw = key === "load_memories" ? null : (art ? (Array.isArray(art.plan || art.search_results || art.critique) ? (art.plan || art.search_results) : String(art.critique)) : null);
    return {
      key,
      ...NODE_MAP[key],
      status: st.status || "waiting",
      elapsed: st.elapsed || "",
      error: st.error || "",
      memoryCount: mem?.count ?? 0,
      artifact: raw,
      artifactLines: raw == null ? [] : (Array.isArray(raw) ? raw : String(raw).split("\n")),
    };
  }).sort((a, b) => a.order - b.order);
});

const detailSteps = computed(() => steps.value);

const memoryItems = computed(() => {
  const evs = stepEvents("load_memories");
  const d = evs.find((e) => e.data?.memories?.length);
  return d?.data?.memories || [];
});

const memoryCount = computed(() => {
  const evs = stepEvents("load_memories");
  const d = evs.find((e) => e.data?.count != null);
  return d?.data?.count || 0;
});

const reviewRounds = computed(
  () => props.events.filter((e) => e.step === "reviewer" && e.status === "start").length,
);

const totalElapsed = computed(() =>
  Math.round(steps.value.reduce((sum, s) => sum + (Number(s.elapsed) || 0), 0)),
);

const intentLabel = computed(() => INTENT_LABEL[props.intent] || "");

function dotCls(s) {
  return s === "done"
    ? "bg-emerald-500"
    : s === "running"
    ? "bg-accent animate-pulse"
    : s === "error"
    ? "bg-red-500"
    : "border-2 border-slate-300 bg-transparent";
}

function textCls(s) {
  return s === "done"
    ? "text-slate-900 dark:text-slate-100"
    : s === "running"
    ? "text-accent font-semibold"
    : s === "error"
    ? "text-red-600"
    : "text-slate-400";
}

function chipCls(s) {
  if (s.status === "running") return "bg-accent/10 text-accent font-medium";
  if (s.status === "done") return "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400";
  if (s.status === "error") return "bg-red-50 text-red-600 dark:bg-red-500/10";
  return "bg-slate-100 text-slate-400 dark:bg-slate-700/50";
}
</script>
