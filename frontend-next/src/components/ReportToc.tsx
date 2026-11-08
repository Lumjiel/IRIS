import { useEffect, useState } from "react";
import { useGraphStore } from "@/store/graphStore";
import { cn } from "@/lib/utils";

/**
 * 研报目录（右栏）：解析报告 ## 标题，点击滚动定位，滚动高亮当前章节。
 * 依赖消息流里已渲染的 .aui-md h2 元素做定位与 Spy。
 */
export function ReportToc() {
  const lastReport = useGraphStore((s) => s.lastReport);
  const running = useGraphStore((s) => s.running);
  const [sections, setSections] = useState<string[]>([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (!lastReport) {
      setSections([]);
      return;
    }
    setSections(
      lastReport
        .split("\n")
        .filter((l) => l.startsWith("## "))
        .map((l) => l.replace(/^##\s+/, "").trim()),
    );
  }, [lastReport]);

  useEffect(() => {
    if (running || sections.length === 0) return;
    const container = document.querySelector("[data-slot='aui_thread-viewport']") as HTMLElement | null;
    const scrollRoot = container?.parentElement ?? document;
    const onScroll = () => {
      const headings = Array.from(document.querySelectorAll<HTMLElement>(".aui-md h2"));
      if (headings.length === 0) return;
      let current = 0;
      headings.forEach((h, i) => {
        if (h.getBoundingClientRect().top < window.innerHeight * 0.4) current = i;
      });
      setActive(current);
    };
    scrollRoot.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => scrollRoot.removeEventListener("scroll", onScroll);
  }, [running, sections]);

  if (running || sections.length === 0) return null;

  const jump = (idx: number) => {
    const headings = Array.from(document.querySelectorAll<HTMLElement>(".aui-md h2"));
    headings[idx]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <nav data-slot="iris_toc" className="text-xs">
      <div className="mb-2 font-medium text-muted-foreground">报告目录</div>
      <ol className="space-y-1">
        {sections.map((t, i) => (
          <li key={i}>
            <button
              onClick={() => jump(i)}
              className={cn(
                "w-full truncate rounded px-2 py-1 text-left transition-colors",
                i === active
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
              title={t}
            >
              {t}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
