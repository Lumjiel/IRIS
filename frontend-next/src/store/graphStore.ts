import { create } from "zustand";

export type NodeStatus = "running" | "done" | "failed";

export interface GraphNodeState {
  status: NodeStatus;
  elapsed?: number;
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

  reset: () => void;
  setIntent: (intent: string) => void;
  setNodeStatus: (step: string, status: NodeStatus, elapsed?: number) => void;
  setError: (msg: string) => void;
  setRunning: (v: boolean) => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  intent: null,
  nodes: {},
  order: [],
  error: null,
  running: false,

  reset: () =>
    set({ intent: null, nodes: {}, order: [], error: null, running: true }),
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
  writer: "报告撰写",
  reviewer: "质量审查",
  refiner: "修订",
};
