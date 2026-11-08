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
  /** data_collector 完成后拉到的实时行情 */
  quote: QuoteData | null;

  reset: () => void;
  /** 会话切换时清理（不动 running，避免误杀仍在后台跑的 run） */
  clearSession: () => void;
  setIntent: (intent: string) => void;
  setNodeStatus: (step: string, status: NodeStatus, elapsed?: number) => void;
  setError: (msg: string) => void;
  setRunning: (v: boolean) => void;
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

  reset: () =>
    set({ intent: null, nodes: {}, order: [], error: null, running: true, lastReport: null, quote: null }),
  setIntent: (intent) => set({ intent }),
  setNodeStatus: (step, status, elapsed) =>
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
      return { nodes, order };
    }),
  setError: (msg) => set({ error: msg, running: false }),
  setRunning: (v) => set({ running: v }),
  clearSession: () =>
    set({ intent: null, nodes: {}, order: [], error: null, lastReport: null, quote: null }),
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
