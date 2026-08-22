import { defineStore } from "pinia";

/**
 * 全局应用状态 store
 * 管理：深色模式、用户偏好、会话 thread_id
 */
export const useAppStore = defineStore("app", {
  state: () => ({
    dark: false,
    threadId: null,
    preferences: {},
  }),

  getters: {
    isDark: (state) => state.dark,
  },

  actions: {
    initFromStorage() {
      // 深色模式
      const savedDark = localStorage.getItem("iris-dark");
      this.dark =
        savedDark === null
          ? window.matchMedia("(prefers-color-scheme: dark)").matches
          : savedDark === "true";

      // 会话 ID
      this.threadId = localStorage.getItem("iris_thread_id") || null;

      // 用户偏好
      try {
        this.preferences = JSON.parse(
          localStorage.getItem("iris_preferences") || "{}",
        );
      } catch {
        this.preferences = {};
      }
    },

    toggleDark() {
      this.dark = !this.dark;
      localStorage.setItem("iris-dark", this.dark);
    },

    setThreadId(id) {
      this.threadId = id;
      localStorage.setItem("iris_thread_id", id);
    },

    setPreferences(prefs) {
      this.preferences = { ...this.preferences, ...prefs };
      localStorage.setItem(
        "iris_preferences",
        JSON.stringify(this.preferences),
      );
    },

    resetSession() {
      this.threadId = crypto.randomUUID();
      localStorage.setItem("iris_thread_id", this.threadId);
    },
  },
});
