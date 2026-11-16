import { useCallback, useEffect, useState } from "react";
import { useAui } from "@assistant-ui/react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useGraphStore, type QuoteData } from "@/store/graphStore";
import {
  ArrowDownRight,
  ArrowUpRight,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  History,
  Layers,
  Loader2,
  RefreshCw,
  Sparkles,
  Star,
  Trash2,
  TrendingUp,
  XCircle,
} from "lucide-react";

/* ============ 类型（与后端 /api/scenario/* 对齐） ============ */

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
  run_id: number | null;
  saved?: boolean;
  created_at?: string;
}

interface HistoryItem {
  id: number;
  created_at: string;
  scenario: string;
  impact_count: number;
  top_impact: ScenarioImpact | null;
  verified: boolean;
}

interface VerifyItem {
  target: string;
  direction: "up" | "down";
  probability: number;
  base_date?: string;
  base_close?: number;
  latest_date?: string;
  latest_close?: number;
  pct_change?: number;
  hit?: boolean;
  code: string;
  error?: string;
}

interface VerifyResult {
  start_date: string;
  verifiable: VerifyItem[];
  unverifiable_count: number;
  hit_count: number;
  judgeable_count: number;
  hit_rate: number | null;
}

type StageKey = "decompose" | "analogy" | "synthesize";
interface StageState {
  key: StageKey;
  label: string;
  status: "pending" | "running" | "done";
}

const INITIAL_STAGES: StageState[] = [
  { key: "decompose", label: "拆解风险因子", status: "pending" },
  { key: "analogy", label: "联网检索历史类比案例", status: "pending" },
  { key: "synthesize", label: "因子叠加推演与概率合成", status: "pending" },
];

const EXAMPLES = [
  "未来一年地缘战争增多，全球粮食欠收",
  "美联储进入持续降息周期",
  "国内房地产政策全面松绑",
  "AI 算力需求见顶回落",
];

function extractCode(target: string): string | null {
  const m = target.match(/\d{6}/);
  return m ? m[0] : null;
}

interface WatchItem {
  code: string;
  name: string;
  added_at: string;
}

