import { create } from "zustand";

export type NodeStatus = "running" | "done" | "failed";

export interface GraphNodeState {
  status: NodeStatus;
  elapsed?: number;
}

export interface QuoteData {
  stock_code: string;
  最新价?: string;
  涨跌幅?: string;
  今开?: string;
  最高?: string;
  最低?: string;
  昨收?: string;
  市盈率?: string;
  总市值?: string;
  data_source?: string;
  延时?: string;
}

interface GraphState {
  /** 意图：research / refine / chat */
  intent: string | null;
  /** 节点状态表，key 为后端节点名（router/planner/...） */
  nodes: Record<string, GraphNodeState>;
  /** 节点出现顺序（时间线按此渲染） */
  order: string[];
  error: string | null;
  /** 是否正在研究 */
  running: boolean;
  /** 最近一次研究生成的完整报告原文（用于导出/复制） */
  lastReport: string | null;
  /** 搜索轨迹（LLM 自主决策的搜索词，来自 search_tools 节点事件） */
  searchLog: string[];
  /** 数据源轨迹（来自 data_collector 节点事件） */
  dataSources: string[];
  /** 分章撰写进度（writer progress 事件的 chapter_done） */
  chapterLog: string[];
  /** 本轮研究起止时间（小结/计时用） */
  startedAt: number | null;
  endedAt: number | null;
  /** data_collector 完成后拉到的实时行情 */
  quote: QuoteData | null;

  reset: () => void;
  /** 会话切换时清理（不动 running，避免误杀仍在后台跑的 run） */
  clearSession: () => void;
  setIntent: (intent: string) => void;
  setNodeStatus: (step: string, status: NodeStatus, elapsed?: number, data?: Record<string, unknown>) => void;
  setError: (msg: string) => void;
  setRunning: (v: boolean) => void;
  markRunEnd: () => void;
  setLastReport: (text: string | null) => void;
  setQuote: (q: QuoteData | null) => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  intent: null,
  nodes: {},
  order: [],
  error: null,
  running: false,
  lastReport: null,
  quote: null,
  searchLog: [],
  dataSources: [],
  chapterLog: [],
  startedAt: null,
  endedAt: null,

  reset: () =>
    set({
      intent: null, nodes: {}, order: [], error: null, running: true,
      lastReport: null, quote: null, searchLog: [], dataSources: [], chapterLog: [],
      startedAt: Date.now(), endedAt: null,
    }),
  setIntent: (intent) => set({ intent }),
  setNodeStatus: (step, status, elapsed, data) =>
    set((s) => {
      const known = s.nodes[step];
      const nodes = {
        ...s.nodes,
        [step]: {
          status,
          // elapsed 只在 done 时更新；start 事件保留已有值
          elapsed: elapsed ?? known?.elapsed,
        },
      };
      const order = known ? s.order : [...s.order, step];
      // 轨迹事件：搜索词 / 数据源（done 事件可能带 data，wrapper 的空 done 不覆盖）
      let searchLog = s.searchLog;
      let dataSources = s.dataSources;
      let chapterLog = s.chapterLog;
      if (data) {
        if (typeof data.search_query === "string" && data.search_query) {
          searchLog = [...s.searchLog, data.search_query];
        }
        if (Array.isArray(data.data_sources)) {
          dataSources = data.data_sources.map(String);
        }
      if (typeof data.chapter_done === "string" && data.chapter_done) {
        chapterLog = s.chapterLog.includes(data.chapter_done)
          ? s.chapterLog
          : [...s.chapterLog, data.chapter_done];
      }
      }
      return { nodes, order, searchLog, dataSources, chapterLog };
    }),
  setError: (msg) => set({ error: msg, running: false }),
  setRunning: (v) => set({ running: v }),
  markRunEnd: () => set((s) => ({ endedAt: s.endedAt ?? Date.now() })),
  clearSession: () =>
    set({ intent: null, nodes: {}, order: [], error: null, lastReport: null, quote: null, chapterLog: [] }),
  setLastReport: (text) => set({ lastReport: text }),
  setQuote: (q) => set({ quote: q }),
}));

/** 节点显示名（与后端 graph/nodes 对应） */
export const NODE_LABELS: Record<string, string> = {
  load_memories: "记忆注入",
  router: "意图路由",
  planner: "研究规划",
  researcher: "文档检索",
  search_agent: "搜索决策",
  search_tools: "网络搜索",
  data_collector: "数据拉取",
  revision_search: "定向补搜",
  writer: "报告撰写",
  reviewer: "质量审查",
  refiner: "修订",
};
