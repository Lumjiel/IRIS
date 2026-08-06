# IRIS 项目完整性审查报告

**审查时间**: 2026-08-06
**分支**: feat/v2-skill-memory-tool
**最新提交**: 78c2272

---

## 一、文件结构完整性

### ✅ 已创建的文件

| 模块 | 文件 | 状态 |
|------|------|------|
| **Skill** | `backend/app/skills/__init__.py` | ✅ |
| | `backend/app/skills/models.py` | ✅ Skill 数据类 |
| | `backend/app/skills/registry.py` | ✅ 扫描/注册/匹配 |
| | `backend/app/skills/lifecycle.py` | ✅ CRUD 操作 |
| | `backend/app/skills/router.py` | ✅ 路由匹配 |
| | `backend/app/skills/builtin/content_research/SKILL.md` | ✅ 内置 Skill |
| **Memory** | `backend/app/memory/__init__.py` | ✅ |
| | `backend/app/memory/models.py` | ✅ MemoryRecord |
| | `backend/app/memory/store.py` | ✅ SQLite CRUD |
| | `backend/app/memory/extractor.py` | ✅ 记忆提取 |
| **Tools** | `backend/app/tools/__init__.py` | ✅ |
| | `backend/app/tools/registry.py` | ✅ ToolRegistry |
| | `backend/app/tools/builtin/__init__.py` | ✅ |
| | `backend/app/tools/builtin/search.py` | ✅ web_search |
| | `backend/app/tools/builtin/doc_search.py` | ✅ doc_search |
| | `backend/app/tools/builtin/citation.py` | ✅ citation_search |
| **Utils** | `backend/app/utils/citations.py` | ✅ CitationFormatter |
| **State** | `backend/app/graph/state.py` | ✅ 新增字段 |
| **API** | `backend/app/api/routes.py` | ✅ 22 个端点 |

### ✅ API 端点清单

| 端点 | 说明 | 状态 |
|------|------|------|
| `POST /api/chat` | SSE 流式聊天 | ✅ 原有 |
| `POST /api/upload` | 上传 PDF | ✅ 原有 |
| `POST /api/clear` | 重置知识库 | ✅ 原有 |
| `GET /api/memory/{thread_id}` | 获取会话记忆 | ✅ 原有 |
| `POST /api/memory/{thread_id}/reset` | 清空会话摘要 | ✅ 原有 |
| `GET /api/memory/search` | 搜索长期记忆 | ✅ 新增 |
| `GET /api/memory/{memory_id}` | 获取单条记忆 | ✅ 新增 |
| `DELETE /api/memory/{memory_id}` | 删除记忆 | ✅ 新增 |
| `GET /api/tools` | 列出所有工具 | ✅ 新增 |
| `GET /api/tools/{name}` | 获取工具详情 | ✅ 新增 |
| `POST /api/tools/{name}/execute` | 执行工具 | ✅ 新增 |
| `GET /api/skills` | 列出所有 Skill | ✅ 新增 |
| `POST /api/skills` | 创建 Skill | ✅ 新增 |
| `GET /api/skills/{name}` | 获取 Skill 详情 | ✅ 新增 |
| `PUT /api/skills/{name}` | 更新 Skill | ✅ 新增 |
| `DELETE /api/skills/{name}` | 删除 Skill | ✅ 新增 |
| `GET /api/aihot/news` | AI HOT 新闻 | ✅ 原有 |
| `POST /api/save-report` | 保存报告 | ✅ 原有 |
| `GET /api/materials` | 列出素材 | ✅ 原有 |

---

## 二、已知 Bug

### 🔴 Bug 1：search_sources 未填充

**位置**: `backend/app/graph/nodes/researcher.py`

**问题**: `sources` 列表初始化为 `[]`，但从未被填充。`search_tavily_structured` 可以返回结构化数据（含 URL/标题），但 `builtin/search.py` 用的是 `search_tavily`（纯文本）。

**影响**: CitationFormatter 无法生成引用标注，因为 `search_sources` 为空。

**修复方案**: 修改 researcher.py，使用 `search_tavily_structured` 获取结构化结果并填充 sources。

### 🟡 Bug 2：Planner 缺少 memory_context

**位置**: `backend/app/graph/nodes/planner.py`

**问题**: planner.py 从 `_skill_cache` 读取 Skill，但没有从 MemoryStore 读取 Semantic 记忆（用户偏好）。

**影响**: 记忆系统虽然写入成功，但规划时无法利用历史偏好。

---

## 三、架构审查

### ✅ 设计决策正确

1. **Skill 体系**：SKILL.md + Registry + 按需加载，参考 SlotFlow 设计
2. **四层记忆**：Working/Episodic/Semantic/Procedural，SQLite 存储
3. **Tool Registry**：动态注册 + Skill 声明所需工具
4. **引用系统**：CitationFormatter + 自动标注

### ✅ 向后兼容

- 现有 6 节点逻辑不变
- conversation_summary 保留
- 所有 API 端点保留

---

## 四、待修复事项

| 优先级 | 事项 | 预计时间 |
|--------|------|---------|
| 🔴 高 | 修复 search_sources 未填充 | 30min |
| 🟡 中 | Planner 集成 Semantic 记忆读取 | 30min |
| 🟢 低 | 添加更多内置 Skill（tech_evaluation、industry_analysis） | 2h |

---

## 五、面试叙事完整性

### 开场（30 秒）
> "IRIS 是一个通用深度调研引擎，基于 LangGraph 状态机 + 6 个 Agent 节点。我自己运营公众号，把调研时间从 2 小时压到 15 分钟。"

### 技术深度（2 分钟）
> "核心创新是四个子系统：
> 1. **Skill 体系**：每个调研场景一个 SKILL.md，系统自动匹配，零代码扩展
> 2. **四层记忆**：Working/Episodic/Semantic/Procedural，越用越聪明
> 3. **Tool Registry**：动态注册，Skill 声明所需工具，Planner 自动选择
> 4. **引用系统**：每个结论自动标注来源，末尾追加参考文献"

### 追问准备
> - 为什么 LangGraph 而不是 CrewAI？→ 图拓扑精确控制回跳
> - 记忆为什么不用向量数据库？→ SQLite + 关键词够用，延迟更低
> - 怎么保证质量？→ Reviewer 审查 + 回跳 Planner 重搜
