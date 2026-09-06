import { reactive, ref } from "vue";

const STORAGE_KEY = "iris_watchlist";

/**
 * 自选股管理 composable（localStorage 持久化）
 * 数据结构：[{ code, name, addedAt }]
 *
 * 返回 reactive 包装：模板里 watchlist.list 直接是数组。
 * 若返回普通对象包 ref，嵌套 ref 不会被模板解包，`watchlist.list.length`
 * 恒为 undefined（2026-09-06 修的存量 bug：空态引导从不显示）。
 */
export function useWatchlist() {
  const list = ref(load());

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  const persist = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(list.value));
    } catch {
      // localStorage 不可用时静默降级
    }
  };

  /** 添加自选股（去重，code 归一为 6 位） */
  const add = (item) => {
    const code = String(item.code || "")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!code) return false;
    const exists = list.value.some((s) => s.code === code);
    if (!exists) {
      list.value.push({ code, name: item.name || code, addedAt: Date.now() });
      persist();
    }
    return !exists;
  };

  /** 移除自选股 */
  const remove = (code) => {
    const idx = list.value.findIndex((s) => s.code === String(code));
    if (idx >= 0) {
      list.value.splice(idx, 1);
      persist();
    }
  };

  const has = (code) => list.value.some((s) => s.code === String(code));

  return reactive({ list, add, remove, has });
}
