import { useState } from "react";
import {
  AssistantRuntimeProvider,
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
import { Welcome } from "@/components/Welcome";
import { StatusCard } from "@/components/StatusCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function AppInner() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-dvh bg-background">
      {/* 左侧边栏：会话 + 状态 */}
      <aside
        className={cn(
          "flex h-full shrink-0 flex-col border-r bg-card/40 transition-all duration-200",
          sidebarOpen ? "w-72" : "w-0 overflow-hidden border-r-0",
        )}
      >
        <div className="flex items-center gap-2.5 px-4 py-3.5">
          <span className="text-lg">📊</span>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold tracking-tight">
              IRIS 投研平台
            </div>
            <div className="truncate text-[11px] text-muted-foreground">
              LangGraph 多智能体 · A 股
            </div>
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
          <span className="text-xs text-muted-foreground">
            检索 → 数据拉取 → 撰写 → 审查 · 六章节中文研报
          </span>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ResearchTimeline />
          <Thread components={{ Welcome }} />
        </div>
      </div>
    </div>
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
