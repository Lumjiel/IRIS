import { useGraphStore, NODE_LABELS } from "@/store/graphStore";
import { cn } from "@/lib/utils";

/**
 * 多 Agent 研究过程时间线：消费后端节点 start/done 事件，展示真实进度与耗时。
 */
export function ResearchTimeline() {
  const { nodes, order, error, running } = useGraphStore();

  if (order.length === 0 && !error) return null;

  return (
    <div
      data-slot="iris_timeline"
      className="mx-auto w-full max-w-3xl px-4 pb-2"
    >
      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card/60 px-4 py-3 text-xs shadow-sm">
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
              {n.status === "done" && n.elapsed != null && (
                <span className="tabular-nums opacity-70">
                  {n.elapsed.toFixed(1)}s
                </span>
              )}
            </span>
          );
        })}
        {running && order.length === 0 && (
          <span className="text-muted-foreground">连接中…</span>
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
