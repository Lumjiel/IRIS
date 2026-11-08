import { createLocalStorageAdapter } from "@assistant-ui/core/react";
import type { ThreadMessage } from "@assistant-ui/react";

/**
 * 会话持久层：官方 createLocalStorageAdapter（元数据 + 消息 + 自动挂 history）。
 * 标题生成器自定义为中文截断风格。
 */

const storage = {
  getItem: (key: string) => Promise.resolve(localStorage.getItem(key)),
  setItem: (key: string, value: string) =>
    Promise.resolve(localStorage.setItem(key, value)),
  removeItem: (key: string) => Promise.resolve(localStorage.removeItem(key)),
};

async function makeTitle(messages: readonly ThreadMessage[]): Promise<string> {
  const first = messages.find((m) => m.role === "user");
  const text =
    first?.content
      .filter((p): p is { type: "text"; text: string } => p.type === "text")
      .map((p) => p.text)
      .join(" ") ?? "";
  const t = text.trim().replace(/\s+/g, " ");
  return t.length > 24 ? `${t.slice(0, 24)}…` : t || "新的研究";
}

export const irisThreadListAdapter = createLocalStorageAdapter({
  storage,
  prefix: "iris:",
  titleGenerator: { generateTitle: makeTitle },
});
