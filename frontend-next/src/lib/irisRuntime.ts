import { type ChatModelAdapter } from "@assistant-ui/react";
import { useGraphStore } from "@/store/graphStore";

/**
 * IRIS 后端 SSE → assistant-ui LocalRuntime 适配器。
 *
 * 后端事件流（POST /api/chat，全部为 `data: {json}` 行）：
 * - {step:"intent", data:{intent, route, elapsed}}          意图判定
 * - {step:"<node>_token", data:{token, final?}}             报告/回复 token（writer/refiner）
 * - {step:"<node>", status:"start"|"done", elapsed?, data?} 节点状态事件（时间线）
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

    let text = "";
    let textDirty = false;

    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        search_mode: "hybrid",
        thread_id: `web-${Date.now().toString(36)}`,
        style: "detailed",
        language: "zh",
      }),
      signal: abortSignal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`后端请求失败: ${res.status}`);
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
      if (evt.status === "start" || evt.status === "done") {
        store.setNodeStatus(step, evt.status === "start" ? "running" : "done", evt.elapsed);
        return;
      }
      if (step === "error") {
        store.setError(evt.data?.message ?? "研究过程发生错误");
        return;
      }
      // 其余为图状态快照事件，忽略
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        for (const line of rawEvent.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          if (handleEvent(payload) === "done") {
            store.setRunning(false);
            if (textDirty) {
              yield { content: [{ type: "text" as const, text }] };
            }
            return;
          }
        }
        if (textDirty) {
          yield { content: [{ type: "text" as const, text }] };
          textDirty = false;
        }
      }
    }

    store.setRunning(false);
    if (text) {
      yield { content: [{ type: "text" as const, text }] };
    }
  },
};
