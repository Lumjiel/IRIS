import { type ChatModelAdapter } from "@assistant-ui/react";
import { useGraphStore } from "@/store/graphStore";

/** 显示层转换：[来源: X] → `来源: X`（.aui-md code 渲染成小标签） */
function toDisplay(text: string): string {
  return text.replace(/\s*\[来源[:：]\s*([^\]]+)\]/g, "`来源: $1`");
}

/** 从用户提问中提取 A 股 6 位代码（主板/创业板/科创板，带数字边界防手机号误命中） */
function extractStockCode(query: string): string | null {
  const m = query.match(/(?<!\d)(60\d{4}|00\d{4}|30[01]\d{3}|688\d{3})(?!\d)/);
  return m ? m[1] : null;
}

/** 行情请求竞态防护：每个 run 一个序号，resolve 时校验仍是当前轮 */
let runSeq = 0;

async function fetchQuote(code: string, seq: number) {
  try {
    const r = await fetch(`/api/stock/${code}/quote`);
    const j = await r.json();
    if (seq !== runSeq) return; // 已切换会话/开新研究，丢弃旧行情
    if (!j.error && j.quote) {
      useGraphStore.getState().setQuote({ stock_code: code, ...j.quote });
    }
  } catch {
    /* 行情卡 fail-open：拉不到就不显示 */
  }
}

/**
 * IRIS 后端 SSE → assistant-ui LocalRuntime 适配器。
 *
 * 后端事件流（POST /api/chat，全部为 `data: {json}` 行）：
 * - {step:"intent", data:{intent, route, elapsed}}          意图判定
 * - {step:"<node>_token", data:{token, final?}}             报告/回复 token（writer/refiner）
 * - {step:"<node>", status:"start"|"done"|"failed", elapsed?, data?} 节点状态事件（时间线）
 * - {step:"<node>", data:{...}}                             图状态快照（前端忽略）
 * - {step:"error", data:{message}}                          错误
 * - "data: [DONE]"                                          结束
 */
export const IrisModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const last = messages[messages.length - 1];
    const query = last.content
      .filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join("\n")
      .trim();

    const store = useGraphStore.getState();
    store.reset();
    const seq = ++runSeq;

    // 后端会话连续性：同一会话（首条用户消息相同）复用同一 thread_id，
    // 让后端 checkpoint / conversation_summary 跨轮次生效
    const firstUser = messages.find((m) => m.role === "user");
    const firstText =
      firstUser?.content
        .filter((p): p is { type: "text"; text: string } => p.type === "text")
        .map((p) => p.text)
        .join(" ") ?? "";
    let hash = 0;
    for (let i = 0; i < firstText.length; i++) {
      hash = (hash * 31 + firstText.charCodeAt(i)) | 0;
    }
    const backendThreadId = `web-${(hash >>> 0).toString(36)}`;

    if (!query) {
      store.setError("请输入要研究的问题");
      store.setRunning(false); store.markRunEnd();
      return;
    }

    let text = "";
    let textDirty = false;
    let lastYieldLen = 0;
    /** 文本增量节流：不足 24 字符的增量不单独 yield，避免长报告 O(n²) 重渲染 */
    const shouldYield = () => textDirty && text.length - lastYieldLen >= 24;
    const doYield = function* () {
      if (textDirty) {
        lastYieldLen = text.length;
        textDirty = false;
        yield { content: [{ type: "text" as const, text: toDisplay(text) }] };
      }
    };

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          search_mode: "hybrid",
          thread_id: backendThreadId,
          style: "detailed",
          language: "zh",
        }),
        signal: abortSignal,
      });

      if (!res.ok || !res.body) {
        // 429 等 HTTP 错误：透传后端 detail（日配额/频率提示），前端时间线直接可读
        let detail = `后端请求失败: ${res.status}`;
        try {
          const j = await res.json();
          if (j?.detail) detail = String(j.detail);
        } catch {
          /* 非 JSON 响应体，用默认文案 */
        }
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const handleEvent = (payload: string): "done" | undefined => {
        if (payload === "[DONE]") return "done";
        let evt: {
          step?: string;
          status?: string;
          elapsed?: number;
          data?: { token?: string; message?: string; intent?: string };
        };
        try {
          evt = JSON.parse(payload);
        } catch {
          return; // 心跳注释行等非 JSON 载荷
        }
        const step = evt.step ?? "";

        if (step.endsWith("_token")) {
          const tok = evt.data?.token ?? "";
          if (tok) {
            text += tok;
            textDirty = true;
          }
          return;
        }
        if (step === "intent") {
          store.setIntent(evt.data?.intent ?? "chat");
          return;
        }
        if (evt.status === "progress") {
          store.setNodeStatus(step, "running", undefined, evt.data as Record<string, unknown>);
          return;
        }
        if (evt.status === "start" || evt.status === "done" || evt.status === "failed") {
          store.setNodeStatus(
            step,
            evt.status === "start" ? "running" : evt.status,
            evt.elapsed,
            evt.data as Record<string, unknown> | undefined,
          );
          // data_collector 完成后拉实时行情卡（REST，fail-open）
          if (evt.status === "done" && step === "data_collector") {
            const code = extractStockCode(query);
            if (code) void fetchQuote(code, seq);
          }
          return;
        }
        if (step === "error") {
          store.setError(evt.data?.message ?? "研究过程发生错误");
          return;
        }
        // 其余为图状态快照事件，忽略
      };

      const processFrame = function* (frame: string) {
        for (const line of frame.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          if (handleEvent(payload) === "done") {
            store.setRunning(false); store.markRunEnd();
            if (text.length > 200) store.setLastReport(text);
            if (text) {
              yield { content: [{ type: "text" as const, text: toDisplay(text) }] };
            }
            return "done";
          }
        }
        return undefined;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        // CRLF 归一化：兼容不同 SSE 实现
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const r = yield* processFrame(frame);
          if (r === "done") return;
          if (shouldYield()) yield* doYield();
        }
      }
      // flush 解码器残余 + 残余 buffer
      buffer += decoder.decode().replace(/\r\n/g, "\n");
      if (buffer.trim()) {
        const r = yield* processFrame(buffer);
        if (r === "done") return;
      }
      if (text) {
        if (text.length > 200) store.setLastReport(text);
        yield { content: [{ type: "text" as const, text: toDisplay(text) }] };
      }
      store.setRunning(false); store.markRunEnd();
    } catch (e) {
      // 用户主动停止（AbortError）不算错误，静默收场
      if (e instanceof DOMException && e.name === "AbortError") {
        store.setRunning(false); store.markRunEnd();
        return;
      }
      store.setError(e instanceof Error ? e.message : "研究请求失败，请重试");
      store.setRunning(false); store.markRunEnd();
    } finally {
      if (useGraphStore.getState().running) store.setRunning(false); store.markRunEnd();
    }
  },
};
