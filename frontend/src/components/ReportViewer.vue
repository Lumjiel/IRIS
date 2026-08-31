<template>
  <div class="card overflow-hidden">
    <div v-if="title" class="px-6 py-4 border-b border-slate-100 dark:border-slate-700/50 bg-white/40 dark:bg-slate-800/40 backdrop-blur-lg border-l-4 border-l-accent">
      <h1 class="text-data-xl font-semibold text-slate-900">{{ title }}</h1>
      <p class="text-label text-slate-500 mt-1">{{ subtitle }}</p>
    </div>

    <!-- 章节 TOC（sticky + scrollspy） -->
    <nav v-if="toc.length > 1" class="hidden lg:block sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-slate-100 px-6 py-2">
      <ul class="flex gap-4 overflow-x-auto text-label">
        <li v-for="item in toc" :key="item.id">
          <a
            :href="`#${item.id}`"
            class="transition-colors duration-200"
            :class="activeId === item.id ? 'text-accent font-medium' : 'text-slate-500 hover:text-slate-700'"
          >{{ item.title }}</a>
        </li>
      </ul>
    </nav>

    <!-- 报告正文 -->
    <div class="p-6 max-w-4xl">
      <div class="prose prose-slate max-w-none text-body leading-relaxed" v-html="rendered" />

      <!-- 流式时光标 -->
      <span v-if="streaming" class="inline-block w-0.5 h-5 bg-accent animate-pulse align-middle mt-2" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue';
import { renderMarkdown } from '../utils/markdown';
import { useThrottledRender } from '../composables/useThrottledRender';

const props = defineProps({
  content: { type: String, default: '' },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
});

// 节流渲染：流式时 50ms 节流，避免每个 token 都重渲染
const throttledContent = useThrottledRender(
  computed(() => props.content),
  50
);
const rendered = computed(() => renderMarkdown(throttledContent.value));

// --- 提取 h2 章节生成 TOC ---
const toc = ref([]);
const activeId = ref('');

const extractToc = () => {
  const tmp = document.createElement('div');
  tmp.innerHTML = rendered.value;
  const h2s = tmp.querySelectorAll('h2');
  toc.value = Array.from(h2s).map(el => ({ id: el.id, title: el.textContent || '' })).filter(t => t.title);
};

watch(rendered, () => nextTick(extractToc), { immediate: true });

// --- ScrollSpy：IntersectionObserver ---
let observer = null;
onMounted(() => {
  observer = new IntersectionObserver(
    entries => {
      for (const e of entries) {
        if (e.isIntersecting) activeId.value = e.target.id;
      }
    },
    { rootMargin: '-20% 0px -70% 0px' }
  );
  nextTick(() => {
    toc.value.forEach(t => {
      const el = document.getElementById(t.id);
      if (el) observer.observe(el);
    });
  });
});

onUnmounted(() => observer && observer.disconnect());
</script>
