import { useEffect, useState } from "react";
import {
  AssistantRuntimeProvider,
  useAuiState,
  useLocalRuntime,
  useRemoteThreadListRuntime,
} from "@assistant-ui/react";
import {
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
} from "lucide-react";
import { Thread } from "@/components/assistant-ui/elements/thread.aui";
import { ThreadList } from "@/components/assistant-ui/elements/thread-list.aui";
import { IrisModelAdapter } from "@/lib/irisRuntime";
import { irisThreadListAdapter } from "@/lib/threadStore";
import { ResearchTimeline } from "@/components/ResearchTimeline";
import { ResearchStatusChip } from "@/components/ResearchStatusChip";
import { MarketDataCard } from "@/components/MarketDataCard";
import { ReportFooterBar } from "@/components/ReportFooterBar";
import { Welcome } from "@/components/Welcome";
import { StatusCard } from "@/components/StatusCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ReportToc } from "@/components/ReportToc";
import { useGraphStore } from "@/store/graphStore";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function AppInner() {
  const [sidebarOpen, setSidebarOpen] = useState(
    () => typeof window === "undefined" || window.innerWidth >= 768,
  );
  const threadTitle = useAuiState((s) => s.threadListItem?.title);
  const remoteId = useAuiState((s) => s.threadListItem?.remoteId ?? null);

  // 会话切换：清展示层残留（行情卡/报告底条/时间线），移动端收起抽屉
  useEffect(() => {
    useGraphStore.getState().clearSession();
    if (window.innerWidth < 768) setSidebarOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remoteId]);

  const running = useGraphStore((s) => s.running);
  const lastReport = useGraphStore((s) => s.lastReport);

  // 长任务保护：运行中关闭/刷新前提醒（SSE 断开 = 后端 run 被取消）
  useEffect(() => {
    if (!running) return;
    const guard = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [running]);

  // 完成提醒：标题闪烁（用户切走 tab 也能注意到）
  useEffect(() => {
    const base = document.title;
    if (!running) {
      if (lastReport) {
        document.title = "✓ 研报已生成 — IRIS";
        const t = setTimeout(() => (document.title = base), 8000);
        return () => clearTimeout(t);
      }
      document.title = base;
      return;
    }
    let on = false;
    const t = setInterval(() => {
      document.title = (on = !on) ? "⏳ 研究中…" : base;
    }, 1500);
    return () => {
      clearInterval(t);
      document.title = base;
    };
  }, [running, lastReport]);

  return (
    <div className="flex h-dvh bg-background">
      {/* 移动端遮罩 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}
      {/* 左侧边栏：会话 + 状态（小屏抽屉，桌面常驻） */}
      <aside
        className={cn(
          "flex h-full shrink-0 flex-col border-r bg-card/95 backdrop-blur transition-all duration-200 md:bg-card/40 md:backdrop-blur-none",
          sidebarOpen
            ? "fixed inset-y-0 left-0 z-40 w-72 md:static"
            : "w-0 overflow-hidden border-r-0",
        )}
      >
        <div className="px-4 py-3.5">
          <div className="text-sm font-semibold tracking-tight">IRIS 投研平台</div>
          <div className="text-[11px] text-muted-foreground">
            LangGraph 多智能体 · A 股
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-3">
          <ThreadList />
        </div>
        <div className="space-y-2 border-t p-3">
          <StatusCard />
          <div className="flex items-center justify-between text-[11px] text-muted-foreground">
            <span>数据与观点分离 · 来源可溯</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      {/* 右栏：研报目录（大屏显示） */}
      <aside className="hidden h-full w-56 shrink-0 overflow-y-auto border-l bg-card/40 px-3 py-4 xl:block">
        <ReportToc />
      </aside>

      {/* 主区 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-2 border-b px-4 py-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="切换侧边栏"
            className="size-7 text-muted-foreground"
          >
            {sidebarOpen ? (
              <PanelLeftCloseIcon className="size-4" />
            ) : (
              <PanelLeftOpenIcon className="size-4" />
            )}
          </Button>
          <span className="min-w-0 truncate text-xs text-muted-foreground">
            {threadTitle ?? "六章节中文研报 · 数据与观点分离 · 来源可溯"}
          </span>
          <ResearchStatusChip />
        </header>
        <div className="min-h-0 flex-1">
          <Thread
            components={{
              Welcome,
              ViewportTop: IrisViewportTop,
              ViewportBottom: ReportFooterBar,
            }}
          />
        </div>
      </div>
    </div>
  );
}

/** 随消息流滚动的研究上下文：时间线（运行中吸顶）+ 行情卡 */
function IrisViewportTop() {
  return (
    <>
      <ResearchTimeline />
      <MarketDataCard />
    </>
  );
}

export default function App() {
  const runtime = useRemoteThreadListRuntime({
    runtimeHook: () => useLocalRuntime(IrisModelAdapter),
    adapter: irisThreadListAdapter,
  });
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <AppInner />
    </AssistantRuntimeProvider>
  );
}
