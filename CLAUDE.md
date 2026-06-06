# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

IRIS (Intelligent Research Insight System) 是一个基于 **LangGraph 状态机** 的自动化深度调研与报告生成系统。通过多节点协作实现：意图识别 → 路径规划 → 动态检索 → 深度撰写 → 自我审查的全自动闭环。

## 技术栈

- **后端**: FastAPI + LangGraph + ChromaDB (RAG) + Tavily (搜索) + SQLite Checkpoint
- **前端**: Vue 3 + Tailwind CSS + markdown-it + KaTeX
- **LLM**: DashScope API (qwen3.7-plus) + 备用 (deepseek-v4-flash)
- **Embedding**: DashScope text-embedding-v4

## 目录结构

```
IRIS/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # FastAPI 路由 (SSE + 限流 + aihot 代理)
│   │   ├── config.py              # 集中配置（所有可调参数）
│   │   ├── graph/
│   │   │   ├── state.py           # AgentState 状态定义
│   │   │   ├── graph.py           # 状态机拓扑构建
│   │   │   └── nodes/             # 6个智能体节点
│   │   ├── rag/engine.py          # 文档解析 + 向量化 + 检索
│   │   ├── tools/search.py        # Tavily 搜索封装
│   │   └── utils/
│   │       ├── llm.py             # 模型工厂（带自动降级）
│   │       └── logger.py          # 统一日志
│   ├── Dockerfile                 # 生产部署镜像
│   ├── DEPLOY.md                  # 部署指南
│   ├── .env.example               # 环境变量模板
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue                # 主页面（Tab 布局 + TOC + 导出）
│   │   ├── components/StatusFlow.vue
│   │   └── services/
│   │       ├── api.js             # API 封装（含 aihot + save-report）
│   │       └── history.js         # localStorage 历史管理
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
| `reviewer` | 质量审查，FAIL → 返回 planner 重试 |
| `refiner` | 对现有报告进行局部修订 |

## 环境变量

在 `backend/.env` 中配置（参考 `.env.example`）：

| 变量 | 说明 | 必填 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | DashScope API Key | ✅ | - |
| `OPENAI_API_BASE` | API 端点 | ✅ | - |
| `DASHSCOPE_API_KEY` | Embedding API Key | ✅ | - |
| `TAVILY_API_KEY` | Tavily 搜索 Key | ✅ | - |
| `LLM_MODEL_PRIMARY` | 主模型 | ❌ | `qwen3.7-plus` |
| `LLM_MODEL_FALLBACK` | 备用模型 | ❌ | `deepseek-v4-flash` |
| `CORS_ORIGINS` | 允许的域名 | 生产必填 | `*` |
| `ENABLE_RERANKER` | CrossEncoder 精排 | ❌ | `false` |
| `CREATION_DIR` | 报告保存目录 | ❌ | 本地路径 |
| `CHECKPOINT_DB` | SQLite 路径 | ❌ | `data/checkpoints.db` |

## 常用命令

```bash
# 后端
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev    # http://localhost:5173

# Docker 部署
cd backend
docker build -t iris-backend .
docker run -d --name iris -p 8000:8000 --memory=1g -v .env:/app/.env iris-backend
```

## 状态机工作流程

```
入口 → router
  ├── NEW_TOPIC → planner → researcher → (should_stop? → END : writer) → reviewer → (FAIL? → planner : END)
  └── REFINE → refiner → END
```

## 关键实现细节

- **模型自动降级**: `llm_invoke()` 主模型额度耗尽/超时 → 自动切换备用模型，5 分钟后自动恢复尝试
- **请求限流**: 内存限流器，每 IP 每分钟最多 5 次研究请求
- **SSE 流式**: `routes.py` 通过 `app.astream()` 将每个节点状态实时推送至前端
- **相关性熔断**: Researcher 内置 Grader LLM，文档不相关时 `should_stop=True`
- **会话持久化**: `AsyncSqliteSaver` + 自动清理过期检查点（默认 7 天）
- **文件管理**: 上传后自动清理 24h 前旧文件，知识库片段上限 2000

## 前端功能

- **Tab 切换布局**: 知识库 / AI 灵感 / 历史，三个面板不同时显示
- **AI 灵感面板**: 代理 aihot API，5 分类筛选，点击填充调研主题
- **研究历史**: localStorage 持久化，支持标记"已用于文章"
- **导出**: 复制 Markdown/HTML + 下载 .md + 保存到素材库（寻阶行创作目录）
- **报告 TOC**: 自动提取标题生成目录导航
- **快捷键**: Ctrl+Enter 快速开始调研

## API 端点

| 端点 | 说明 |
|------|------|
| `POST /api/upload` | 上传 PDF，构建向量知识库 |
| `POST /api/chat` | SSE 流式聊天 |
| `POST /api/clear` | 重置知识库 |
| `GET /api/aihot/news` | AI HOT 新闻代理 |
| `POST /api/save-report` | 保存报告到创作目录 |
| `GET /` | 健康检查 |

## 容错机制

- **模型降级**: 主模型失败 → 备用模型，5 分钟 TTL 自动恢复
- **Router 兜底**: LLM 输出非法 → `looks_like_refine()` 关键词匹配
- **Reviewer 兜底**: JSON 解析失败 → 重试 → fail-closed
- **搜索重试**: Tavily 调用失败 → 2 次重试
- **上传校验**: 文件类型（PDF）+ 大小（20MB）+ 数量（5 个）
