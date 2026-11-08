import { useState } from "react";
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
  const { lastReport, running } = useGraphStore();
  const [copied, setCopied] = useState(false);
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
    URL.revokeObjectURL(url);
  };

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* 剪贴板权限失败时静默 */
    }
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
          {copied ? (
            <CheckIcon className="size-3.5 text-emerald-500" />
          ) : (
            <CopyIcon className="size-3.5" />
          )}
          {copied ? "已复制" : "复制全文"}
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
