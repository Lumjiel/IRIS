# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

IRIS (Intelligent Research & Insight System) 是一个基于 **LangGraph 有向图状态机** 的 AI 研究智能体。通过 6 节点协作实现：意图识别 → 策略规划 → 多源检索 → 报告生成 → 质量评审 → 自动迭代的全自动闭环。

## 技术栈

- **后端**: FastAPI + LangGraph + ChromaDB (RAG) + Tavily (网络搜索) + SQLite Checkpoint
- **前端**: Vue 3 + Tailwind CSS + markdown-it + KaTeX
- **LLM**: DashScope (qwen3-max + deepseek-r1 双模型) + Tavily Search

## 目录结构

```
IRIS/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # FastAPI 路由 (SSE 流式响应)
│   │   ├── graph/
│   │   │   ├── state.py           # AgentState 状态定义
│   │   │   ├── graph.py           # 状态机拓扑构建
│   │   │   └── nodes/             # 6个智能体节点
│   │   ├── rag/engine.py          # 文档解析 + 向量化 + 检索
│   │   └── tools/search.py        # Tavily 搜索封装
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue                # 主页面 (含 SSE 连接 + 打字机效果)
│   │   ├── components/StatusFlow.vue
│   │   └── services/api.js        # API 封装
│   └── package.json
└── docs/
```

## 状态机节点

| 节点 | 职责 |
|------|------|
| `router` | 意图识别：判断 NEW_TOPIC → planner 或 REFINE → refiner |
| `planner` | 规划搜索策略，分解任务 |
| `researcher` | 执行 RAG + Web 检索，相关性评估（Relevance Grader） |
| `writer` | 根据检索结果撰写报告 |
| `reviewer` | 质量审查，FAIL → 返回 planner 重试（最多3轮） |
| `refiner` | 对现有报告进行局部修订 |

## 常用命令

```bash
# 后端
cd backend
python -m venv venv && venv\Scripts\activate  # Windows
pip install -r requirements.txt
# 配置 .env: OPENAI_API_KEY, OPENAI_API_BASE, TAVILY_API_KEY, ENABLE_RERANKER
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev    # 开发服务器 (http://localhost:5173)
npm run build  # 生产构建
```

## 状态机工作流程

```
入口 → router
  ├── NEW_TOPIC → planner → researcher → (should_stop? → END : writer) → reviewer → (FAIL? → planner : END)
  └── REFINE → refiner → END
```

## 关键实现细节

- **SSE 流式**: `routes.py` 中的 `streamChat` 通过 `app.astream()` 将每个节点的状态实时推送至前端
- **相关性熔断**: Researcher 节点内置 Grader LLM，当文档与问题不相关时，`should_stop=True` 触发提前结束（纯文档模式）或自动降级（全网搜索）- **会话持久化**: `AsyncSqliteSaver` 实现断点续跑，每次请求通过 `thread_id` 关联会话状态
- **前端打字机**: `App.vue` 中的 `typeWriterEffect` 每10ms输出3个字符，配合 markdown-it-katex 渲染 LaTeX 公式

## API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/upload` | 上传 PDF（最多5个），构建向量知识库 |
| `POST /api/chat` | SSE 流式聊天，`body: {query, search_mode, thread_id}` |
| `POST /api/clear` | 重置知识库 |