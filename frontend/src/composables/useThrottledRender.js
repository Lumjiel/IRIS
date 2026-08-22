import { ref, watch } from "vue";

/**
 * 节流渲染 composable
 * 用 requestAnimationFrame 节流高频更新（如流式 token），
 * 避免每个 token 都触发 markdown 重渲染
 *
 * @param {import("vue").Ref<string>} source - 源文本 ref
 * @param {number} interval - 最小渲染间隔(ms)，默认 50ms (20fps)
 * @returns {import("vue").Ref<string>} 节流后的文本 ref
 */
export function useThrottledRender(source, interval = 50) {
  const throttled = ref(source.value);
  let lastRender = 0;
  let pending = null;
  let rafId = null;

  watch(source, (val) => {
    pending = val;
    const now = Date.now();
    const elapsed = now - lastRender;

    if (elapsed >= interval) {
      lastRender = now;
      throttled.value = val;
    } else if (!rafId) {
      rafId = requestAnimationFrame(() => {
        rafId = null;
        lastRender = Date.now();
        throttled.value = pending;
      });
    }
  });

  return throttled;
}

/**
 * 批量累积 composable
 * 将高频小更新合并为低频大更新
 * 适合 SSE token 流式场景：积累到一定量或超时后再 flush
 */
export function useBatchAccumulate(interval = 60) {
  const accumulated = ref("");
  let buffer = "";
  let timer = null;

  const push = (chunk) => {
    buffer += chunk;
    if (!timer) {
      timer = setTimeout(() => {
        accumulated.value += buffer;
        buffer = "";
        timer = null;
      }, interval);
    }
  };

  /** 强制刷新缓冲区 */
  const flush = () => {
    if (buffer) {
      accumulated.value += buffer;
      buffer = "";
    }
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const reset = () => {
    accumulated.value = "";
    buffer = "";
    flush();
  };

  return { accumulated, push, flush, reset };
}
