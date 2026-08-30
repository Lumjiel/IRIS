import { ref, reactive, nextTick } from "vue";
import { streamChat, newThreadId, getThreadId } from "../services/api";
import { saveSession } from "../services/history";

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

  // 必须用 reactive 包装：push 进 ref 数组后若直接改原始对象，绕过 Vue3 的 Proxy，
  // 不会触发任何依赖更新——这正是研究流程 UI 卡在「思考中…」的根因
  const newMsg = (role, type, content, extra = {}) => {
    const m = reactive({ id: ++msgId, role, type, content, ...extra });
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
        // 意图事件（首事件）：intent + 识别耗时，供 ProcessBar 溯源徽章
        if (ev.step === "intent") {
          currentIntent = ev.data?.intent || "chat";
          loadingMsg.intent = currentIntent;
          loadingMsg.intentElapsed = ev.data?.elapsed ?? null;
          // chat 路径也保留事件记录（不再黑箱），但消息类型直接进入流式输出
          if (!loadingMsg.events) loadingMsg.events = [];
          loadingMsg.events.push({
            step: "router",
            status: "done",
            elapsed: ev.data?.elapsed ?? null,
          });
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
        // 节点事件：所有路径（含 chat）都记录，不再丢弃——ProcessBar 全程可见
        // 只收两类事件：带 status 的节点状态（start/done）、带可展示产物的 astream 数据
        const artifactData =
          ev.data?.plan || ev.data?.search_results || ev.data?.critique || null;
        const memoryCount = ev.data?.memories?.count ?? null;
        if (ev.step && ev.step !== "intent" && (ev.status || artifactData || memoryCount != null)) {
          if (!loadingMsg.events) loadingMsg.events = [];
          const existing = loadingMsg.events.find((e) => e.step === ev.step);
          if (existing) {
            // 状态事件（start/done）→ 更新状态 + 耗时
            if (ev.status) {
              existing.status = ev.status;
              if (ev.elapsed != null) existing.elapsed = ev.elapsed;
            }
            // astream data / done 附加数据 → 只更新中间产物，不覆盖状态
            if (artifactData) existing.artifact = artifactData;
            if (memoryCount != null) {
              existing.memories = { count: memoryCount };
              loadingMsg.memoryCount = memoryCount;
            }
          } else {
            loadingMsg.events.push({
              step: ev.step,
              status: ev.status || "running",
              artifact: artifactData,
              memories: memoryCount != null ? { count: memoryCount } : null,
              elapsed: ev.elapsed ?? null,
            });
            if (memoryCount != null) loadingMsg.memoryCount = memoryCount;
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
            // 首个研究/修订 token 到达即切换类型：让 ReportViewer 立即进入流式渲染，
            // 不必干等最后一条 final_report 完整事件（SSE 结束与 astream 收尾存在时序差）
            if (!loadingMsg.report) loadingMsg.report = "";
            if (loadingMsg.type !== currentIntent)
              loadingMsg.type = currentIntent || "research";
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
        if (loadingMsg.type === "loading") {
          // 流式结束仍无内容 = LLM 调用失败（如 key 失效/额度耗尽），明确报错而非永远"思考中"
          if (!loadingMsg.report && (!loadingMsg.content || loadingMsg.content === "思考中…")) {
            loadingMsg.type = "error";
            loadingMsg.content = "回复生成失败（LLM 调用异常），请稍后重试";
          } else {
            loadingMsg.type = "chat";
          }
        } else if ((loadingMsg.type === "research" || loadingMsg.type === "refine") && !loadingMsg.report) {
          // 研报流式中断且未产出任何内容
          loadingMsg.type = "error";
          loadingMsg.content = "研报生成中断，请重新发起研究";
        }
        // 持久化研究/修订报告，供侧栏历史与 HistoryView 展示（chat 对话不入库）
        if (loadingMsg.report) {
          saveSession({
            threadId: getThreadId(),
            query,
            report: loadingMsg.report,
            messages: messages.value,
            mode,
          });
        }
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
