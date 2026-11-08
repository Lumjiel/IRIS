import { useGraphStore, NODE_LABELS } from "@/store/graphStore";
import { cn } from "@/lib/utils";

/**
 * 多 Agent 研究过程时间线：消费后端节点 start/done 事件，展示真实进度与耗时。
 */
export function ResearchTimeline() {
  const nodes = useGraphStore((s) => s.nodes);
  const order = useGraphStore((s) => s.order);
  const error = useGraphStore((s) => s.error);
  const running = useGraphStore((s) => s.running);

  const preparing = running && order.length === 0 && !error;
  if (preparing === false && order.length === 0 && !error) return null;

  return (
    <div
      data-slot="iris_timeline"
      className="sticky top-0 z-10 mx-auto w-full max-w-3xl px-4 pb-2 pt-2"
    >
      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card/80 px-4 py-3 text-xs shadow-sm backdrop-blur">
        <span className="mr-1 font-medium text-muted-foreground">
          研究进程
        </span>
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
