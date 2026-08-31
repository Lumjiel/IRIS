<template>
  <footer class="border-t border-slate-200/70 dark:border-slate-700/60 bg-white/60 dark:bg-slate-800/60 backdrop-blur-xl px-4 py-3 shrink-0">
    <div class="max-w-3xl mx-auto">
      <div class="flex items-end gap-2 bg-white/60 dark:bg-slate-900/60 backdrop-blur-lg rounded-lg border border-slate-200/70 dark:border-slate-700/60 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/10 transition-colors duration-200 px-3 py-2">
        <!-- 附件按钮（PDF 文档入库） -->
        <button
          type="button"
          @click="pickFiles"
          class="shrink-0 w-8 h-8 rounded-md text-slate-400 hover:text-accent hover:bg-slate-100 dark:hover:bg-slate-700/50 flex items-center justify-center transition-colors"
          title="上传 PDF 文档（入库知识库，随问题一起分析）"
        >
          <svg class="w-4.5 h-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,application/pdf"
          multiple
          hidden
          @change="onPick"
        />
        <textarea
          ref="inputBox"
          :value="modelValue"
          @input="onInput"
          @keydown.enter.exact.prevent="$emit('send', pendingFiles)"
          class="flex-1 bg-transparent resize-none text-body text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none leading-relaxed"
          :rows="1"
          placeholder="输入股票代码或研究主题，回车发送；📎 可附带 PDF 文档…"
        />
        <button
          @click="$emit('send', pendingFiles)"
          :disabled="disabled || uploading || (!(modelValue && modelValue.trim()) && pendingFiles.length === 0)"
          class="shrink-0 w-10 h-10 rounded-md bg-accent hover:bg-accent/90 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <svg v-if="!uploading" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          <svg v-else class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.22-8.56"/></svg>
        </button>
      </div>

      <!-- 待上传文件 chips -->
      <div v-if="pendingFiles.length" class="flex flex-wrap gap-1.5 mt-2">
        <span
          v-for="(f, i) in pendingFiles"
          :key="i"
          class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200/60 dark:border-indigo-500/30 text-caption text-indigo-600 dark:text-indigo-300"
        >
          <svg class="w-3 h-3 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="max-w-[10rem] truncate">{{ f.name }}</span>
          <button
            type="button"
            @click="removeFile(i)"
            class="text-indigo-400 hover:text-red-500 transition-colors"
            aria-label="移除文件"
          >
            <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </span>
      </div>

      <p class="text-label text-slate-400 dark:text-slate-500 text-center mt-1.5">
        IRIS 可能会犯错，请核实重要信息 · 上传 PDF 将重建知识库
      </p>
    </div>
  </footer>
</template>

<script setup>
import { ref, watch, nextTick } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "send"]);

const inputBox = ref(null);
const fileInput = ref(null);
const pendingFiles = ref([]);

const autoResize = (el) => {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
};

const onInput = (e) => {
  emit("update:modelValue", e.target.value);
  autoResize(e.target);
};

// 发送后清空输入 → 重置高度
watch(
  () => inputBox.value,
  (el) => {
    if (el) nextTick(() => autoResize(el));
  },
);

// === 附件 ===
const pickFiles = () => fileInput.value?.click();

const onPick = (e) => {
  const files = Array.from(e.target.files || []).filter((f) =>
    f.name.toLowerCase().endsWith(".pdf"),
  );
  if (files.length !== (e.target.files?.length || 0)) {
    // 非 PDF 被过滤：前端提示（后端也会校验）
    const all = Array.from(e.target.files || []);
    if (all.some((f) => !f.name.toLowerCase().endsWith(".pdf"))) {
      alert("仅支持 PDF 文档，已忽略其他文件");
    }
  }
  pendingFiles.value = [...pendingFiles.value, ...files].slice(0, 5);
  e.target.value = ""; // 允许重复选择同一文件
};

const removeFile = (i) => {
  pendingFiles.value.splice(i, 1);
};

const clearFiles = () => {
  pendingFiles.value = [];
};

defineExpose({ clearFiles, autoResize, inputBox });
</script>