/** 推演条目联动：带代码的标的可查实时行情 / 一键转研报深入研究 / 加入自选对照 */
function ImpactActions({
  target,
  onAddWatch,
}: {
  target: string;
  onAddWatch: (code: string, name: string) => void;
}) {
  const code = extractCode(target);
  const aui = useAui();
  const setMode = useGraphStore((s) => s.setMode);
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  if (!code) return null;

  const name = target.replace(/\(?\d{6}\)?/g, "").replace(/[：:]/g, " ").trim() || code;

  const fetchQuote = async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/stock/${code}/quote`, { cache: "no-store" });
      const d = await r.json();
      setQuote((d.quote ?? d) as QuoteData);
      setOpen(true);
    } catch {
      /* fail-open */
    } finally {
      setLoading(false);
    }
  };

  const pct = quote?.涨跌幅 ? Number(quote.涨跌幅) : null;

  return (
    <div className="flex flex-wrap items-center gap-2 border-t pt-2 text-[11px]">
      {!open ? (
        <button
          onClick={() => void fetchQuote()}
          className="text-muted-foreground transition-colors hover:text-violet-500"
        >
          {loading ? "行情加载中…" : `📊 查 ${code} 实时行情`}
        </button>
      ) : (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-mono text-muted-foreground">{code}</span>
          <span className="font-semibold tabular-nums">{quote?.最新价 ?? "—"}</span>
          {pct !== null && !Number.isNaN(pct) && (
            <span
              className={cn(
                "font-medium tabular-nums",
                pct >= 0 ? "text-red-600" : "text-emerald-600",
              )}
            >
              {pct > 0 ? "+" : ""}
              {pct.toFixed(2)}%
            </span>
          )}
          {quote?.市盈率 && (
            <span className="text-muted-foreground">
              PE <span className="tabular-nums text-foreground">{quote.市盈率}</span>
            </span>
          )}
          {quote?.data_source && (
            <span className="text-muted-foreground/70" title={quote.data_source}>
              {quote.data_source}
            </span>
          )}
        </div>
      )}
      <button
        onClick={() => onAddWatch(code, name)}
        className="font-medium text-amber-600 transition-colors hover:text-amber-500"
        title="加入自选股对照"
      >
        ＋对照
      </button>
      <button
        onClick={() => {
          aui.thread.append(`研究一下 ${code} ${name} 的投资价值`);
          setMode("chat");
        }}
        className="font-medium text-violet-600 transition-colors hover:text-violet-500 dark:text-violet-400"
      >
        → 转研报深入研究
      </button>
    </div>
  );
}

/**
 * 情景推演面板：输入对未来的预测情景 → 方向 × 概率 × 依据链
 * 支持真进度 SSE、追加因子多轮推演、历史存档回看与事后走势验证
 */
export function ScenarioPanel() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [stages, setStages] = useState<StageState[]>(INITIAL_STAGES);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState("");
  const [round, setRound] = useState(1);

  // 追加因子
  const [appendInput, setAppendInput] = useState("");

  // 历史存档
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);

  // 事后验证
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);

  // 今日热点（懒人一键）
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestMode, setSuggestMode] = useState<"news" | "preset">("preset");
  const [suggestLoading, setSuggestLoading] = useState(true);

  // 输入结构引导：时间聚焦
  const FOCUS_OPTIONS = ["不限", "短期(1-2周)", "中期(1-3月)", "长期(半年以上)"];
  const [focus, setFocus] = useState("不限");

  // 自选股对照
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [wlInput, setWlInput] = useState("");
  const [wlError, setWlError] = useState("");

  const refreshWatchlist = useCallback(async () => {
    try {
      const r = await fetch("/api/watchlist", { cache: "no-store" });
      const d = await r.json();
      setWatchlist(d.items ?? []);
    } catch {
      /* fail-soft */
    }
  }, []);

  useEffect(() => {
    void refreshWatchlist();
  }, [refreshWatchlist]);

  const addWatch = useCallback(
    async (code: string, name: string) => {
      try {
        const r = await fetch("/api/watchlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, name }),
        });
        const d = await r.json();
        if (!r.ok) throw new Error(d.detail?.[0]?.msg ?? d.detail ?? "添加失败");
        void refreshWatchlist();
      } catch (e) {
        setWlError(e instanceof Error ? e.message : "添加失败");
      }
    },
    [refreshWatchlist],
  );

  const removeWatch = useCallback(
    async (code: string) => {
      try {
        await fetch(`/api/watchlist/${code}`, { method: "DELETE" });
        void refreshWatchlist();
      } catch {
        /* 忽略 */
      }
    },
    [refreshWatchlist],
  );

  useEffect(() => {
    let alive = true;
    fetch("/api/scenario/suggest", { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => {
        if (!alive) return;
        setSuggestions(d.suggestions ?? []);
        setSuggestMode(d.mode ?? "preset");
      })
      .catch(() => {})
      .finally(() => alive && setSuggestLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const canSubmit = input.trim().length > 0 && !loading;

  const refreshHistory = useCallback(async () => {
    try {
      const r = await fetch("/api/scenario/history");
      const d = await r.json();
      setHistory(d.runs ?? []);
    } catch {
      /* 历史加载失败不影响主流程 */
    }
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  /** 核心：SSE 消费一次推演（真实阶段进度 → 最终结果） */
  const analyze = async (scenarioText: string) => {
    if (!scenarioText.trim() || loading) return;
    // 时间聚焦：拼接进情景文本，让推演聚焦对应时间窗
    const merged =
      focus !== "不限" ? `${scenarioText.trim()}（请重点关注${focus}的影响）` : scenarioText.trim();
    setLoading(true);
    setError("");
    setResult(null);
    setVerify(null);
    setStages(INITIAL_STAGES.map((s) => ({
      ...s,
      status: s.key === "decompose" ? "running" : "pending",
    })));
    try {
      const res = await fetch("/api/scenario/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: merged }),
      });
      if (!res.ok || !res.body) {
        const d = await res.json().catch(() => null);
        const msg = d?.detail?.[0]?.msg ?? d?.detail ?? `HTTP ${res.status}`;
        throw new Error(String(msg));
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = "";
      let gotResult = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          const t = line.trim();
          if (!t.startsWith("data:")) continue;
          const ev = JSON.parse(t.slice(5).trim());
          if (ev.type === "stage") {
            const { key, status } = ev as { key: StageKey; status: "start" | "done" };
            setStages((prev) =>
              prev.map((s) =>
                s.key === key
                  ? { ...s, status: status === "start" ? ("running" as const) : ("done" as const) }
                  : s,
              ),
            );
            // done 时把下一阶段置为 running
            if (status === "done") {
              setStages((prev) => {
                const idx = prev.findIndex((s) => s.key === key);
                return prev.map((s, i) =>
                  i === idx + 1 ? { ...s, status: "running" as const } : s,
                );
              });
            }
          } else if (ev.type === "result") {
            gotResult = true;
            setResult(ev.data as ScenarioResult);
            void refreshHistory();
          } else if (ev.type === "error") {
            throw new Error(ev.detail ?? "推演失败");
          }
        }
      }
      if (!gotResult) throw new Error("推演流意外中断");
    } catch (e) {
      setError(e instanceof Error ? e.message : "推演请求失败");
    } finally {
      setLoading(false);
    }
  };

  /** 追加因子：并入原情景重新推演（第 N 轮） */
  const runAppend = () => {
    const add = appendInput.trim();
    if (!add || !result || loading) return;
    const merged = `${result.scenario}；另外：${add}`;
    setRound((r) => r + 1);
    setInput(merged.slice(0, 500));
    void analyze(merged.slice(0, 500));
    setAppendInput("");
  };

  /** 加载一条历史存档到主视图 */
  const loadRun = async (id: number) => {
    if (loading) return;
    setError("");
    setVerify(null);
    try {
      const r = await fetch(`/api/scenario/history/${id}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "加载失败");
      setResult(d.payload as ScenarioResult);
      setInput(d.scenario ?? "");
      setRound(1);
      setVerify(d.verify ?? null);
      setHistoryOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  };

  const deleteRun = async (id: number) => {
    try {
      await fetch(`/api/scenario/history/${id}`, { method: "DELETE" });
      if (result?.run_id === id) setResult(null);
      void refreshHistory();
    } catch {
      /* 忽略 */
    }
  };

  /** 事后验证：推演日至今实际涨跌 */
  const runVerify = async () => {
    if (!result?.run_id || verifying) return;
    setVerifying(true);
    try {
      const r = await fetch(`/api/scenario/history/${result.run_id}/verify`, {
        method: "POST",
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail ?? "验证失败");
      setVerify(d as VerifyResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "验证失败");
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col overflow-y-auto px-4 py-6">
      {/* 标题区 */}
      <div className="mb-4 flex items-center gap-2">
        <FlaskConical className="size-5 text-violet-500" />
        <div>
          <h1 className="text-base font-semibold tracking-tight">
            情景推演
            {round > 1 && (
              <span className="ml-2 rounded-full bg-violet-500/10 px-2 py-0.5 text-[11px] font-normal text-violet-500">
                第 {round} 轮
              </span>
            )}
          </h1>
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
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void analyze(input);
          }}
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] text-muted-foreground">
            {input.length}/500 · Ctrl+Enter 提交
          </span>
          <Button size="sm" onClick={() => void analyze(input)} disabled={!canSubmit}>
            {loading ? (
              <RefreshCw className="size-3.5 animate-spin" />
            ) : (
              "开始推演"
            )}
          </Button>
        </div>
        {/* 时间聚焦：结构化引导，降低"不知道写多细"的门槛 */}
        {!loading && (
          <div className="flex flex-wrap items-center gap-1.5 border-t pt-2">
            <span className="text-[11px] text-muted-foreground">时间聚焦</span>
            {FOCUS_OPTIONS.map((f) => (
              <button
                key={f}
                onClick={() => setFocus(f)}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-[11px] transition-colors",
                  focus === f
                    ? "border-violet-400 bg-violet-500/10 text-violet-600 dark:text-violet-400"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {f}
              </button>
            ))}
          </div>
        )}
        {/* 今日热点（懒人一键） / 示例情景 */}
        {!result && !loading && (
          <div className="border-t pt-2">
            {suggestLoading ? (
              <div className="flex flex-wrap gap-1.5">
                {[0, 1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-6 animate-pulse rounded-full bg-muted"
                    style={{ width: `${140 + i * 24}px` }}
                  />
                ))}
              </div>
            ) : suggestions.length > 0 ? (
              <>
                <div className="mb-1.5 flex items-center gap-1.5">
                  <Sparkles className="size-3.5 text-violet-500" />
                  <span className="text-[11px] text-muted-foreground">
                    今日热点 · 点一下直接推演
                  </span>
                  <span
                    className={cn(
                      "rounded px-1.5 py-0.5 text-[10px]",
                      suggestMode === "news"
                        ? "bg-emerald-500/10 text-emerald-600"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {suggestMode === "news" ? "实时快讯" : "预设"}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setInput(s);
                        void analyze(s);
                      }}
                      className="rounded-full border border-violet-300/60 bg-violet-500/5 px-2.5 py-1 text-[11px] text-violet-600 transition-colors hover:bg-violet-500/15 dark:border-violet-700/60 dark:text-violet-400"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex flex-wrap gap-1.5">
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
        )}
        {/* 历史存档折叠条 */}
        <div className="border-t pt-2">
          <button
            onClick={() => setHistoryOpen((v) => !v)}
            className="flex w-full items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
          >
            {historyOpen ? (
              <ChevronDown className="size-3.5" />
            ) : (
              <ChevronRight className="size-3.5" />
            )}
            <History className="size-3.5" />
            历史推演（{history.length}）
          </button>
          {historyOpen && (
            <div className="mt-2 max-h-64 space-y-1.5 overflow-y-auto">
              {history.length === 0 && (
                <p className="px-1 text-[11px] text-muted-foreground/60">
                  还没有存档。每次推演会自动保存，之后可以回看并验证走势。
                </p>
              )}
              {history.map((h) => (
                <div
                  key={h.id}
                  className="group flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[11px] hover:bg-muted/50"
                >
                  <button
                    className="min-w-0 flex-1 text-left"
                    onClick={() => void loadRun(h.id)}
                  >
                    <div className="truncate font-medium">{h.scenario}</div>
                    <div className="text-muted-foreground">
                      {h.created_at} · {h.impact_count} 条推演
                      {h.verified && (
                        <span className="ml-1 text-emerald-600">· 已验证</span>
                      )}
                    </div>
                  </button>
                  <button
                    aria-label="删除存档"
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    onClick={() => void deleteRun(h.id)}
                  >
                    <Trash2 className="size-3.5 text-muted-foreground hover:text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 加载中：真实阶段进度 */}
      {loading && (
        <div className="mt-6 space-y-2 rounded-xl border bg-card p-4">
          {stages.map((s) => (
            <div key={s.key} className="flex items-center gap-2 text-xs">
              {s.status === "done" ? (
                <CheckCircle2 className="size-3.5 text-emerald-500" />
              ) : s.status === "running" ? (
                <Loader2 className="size-3.5 animate-spin text-violet-500" />
              ) : (
                <span className="text-muted-foreground/40">○</span>
              )}
              <span className={cn(s.status === "pending" && "text-muted-foreground/40")}>
                {s.label}
              </span>
            </div>
          ))}
          <p className="pt-1 text-[11px] text-muted-foreground/70">
            含联网检索历史案例，通常 1-2 分钟；关闭页面不会中断后台推演
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
            <div className="mb-1.5 flex items-center justify-between text-xs font-semibold text-muted-foreground">
              <span>推演总结论</span>
              {result.created_at && (
                <span className="text-[10px] font-normal">
                  {result.created_at}
                  {result.saved && " · 已存档"}
                </span>
              )}
            </div>
            <p className="text-sm leading-relaxed">{result.summary}</p>
            {result.confidence_note && (
              <p className="mt-2 border-t pt-2 text-[11px] text-muted-foreground">
                置信度说明：{result.confidence_note}
              </p>
            )}
          </div>

          {/* 自选股对照：这个情景对我的持仓意味着什么 */}
          <div className="rounded-xl border bg-card">
            <div className="flex items-center gap-2 border-b bg-muted/40 px-4 py-2 text-xs font-semibold">
              <Star className="size-3.5 text-amber-500" />
              自选股对照
              <span className="text-[10px] font-normal text-muted-foreground">
                这个情景对你关注的标的意味着什么
              </span>
              <div className="ml-auto flex items-center gap-1.5">
                <input
                  value={wlInput}
                  onChange={(e) => setWlInput(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="6位代码"
                  className="h-6 w-20 rounded border bg-transparent px-1.5 text-[11px] tabular-nums outline-none focus:border-violet-400"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && wlInput.length === 6) {
                      void addWatch(wlInput, "");
                      setWlInput("");
                    }
                  }}
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="h-6 px-2 text-[11px]"
                  disabled={wlInput.length !== 6}
                  onClick={() => {
                    void addWatch(wlInput, "");
                    setWlInput("");
                  }}
                >
                  添加
                </Button>
              </div>
            </div>
            {wlError && (
              <p className="px-4 pt-2 text-[11px] text-red-500">{wlError}</p>
            )}
            {watchlist.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-muted-foreground">
                还没有自选股。点下方推演条目的「＋对照」，或输入 6 位代码添加，之后每次推演都会自动告诉你它受何影响。
              </p>
            ) : (
              <div className="divide-y">
                {watchlist.map((w) => {
                  const hit = result.impacts.find(
                    (imp) => !!extractCode(imp.target) && extractCode(imp.target) === w.code,
                  );
                  return (
                    <div key={w.code} className="flex items-center gap-2 px-4 py-2.5 text-xs">
                      <span className="font-mono text-[11px] text-muted-foreground">{w.code}</span>
                      <span className="min-w-0 flex-1 truncate font-medium">
                        {w.name || w.code}
                      </span>
                      {hit ? (
                        <>
                          <span
                            className={cn(
                              "rounded px-1.5 py-0.5 text-[11px] font-medium",
                              hit.direction === "up"
                                ? "bg-red-500/10 text-red-500"
                                : "bg-emerald-500/10 text-emerald-600",
                            )}
                          >
                            {hit.direction === "up" ? "涨" : "跌"} {hit.probability}% ·{" "}
                            {hit.horizon}
                          </span>
                        </>
                      ) : (
                        <span className="text-[11px] text-muted-foreground/70">
                          本次推演未直接涉及
                        </span>
                      )}
                      <button
                        aria-label="移除自选股"
                        onClick={() => void removeWatch(w.code)}
                        className="text-muted-foreground/60 transition-colors hover:text-red-500"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* 事后验证区 */}
          {result.run_id && (
            <div className="rounded-xl border bg-card">
              <div className="flex items-center gap-2 border-b bg-muted/40 px-4 py-2 text-xs font-semibold">
                <TrendingUp className="size-3.5 text-violet-500" />
                事后走势验证
                <Button
                  size="sm"
                  variant="outline"
                  className="ml-auto h-6 px-2 text-[11px]"
                  onClick={() => void runVerify()}
                  disabled={verifying}
                >
                  {verifying ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : verify ? (
                    "重新验证"
                  ) : (
                    "验证走势"
                  )}
                </Button>
              </div>
              {verify ? (
                <div className="px-4 py-3">
                  {verify.judgeable_count > 0 ? (
                    <div className="space-y-2">
                      <div className="text-[11px] text-muted-foreground">
                        推演日 {verify.start_date} 至今 · 方向命中{" "}
                        <span
                          className={cn(
                            "font-semibold",
                            (verify.hit_rate ?? 0) >= 50
                              ? "text-emerald-600"
                              : "text-red-500",
                          )}
                        >
                          {verify.hit_count}/{verify.judgeable_count}（{verify.hit_rate}%）
                        </span>
                      </div>
                      {verify.verifiable.map((v, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 border-t pt-2 text-xs first:border-t-0 first:pt-0"
                        >
                          {v.error ? (
                            <AlertTriangle className="size-3.5 shrink-0 text-amber-500" />
                          ) : v.hit ? (
                            <CheckCircle2 className="size-3.5 shrink-0 text-emerald-500" />
                          ) : (
                            <XCircle className="size-3.5 shrink-0 text-red-500" />
                          )}
                          <span className="min-w-0 flex-1 truncate">{v.target}</span>
                          <span className="text-muted-foreground">
                            预测{v.direction === "up" ? "涨" : "跌"} {v.probability}%
                          </span>
                          {v.error ? (
                            <span className="text-[10px] text-amber-600">{v.error}</span>
                          ) : (
                            <span
                              className={cn(
                                "font-mono font-semibold",
                                (v.pct_change ?? 0) > 0 ? "text-red-500" : "text-emerald-600",
                              )}
                            >
                              {(v.pct_change ?? 0) > 0 ? "+" : ""}
                              {v.pct_change}%
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">
                      本次推演无可识别股票代码的标的，暂无法自动验证。
                    </p>
                  )}
                  {verify.unverifiable_count > 0 && (
                    <p className="mt-2 text-[10px] text-muted-foreground/70">
                      另有 {verify.unverifiable_count} 条板块级推演无法自动验证（纯板块目标）。
                    </p>
                  )}
                </div>
              ) : (
                <p className="px-4 py-3 text-[11px] text-muted-foreground">
                  推演只是起点——点「验证走势」查看推演日至今的实际涨跌，校准概率是否靠谱。
                </p>
              )}
            </div>
          )}

          {/* 追加因子：多轮推演 */}
          <div className="rounded-xl border border-dashed bg-card p-3">
            <div className="flex items-center gap-2">
              <Textarea
                value={appendInput}
                onChange={(e) => setAppendInput(e.target.value.slice(0, 200))}
                placeholder="追加因子再推演，例如：如果央行同时降息呢？"
                className="min-h-10 resize-none border-0 bg-transparent px-1 text-xs shadow-none focus-visible:ring-0"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    runAppend();
                  }
                }}
              />
              <Button
                size="sm"
                variant="secondary"
                className="h-8 shrink-0"
                onClick={runAppend}
                disabled={!appendInput.trim() || loading}
              >
                并入推演
              </Button>
            </div>
          </div>

          {/* 推演明细表 */}
          <div className="overflow-hidden rounded-xl border bg-card">
            <div className="border-b bg-muted/40 px-4 py-2 text-xs font-semibold">
              板块推演明细 · 主观情景概率 · 按 |概率-50%| 降序
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
                      title="主观情景概率：基于历史类比与因子逻辑的估计，非统计精确值"
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
                  {/* 联动：查行情 / 转研报 / 加入对照 */}
                  <ImpactActions target={imp.target} onAddWatch={(c, n) => void addWatch(c, n)} />
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
