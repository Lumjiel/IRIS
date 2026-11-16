import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowDownRight,
  ArrowUpRight,
  AlertTriangle,
  FlaskConical,
  History,
  Layers,
  RefreshCw,
} from "lucide-react";

/* ============ 类型（与后端 /api/scenario/analyze 对齐） ============ */

interface ScenarioFactor {
  name: string;
  description: string;
  beneficiaries: string[];
  losers: string[];
}

interface ScenarioCase {
  event: string;
  time: string;
  summary: string;
  market_reactions: { target: string; reaction: string; source: string }[];
  relevance: string;
}

interface ScenarioImpact {
  target: string;
  direction: "up" | "down";
  probability: number;
  horizon: string;
  reasoning: string;
  drivers: string[];
  headwinds: string[];
  case_refs: string[];
}

interface ScenarioResult {
  ok: boolean;
  error?: string;
  scenario: string;
  factors: ScenarioFactor[];
  cases: ScenarioCase[];
  used_web: boolean;
  summary: string;
  impacts: ScenarioImpact[];
  confidence_note: string;
  degraded: string[];
  disclaimer: string;
}

const EXAMPLES = [
  "未来一年地缘战争增多，全球粮食欠收",
  "美联储进入持续降息周期",
  "国内房地产政策全面松绑",
  "AI 算力需求见顶回落",
];

const STAGES = [
  "拆解风险因子…",
  "联网检索历史类比案例…",
  "因子叠加推演与概率合成…",
];

/**
 * 情景推演面板：输入对未来的预测情景 → 方向 × 概率 × 依据链
 * 独立于聊天 Thread，通过顶栏切换进入
 */
