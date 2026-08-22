import { ref, nextTick } from "vue";
import { streamChat, newThreadId } from "../services/api";

let msgId = 0;

/**
 * 聊天状态管理 composable
 * 从 App.vue 提取：消息列表、SSE 解析、加载状态
 */
export function useChat() {
  const messages = ref([]);
  const isLoading = ref(false);
  const scrollEl = ref(null);

  const scrollToBottom = () => {
    const el = scrollEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  };

  const newMsg = (role, type, content, extra = {}) => {
    const m = { id: ++msgId, role, type, content, ...extra };
    messages.value.push(m);
    nextTick(scrollToBottom);
    return m;
  };

  /**
   * 发送消息并处理 SSE 流式响应
   * @param {string} query - 用户输入
   * @param {string} mode - 搜索模式 (hybrid/document)
   * @param {AbortSignal} signal - 中止信号
   */
  const sendMessage = async (query, mode = "hybrid", signal) => {
    if (!query.trim() || isLoading.value) return;

    newMsg("user", "text", query);
    isLoading.value = true;

    const loadingMsg = newMsg("assistant", "loading", "思考中…");
    let currentIntent = null;

    streamChat(
      query,
      mode,
      (ev) => {
        // 意图事件（首事件）
        if (ev.step === "intent") {
          currentIntent = ev.data?.intent || "chat";
          loadingMsg.type = currentIntent === "chat" ? "chat" : "loading";
          loadingMsg.content =
            currentIntent === "research"
              ? "正在启动研究…"
              : currentIntent === "refine"
                ? "正在修订报告…"
                : "思考中…";
          return;
        }

        // 节点事件（研究/修订路径）
        if (ev.step && ev.step !== "intent" && currentIntent !== "chat") {
          if (!loadingMsg.events) loadingMsg.events = [];
          const existing = loadingMsg.events.find((e) => e.step === ev.step);
          if (existing) {
            // 状态事件（start/done）→ 更新状态 + 耗时
            if (ev.status) {
              existing.status = ev.status;
              if (ev.elapsed != null) existing.elapsed = ev.elapsed;
            }
            // astream data 事件 → 只更新中间产物，不覆盖状态
            if (ev.data) {
              existing.artifact =
                ev.data.plan ||
                ev.data.search_results ||
                ev.data.critique ||
                existing.artifact;
            }
          } else if (ev.step !== "chat") {
            loadingMsg.events.push({
              step: ev.step,
              status: ev.status || "running",
              artifact:
                ev.data?.plan ||
                ev.data?.search_results ||
                ev.data?.critique ||
                null,
              elapsed: ev.elapsed ?? null,
            });
          }
        }

        // 报告内容
        if (ev.data?.final_report) {
          loadingMsg.report = ev.data.final_report;
          loadingMsg.type = currentIntent;
        } else if (ev.data?.chat_response) {
          loadingMsg.content = ev.data.chat_response;
          loadingMsg.type = "chat";
        } else if (ev.data?.token && !ev.data.final) {
          if (currentIntent === "chat") {
            loadingMsg.content =
              (loadingMsg.content === "思考中…" ? "" : loadingMsg.content) +
              ev.data.token;
          } else {
            loadingMsg.streaming = true;
            if (!loadingMsg.report) loadingMsg.report = "";
            loadingMsg.report += ev.data.token;
          }
        }

        // 行情 & 财务数据：后端 data_collector 节点输出 financial_data 结构
        // { stock_code, stock_info, indicators: {...}, quote: {...} }
        const fin = ev.data?.financial_data;
        if (fin?.quote)
          loadingMsg.quote = {
            ...fin.quote,
          };
        if (fin?.indicators)
          loadingMsg.financial = {
            ...fin.indicators,
          };
      },
      () => {
        isLoading.value = false;
        loadingMsg.streaming = false;
        if (loadingMsg.events) {
          loadingMsg.events.forEach((e) => {
            if (e.status === "running") e.status = "done";
          });
        }
        if (loadingMsg.type === "loading") loadingMsg.type = "chat";
      },
      (err) => {
        isLoading.value = false;
        loadingMsg.type = "error";
        loadingMsg.content = err?.message || "请求失败，请重试";
      },
      signal,
    );
  };

  /** 获取最近一份报告消息（供 ActionBar 使用） */
  const getCurrentReport = () =>
    messages.value.find((m) => m.report && m.type !== "loading");

  /** 清空消息 */
  const clearMessages = () => {
    messages.value = [];
    msgId = 0;
  };

  /** 开启新会话：清空消息 + 换新 thread_id */
  const newThread = () => {
    messages.value = [];
    msgId = 0;
    newThreadId();
  };

  return {
    messages,
    isLoading,
    scrollEl,
    sendMessage,
    getCurrentReport,
    clearMessages,
    scrollToBottom,
    newThread,
  };
}
