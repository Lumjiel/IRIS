import { useAui } from "@assistant-ui/react";

const PROMPTS = [
  "研究一下 600196 复星医药的投资价值",
  "研究一下 000001 平安银行的投资价值",
  "研究一下 600519 贵州茅台的投资价值",
];

/**
 * IRIS 品牌欢迎页（覆盖 assistant-ui 默认 Welcome 插槽）
 */
export function Welcome() {
  const aui = useAui();
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <h1 className="text-xl font-semibold tracking-tight">
        IRIS · A 股投研多智能体平台
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">
        输入股票代码或名称，多 Agent 协作完成
        检索 → 数据拉取 → 撰写 → 审查 全流程，生成六章节中文研报。
      </p>
      <div className="mt-2 flex flex-wrap justify-center gap-2">
        {PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => aui.thread.append(p)}
            className="rounded-full border bg-card px-3.5 py-1.5 text-xs text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