export function ScenarioPanel() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState("");

  const canSubmit = input.trim().length > 0 && !loading;

  const analyze = async () => {
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    setResult(null);
    // 阶段提示动画（纯展示，实际后端一次性返回）
    const timer = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      4000,
    );
    try {
      const res = await fetch("/api/scenario/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: input.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "推演请求失败");
    } finally {
      clearInterval(timer);
      setLoading(false);
      setStage(0);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col overflow-y-auto px-4 py-6">
      {/* 标题区 */}
      <div className="mb-4 flex items-center gap-2">
        <FlaskConical className="size-5 text-violet-500" />
        <div>
          <h1 className="text-base font-semibold tracking-tight">情景推演</h1>
          <p className="text-xs text-muted-foreground">
            输入对未来的预测情景，基于历史类比推演 A 股板块涨跌方向与主观概率
          </p>
        </div>
      </div>

      {/* 输入区 */}
      <div className="space-y-2 rounded-xl border bg-card p-3">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value.slice(0, 500))}
          placeholder="描述你对未来的预测，例如：未来一年战争增多，粮食欠收…"
          className="min-h-20 resize-none border-0 bg-transparent px-1 text-sm shadow-none focus-visible:ring-0"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) analyze();
          }}
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] text-muted-foreground">
            {input.length}/500 · Ctrl+Enter 提交
          </span>
          <Button size="sm" onClick={analyze} disabled={!canSubmit}>
            {loading ? (
              <RefreshCw className="size-3.5 animate-spin" />
            ) : (
              "开始推演"
            )}
          </Button>
        </div>
        {/* 示例情景 */}
        {!result && !loading && (
          <div className="flex flex-wrap gap-1.5 border-t pt-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setInput(ex)}
                className="rounded-full border px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-violet-400 hover:text-violet-500"
              >
                {ex}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 加载中 */}
      {loading && (
        <div className="mt-6 space-y-2 rounded-xl border bg-card p-4">
          {STAGES.map((s, i) => (
            <div key={s} className="flex items-center gap-2 text-xs">
              {i < stage ? (
                <span className="text-emerald-500">✓</span>
              ) : i === stage ? (
                <RefreshCw className="size-3.5 animate-spin text-violet-500" />
              ) : (
                <span className="text-muted-foreground/40">○</span>
              )}
              <span className={cn(i > stage && "text-muted-foreground/40")}>{s}</span>
            </div>
          ))}
          <p className="pt-1 text-[11px] text-muted-foreground/70">
            通常需要 30-60 秒（含联网检索历史案例）
          </p>
        </div>
      )}

      {/* 错误 */}
      {error && (
        <div className="mt-6 flex items-start gap-2 rounded-xl border border-red-300 bg-red-500/10 p-3 text-xs text-red-600 dark:border-red-800 dark:text-red-400">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 结果 */}
      {result && (
        <div className="mt-6 space-y-4 pb-8">
          {result.degraded.length > 0 && (
            <div className="rounded-lg border border-amber-300 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-600 dark:border-amber-800 dark:text-amber-400">
              部分降级：{result.degraded.join("；")}
            </div>
          )}

          {/* 总结论 */}
          <div className="rounded-xl border bg-card p-4">
            <div className="mb-1.5 text-xs font-semibold text-muted-foreground">
              推演总结论
            </div>
            <p className="text-sm leading-relaxed">{result.summary}</p>
            {result.confidence_note && (
              <p className="mt-2 border-t pt-2 text-[11px] text-muted-foreground">
                置信度说明：{result.confidence_note}
              </p>
            )}
          </div>

          {/* 推演明细表 */}
          <div className="overflow-hidden rounded-xl border bg-card">
            <div className="border-b bg-muted/40 px-4 py-2 text-xs font-semibold">
              板块推演明细 · 按 |概率-50%| 降序
            </div>
            <div className="divide-y">
              {result.impacts.map((imp, i) => (
                <div key={i} className="space-y-2 px-4 py-3">
                  <div className="flex items-center gap-2">
                    {imp.direction === "up" ? (
                      <ArrowUpRight className="size-4 shrink-0 text-red-500" />
                    ) : (
                      <ArrowDownRight className="size-4 shrink-0 text-emerald-600" />
                    )}
                    <span className="text-sm font-semibold">{imp.target}</span>
                    <span
                      className={cn(
                        "font-mono text-sm font-bold",
                        imp.direction === "up" ? "text-red-500" : "text-emerald-600",
                      )}
                    >
                      {imp.direction === "up" ? "涨" : "跌"} {imp.probability}%
                    </span>
                    <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      {imp.horizon}
                    </span>
                  </div>
                  {/* 概率条 */}
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        imp.direction === "up" ? "bg-red-500" : "bg-emerald-500",
                      )}
                      style={{ width: `${imp.probability}%` }}
                    />
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {imp.reasoning}
                  </p>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                    {imp.drivers.map((d) => (
                      <span key={d} className="text-red-500/90">＋ {d}</span>
                    ))}
                    {imp.headwinds.map((d) => (
                      <span key={d} className="text-emerald-600/90">－ {d}</span>
                    ))}
                  </div>
                  {imp.case_refs.length > 0 && (
                    <div className="flex items-center gap-1 text-[11px] text-muted-foreground/80">
                      <History className="size-3" />
                      类比案例：{imp.case_refs.join("、")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* 因子拆解 */}
          {result.factors.length > 0 && (
            <div className="rounded-xl border bg-card p-4">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <Layers className="size-3.5 text-violet-500" />
                因子拆解
              </div>
              <div className="space-y-2">
                {result.factors.map((f, i) => (
                  <div key={i} className="text-xs">
                    <span className="font-medium">{f.name}</span>
                    <span className="text-muted-foreground"> — {f.description}</span>
                    <div className="mt-0.5 flex flex-wrap gap-1.5">
                      {f.beneficiaries.map((s) => (
                        <span key={s} className="rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] text-red-500">
                          {s} ↑
                        </span>
                      ))}
                      {f.losers.map((s) => (
                        <span key={s} className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-600">
                          {s} ↓
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 历史案例 */}
          {result.cases.length > 0 && (
            <div className="rounded-xl border bg-card">
              <div className="flex items-center gap-2 border-b bg-muted/40 px-4 py-2 text-xs font-semibold">
                <History className="size-3.5 text-violet-500" />
                历史类比案例
                <span
                  className={cn(
                    "ml-auto rounded-full px-2 py-0.5 text-[10px]",
                    result.used_web
                      ? "bg-emerald-500/10 text-emerald-600"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {result.used_web ? "已联网检索" : "模型知识"}
                </span>
              </div>
              <div className="divide-y">
                {result.cases.map((c, i) => (
                  <div key={i} className="space-y-1.5 px-4 py-3">
                    <div className="flex items-baseline gap-2">
                      <span className="text-sm font-medium">{c.event}</span>
                      <span className="text-[11px] text-muted-foreground">{c.time}</span>
                      <span
                        className={cn(
                          "ml-auto rounded px-1.5 text-[10px]",
                          c.relevance === "高"
                            ? "bg-violet-500/10 text-violet-500"
                            : "bg-muted text-muted-foreground",
                        )}
                      >
                        相关度 {c.relevance}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{c.summary}</p>
                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                      {c.market_reactions.map((r, j) => (
                        <span key={j}>
                          <span className="font-medium">{r.target}</span>
                          <span className="text-muted-foreground"> {r.reaction}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 免责声明 */}
          <div className="rounded-lg border border-dashed px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
            {result.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
}
