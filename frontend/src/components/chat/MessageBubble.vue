<template>
  <div class="flex gap-3" :class="msg.role === 'user' ? 'justify-end' : ''">
    <!-- AI 头像 -->
    <div v-if="msg.role !== 'user'" class="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shrink-0 text-white text-xs font-bold mt-1 shadow-soft ai-avatar">IR</div>

    <div class="max-w-[85%] min-w-0 md:max-w-[75%]" :class="msg.role === 'user' ? 'order-1' : ''">
      <!-- 用户消息 -->
      <div v-if="msg.role === 'user'">
        <div class="bg-accent text-white px-4 py-2.5 rounded-2xl rounded-br-md text-body user-bubble relative dark:bg-indigo-600">{{ msg.content }}</div>
      </div>

      <!-- AI 消息：CHAT -->
      <div v-else-if="msg.type === 'chat'" class="space-y-2">
        <div class="bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/60 dark:border-slate-700/60 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
          <div class="text-body text-slate-700 dark:text-slate-300 leading-relaxed">{{ msg.content }}</div>
        </div>
        <!-- 闲聊路径也展示过程（记忆注入 + 对话节点） -->
        <ProcessBar
          v-if="msg.events && msg.events.length"
          :events="msg.events"
          :intent="msg.intent"
          :done="true"
        />
      </div>

      <!-- AI 消息：RESEARCH / REFINE（节点链置顶：先看流程，再看数据与报告） -->
      <div v-else-if="msg.type === 'research' || msg.type === 'refine'" class="space-y-3">
        <ProcessBar
          :events="msg.events || []"
          :intent="msg.intent"
          :done="!msg.streaming"
          :data-source="msg.quote?.data_source || ''"
        />
        <MarketDataCard v-if="msg.quote" :quote="msg.quote" :kline="msg.kline || []" />
        <FinancialCard v-if="msg.financial" :financial="msg.financial" />
        <!-- 研报正文（流式渲染） -->
        <ReportViewer
          v-if="msg.report"
          :content="msg.report"
          :streaming="!!msg.streaming"
        />
        <ActionBar
          v-if="msg.report && !msg.streaming && msg.type !== 'loading'"
          :report="msg.report"
          :sources="msg.quote?.data_source ? [msg.quote.data_source] : []"
          @copy="$emit('copy', msg)"
          @download="$emit('download', msg)"
          @save="$emit('save', msg)"
        />
        <!-- 基于本报告继续追问（仅最后一条报告消息显示） -->
        <FollowUpInput
          v-if="isLastReport"
          :model-value="followUpValue"
          @update:model-value="$emit('update:followUpValue', $event)"
          @send="$emit('follow-send')"
        />
      </div>

      <!-- AI 消息：加载中 -->
      <div v-else-if="msg.type === 'loading'" class="bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl border border-white/60 dark:border-slate-700/60 rounded-2xl rounded-bl-md px-4 py-3 shadow-soft">
        <div class="flex items-center gap-2 text-body text-slate-500 dark:text-slate-400">
          <span class="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
          {{ msg.content || '思考中…' }}
        </div>
        <!-- 研究流程节点时间线：intent 为 research/refine 时 type 仍是 loading，
             必须在 loading 分支内渲染，否则整个流程期间看不到任何 agent 进度 -->
        <ProcessBar
          :events="msg.events || []"
          :intent="msg.intent"
          :done="false"
          class="mt-3"
        />
        <!-- 骨架屏：研究流程耗时数分钟，shimmer 块降低等待焦虑（有时间线时隐藏） -->
        <div v-if="!(msg.events && msg.events.length)" class="mt-3 space-y-2.5" aria-hidden="true">
          <div class="skeleton-line h-3 rounded bg-slate-100 dark:bg-slate-700/60 w-full"></div>
          <div class="skeleton-line h-3 rounded bg-slate-100 dark:bg-slate-700/60 w-5/6"></div>
          <div class="skeleton-line h-14 rounded-lg bg-slate-100 dark:bg-slate-700/60 w-full"></div>
        </div>
      </div>

      <!-- AI 消息：错误 -->
      <div v-else-if="msg.type === 'error'" class="bg-red-50 border border-red-200 dark:bg-red-900/20 dark:border-red-800 rounded-2xl rounded-bl-md px-4 py-3">
        <div class="text-body text-red-600 dark:text-red-400">{{ msg.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import MarketDataCard from "../MarketDataCard.vue";
import FinancialCard from "../FinancialCard.vue";
import ProcessBar from "../ProcessBar.vue";
import ReportViewer from "../ReportViewer.vue";
import ActionBar from "../ActionBar.vue";
import FollowUpInput from "../FollowUpInput.vue";

defineProps({
  msg: { type: Object, required: true },
  isLastReport: { type: Boolean, default: false },
  followUpValue: { type: String, default: "" },
});
defineEmits(["copy", "download", "save", "update:followUpValue", "follow-send"]);
</script>

<style scoped>
.user-bubble::after {
  content: '';
  position: absolute;
  bottom: 0;
  right: -5px;
  width: 10px;
  height: 10px;
  background: #4F46E5;
  clip-path: polygon(0 0, 100% 100%, 0 100%);
}
.ai-avatar {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.ai-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);
}
</style>
