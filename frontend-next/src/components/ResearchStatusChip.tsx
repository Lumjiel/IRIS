import { useEffect, useState } from "react";
import { useGraphStore, NODE_LABELS } from "@/store/graphStore";

/**
 * 顶栏研究状态 chip：运行中常驻顶栏（不挡内容区），显示当前节点 + 总耗时，
 * 点击平滑滚动到消息流里的完整研究时间线。运行结束自动消失。
 */
export function ResearchStatusChip() {
  const running = useGraphStore((s) => s.running);
  const nodes = useGraphStore((s) => s.nodes);
  const order = useGraphStore((s) => s.order);
  const startedAt = useGraphStore((s) => s.startedAt);

  // 运行中每秒走针
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  if (!running || !startedAt) return null;

  // 当前节点：最后一个 running 的节点；都没有则取最新进入的节点
  const current =
    [...order].reverse().find((s) => nodes[s]?.status === "running") ??
    order[order.length - 1];
  const label = current ? (NODE_LABELS[current] ?? current) : "准备中";

  const total = Math.floor((Date.now() - startedAt) / 1000);
  const m = Math.floor(total / 60);
  // 固定 mm:ss 格式：宽度恒定，避免每秒走针引起顶栏抖动
  const clock = `${String(m).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;

  return (
    <button
      type="button"
      data-slot="iris_status_chip"
      onClick={() =>
        document
          .querySelector('[data-slot="iris_timeline"]')
          ?.scrollIntoView({ behavior: "smooth", block: "start" })
      }
      title="点击查看研究进程详情"
      className="flex h-7 shrink-0 items-center gap-1.5 rounded-full border bg-card/80 px-2.5 text-xs shadow-sm transition-colors hover:bg-accent"
    >
      <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-primary" />
      <span className="shrink-0 font-medium text-primary">研究中</span>
      <span className="max-w-36 truncate text-muted-foreground">{label}</span>
      <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
        {clock}
      </span>
    </button>
  );
}
