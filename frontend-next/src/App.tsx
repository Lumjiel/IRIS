import { AssistantRuntimeProvider, useLocalRuntime } from "@assistant-ui/react";
import { Thread } from "@/components/assistant-ui/elements/thread.aui";
import { IrisModelAdapter } from "@/lib/irisRuntime";
import { ResearchTimeline } from "@/components/ResearchTimeline";
import { Welcome } from "@/components/Welcome";

function AppInner() {
  return (
    <div className="flex h-dvh flex-col bg-background">
      <header className="flex items-center gap-3 border-b px-6 py-3">
        <span className="text-lg">📊</span>
        <div>
          <div className="text-sm font-semibold tracking-tight">
            IRIS 投研信息聚合平台
          </div>
          <div className="text-xs text-muted-foreground">
            LangGraph 多智能体 · A 股真实数据 · 六章节研报
          </div>
        </div>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <ResearchTimeline />
        <Thread components={{ Welcome }} />
      </div>
    </div>
  );
}

export default function App() {
  const runtime = useLocalRuntime(IrisModelAdapter);
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <AppInner />
    </AssistantRuntimeProvider>
  );
}
