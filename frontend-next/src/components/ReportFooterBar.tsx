import { useEffect, useRef, useState } from "react";
import { useAui } from "@assistant-ui/react";
import { CheckIcon, CopyIcon, DownloadIcon } from "lucide-react";
import { useGraphStore } from "@/store/graphStore";
import { Button } from "@/components/ui/button";

const FOLLOW_UPS = [
  "展开风险章节，补充数据依据",
  "对比同行业主要公司的估值水平",
  "把核心结论压缩成三句话",
];

/**
 * 研报完成后的底部条：导出 .md / 复制全文 + 追问引导 chips。
 * 仅在研究生成过长文本报告后出现。
 */
export function ReportFooterBar() {
  const aui = useAui();
  const lastReport = useGraphStore((s) => s.lastReport);
  const running = useGraphStore((s) => s.running);
  const [copied, setCopied] = useState<null | "ok" | "fail">(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timerRef.current), []);
  const visible = !running && lastReport != null && lastReport.length > 200;
  if (!visible) return null;

  const report = lastReport!;

  const download = () => {
    const firstHeading = report.match(/^#\s+(.+)$/m)?.[1]?.trim();
    const name = firstHeading
      ? `${firstHeading.slice(0, 40).replace(/[\/:*?"<>|]/g, "")}.md`
      : `IRIS研报-${new Date().toISOString().slice(0, 10)}.md`;
    const blob = new Blob([report], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); // Firefox 需要延迟 revoke
  };

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopied("ok");
    } catch {
      setCopied("fail");
    }
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div
      data-slot="iris_report_footer"
      className="mx-auto w-full max-w-3xl px-4 pb-2"
    >
      <div className="flex flex-wrap items-center gap-2 rounded-xl border bg-card px-4 py-2.5 text-xs shadow-sm">
        <span className="font-medium">研报已生成</span>
        <Button
          variant="outline"
          size="sm"
          className="h-7 gap-1.5 text-xs"
          onClick={download}
        >
          <DownloadIcon className="size-3.5" />
          下载 .md
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 gap-1.5 text-xs"
          onClick={copyAll}
        >
          {copied === "ok" ? (
            <CheckIcon className="size-3.5 text-emerald-500" />
          ) : (
            <CopyIcon className="size-3.5" />
          )}
          {copied === "ok" ? "已复制" : copied === "fail" ? "复制失败" : "复制全文"}
        </Button>
        <span className="ml-auto hidden text-muted-foreground sm:inline">
          继续追问：
        </span>
        {FOLLOW_UPS.map((q) => (
          <button
            key={q}
            onClick={() => aui.thread.append(q)}
            className="rounded-full border bg-background px-3 py-1 text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
