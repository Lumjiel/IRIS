import { useAui } from "@assistant-ui/react";
import { FlaskConical } from "lucide-react";
import { useGraphStore } from "@/store/graphStore";

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
  const setMode = useGraphStore((s) => s.setMode);
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
      {/* 情景推演引导：让用户知道还有第二个能力 */}
      <button
        onClick={() => setMode("scenario")}
        className="mt-3 flex max-w-md items-center gap-2.5 rounded-xl border border-violet-300/60 bg-violet-500/5 px-4 py-2.5 text-left text-xs transition-colors hover:bg-violet-500/10 dark:border-violet-700/60"
      >
        <FlaskConical className="size-4 shrink-0 text-violet-500" />
        <span className="text-muted-foreground">
          想预判"如果战争增多、粮食欠收，哪些板块会动"？
          <span className="font-medium text-violet-600 dark:text-violet-400">
            试试情景推演 →
          </span>
        </span>
      </button>
    </div>
  );
}
