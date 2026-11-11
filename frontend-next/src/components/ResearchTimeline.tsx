import { useEffect, useState } from "react";
import { useGraphStore, NODE_LABELS } from "@/store/graphStore";
import { cn } from "@/lib/utils";

/**
 * 多 Agent 研究过程时间线：消费后端节点 start/done 事件，展示真实进度与耗时。
 */
function fmtElapsed(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const sec = total % 60;
  return m > 0 ? `${m}m${String(sec).padStart(2, "0")}s` : `${sec}s`;
}

export function ResearchTimeline() {
  const nodes = useGraphStore((s) => s.nodes);
  const order = useGraphStore((s) => s.order);
  const error = useGraphStore((s) => s.error);
  const running = useGraphStore((s) => s.running);
  const startedAt = useGraphStore((s) => s.startedAt);
  const searchLog = useGraphStore((s) => s.searchLog);
  const chapterLog = useGraphStore((s) => s.chapterLog);

  // 总耗时计时器：运行中每秒走针
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  const preparing = running && order.length === 0 && !error;
  if (preparing === false && order.length === 0 && !error) return null;

  return (
    <div
      data-slot="iris_timeline"
      className="mx-auto w-full max-w-3xl px-4 pb-2 pt-2"
    >
      <div className="flex max-h-[55vh] flex-wrap items-center gap-2 overflow-y-auto rounded-xl border bg-card/80 px-4 py-3 text-xs shadow-sm backdrop-blur">
        <span className="mr-1 font-medium text-muted-foreground">
          研究进程
        </span>
        {running && startedAt && (
          <span className="rounded-full bg-primary/10 px-2 py-1 font-mono tabular-nums text-primary">
            {fmtElapsed(Date.now() - startedAt)}
          </span>
        )}
        {order.map((step) => {
          const n = nodes[step];
          const label = NODE_LABELS[step] ?? step;
          return (
            <span
              key={step}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium transition-colors",
                n.status === "running" &&
                  "border-primary/40 bg-primary/10 text-primary",
                n.status === "done" &&
                  "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                n.status === "failed" && "border-destructive/40 bg-destructive/10 text-destructive",
              )}
            >
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  n.status === "running" && "animate-pulse bg-primary",
                  n.status === "done" && "bg-emerald-500",
                  n.status === "failed" && "bg-destructive",
                )}
              />
              {label}
              {n.status === "done" && Number.isFinite(n.elapsed) && (
                <span className="tabular-nums opacity-70">
                  {Number(n.elapsed).toFixed(1)}s
                </span>
              )}
            </span>
          );
        })}
        {chapterLog.length > 0 && (
          <div className="w-full border-t pt-2 text-muted-foreground">
            <div className="mb-1 font-medium">分章撰写进度</div>
            <div className="flex flex-wrap gap-1.5">
              {chapterLog.map((c) => (
                <span
                  key={c}
                  className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-emerald-600 dark:text-emerald-400"
                >
                  ✓ {c}
                </span>
              ))}
            </div>
          </div>
        )}
        {searchLog.length > 0 && (
          <div className="w-full border-t pt-2 text-muted-foreground">
            <div className="mb-1 font-medium">搜索轨迹（LLM 自主决策）</div>
            <ol className="space-y-0.5">
              {searchLog.slice(-4).map((q, i) => (
                <li key={`${i}-${q}`} className="flex gap-2 leading-5">
                  <span className="shrink-0 tabular-nums opacity-60">
                    {String(searchLog.length - Math.min(searchLog.length, 4) + i + 1).padStart(2, "0")}
                  </span>
                  <span className="truncate" title={q}>{q}</span>
                </li>
              ))}
            </ol>
            {searchLog.length > 4 && (
              <div className="mt-1 opacity-60">…共 {searchLog.length} 次</div>
            )}
          </div>
        )}
        {preparing && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary/10 px-2.5 py-1 font-medium text-primary">
            <span className="size-1.5 animate-pulse rounded-full bg-primary" />
            研究准备中…
          </span>
        )}
      </div>
      {error && (
        <div className="mt-2 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-xs text-destructive">
          {error}
        </div>
      )}
    </div>
  );
}
