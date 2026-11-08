import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface SystemStatus {
  data_source: string;
  data_online: boolean;
  llm_degraded: boolean;
  primary_model: string;
  fallback_model: string;
}

/**
 * 系统状态卡：数据链在线状态 + 当前模型（30s 轮询 /api/status）
 */
export function StatusCard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    let alive = true;
    const fetchStatus = () =>
      fetch("/api/status")
        .then((r) => r.json())
        .then((s) => alive && setStatus(s))
        .catch(() => {});
    fetchStatus();
    const timer = setInterval(fetchStatus, 30_000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  if (!status) return null;

  return (
    <div className="space-y-2 rounded-lg border bg-card px-3 py-2.5 text-xs">
      <div className="flex items-center justify-between gap-2">
        <span className="text-muted-foreground">数据链</span>
        <span className="flex items-center gap-1.5 font-medium">
          <span
            className={cn(
              "size-1.5 rounded-full",
              status.data_online ? "bg-emerald-500" : "animate-pulse bg-amber-500",
            )}
          />
          {status.data_online ? "在线" : "降级"}
        </span>
      </div>
      <div className="truncate text-muted-foreground" title={status.data_source}>
        {status.data_source}
      </div>
      <div className="flex items-center justify-between gap-2 border-t pt-2">
        <span className="text-muted-foreground">主模型</span>
        <span className="font-mono text-[11px]">{status.primary_model}</span>
      </div>
      {status.llm_degraded && (
        <div className="rounded bg-amber-500/10 px-2 py-1 text-[11px] text-amber-600 dark:text-amber-400">
          主模型降级，当前使用备用模型
        </div>
      )}
    </div>
  );
}
