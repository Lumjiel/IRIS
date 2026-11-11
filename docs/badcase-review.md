# Badcase 复盘 — IRIS

> 原则：只复盘真实发生的问题，每个结论附证据（文件:行 / 命令输出 / commit）。

## Case 1：流式路径无额度降级，主模型 403 后 writer 直接拿空报告（P0）

**现象**：主模型免费额度耗尽（DashScope 返回 403 FreeTierOnly）后，`llm_invoke()`
路径的节点正常切到 fallback 模型，但 writer 的流式路径产出**空报告**，前端收到空白
正文，无任何报错。

**时间线**：
1. 基线 v1 benchmark（2026-08-24）起，`docs/benchmark.md` 记录主模型 403
   FreeTierOnly、全程 fallback 生成——降级机制在 invoke 路径被验证有效。
2. 流式路径（`utils/streaming.py`）是后来为 SSE 加的：生产者线程调 `llm.stream()`，
   异常处理只做了「吞掉 + 日志」，没有对齐 invoke 路径的额度降级。
3. 主模型额度耗尽成为常态后，流式路径每次 stream 第一批 chunk 就抛 403 →
   被外层 `except Exception` 吞掉 → `full_text` 为空串返回。

**根因**：同一「主模型可能 403」的故障，invoke 路径有降级、stream 路径没有——
两条路径的能力不对齐，属于**降级策略只做了一半**。且空串返回是「静默失败」，
故障被下游（空报告）放大而不是在源头暴露。

**修复**（`backend/app/utils/streaming.py:87-115`）：
- 生产者线程捕获异常后先判 `is_quota_error(e)`；
- 额度类错误 → `mark_primary_exhausted()`（5 分钟 TTL）→ 换 fallback 模型重试一次；
- 非额度错误才按原逻辑吞掉（保住「SSE 不能 500」的产品约束）；
- `finally` 保证结束标记 `None` 入 channel，消费者不挂死。

**验证**：
- 回归测试：`tests/test_streaming.py::test_quota_error_triggers_fallback_stream` —
  注入主模型 403 异常 + mock fallback，断言降级标记被调用且输出来自备用模型
  （2026-11-10 加入，283 tests 全绿）；
- 非额度错误路径：
  `test_non_quota_error_ends_stream_gracefully` 断言流优雅结束、final 标记仍发出。

**反例（什么时候这个修复不成立）**：fallback 模型也在同一账号下共享额度时，
二次 stream 仍会 403——此时输出仍为空串，但 `mark_primary_exhausted` 已触发，
5 分钟内 invoke 路径同样直接走 fallback，系统整体可观测（`GET /api/status`
的 `llm_degraded=true`）。空报告从「无解释的静默失败」变为「有标记的已知降级」。

**教训**：
1. 给一条执行路径加故障处理时，先枚举「同故障在兄弟路径上已有的处理」，
   对齐后再交付——半套降级比没有降级更难排查；
2. 静默吞异常必须留可观测痕迹（这里靠 status 端点 + 日志）。

---

## Case 2：检索测试「本地碰巧绿，CI 红」——测试依赖了真实环境（P1）

**现象**：CI 上 RAG 检索相关测试随机红，本地跑却全绿。

**根因**：测试没有 mock `os.path.exists` / `os.listdir`，本地机器上恰好存在
真实知识库目录，代码走了「真读目录」分支碰巧通过；CI 容器无该目录，函数提前
返回空，断言失败。测试的绿依赖了**开发机的环境残留**，不是被测逻辑正确。

**修复**：给检索/入库测试补上 `exists` / `listdir` mock，并在 CI 无库环境
（`CHROMA_DB_PATH=/nonexistent`）本地复现 → 修复 → 全绿。

**证据**（修复序列，4 连 commit）：
- `fa1223b` fix(test): 检索测试补 os.path.exists mock——本地靠真实知识库碰巧通过，CI 无库提前返回空
- `b4ddd1e` fix(test): 再补 os.listdir mock——CI 无库目录时 listdir 抛错被吞成空结果
- `b466d32` fix(test): 恢复 ingest 测试的 exists mock（装饰器归属彻底摆正）
- `2753d38` fix(test): search 测试补上丢失的 listdir mock——CI 无库环境复现验证通过

**反例**：如果断言本身是「目录存在时应返回空」之类的环境行为断言，mock 掉
文件系统反而把测试变成纯 mock 自嗨——判断依据是断言对象是被测逻辑
（过滤/映射/降级）还是文件系统本身；本例是前者。

**教训**：单测红绿必须只由代码决定，不由测试机的文件系统/网络/时间决定；
「本地绿 CI 红」优先怀疑环境依赖，其次才是并发与时序。

---

## Case 3：性能回归——修订快速通道让 000333 延迟 +362%（P1）

**现象**：v2.1 修订快速通道上线后复测，5 只样本 4 只改善 15%~78%，
唯独 000333 美的集团从 446.8s 恶化到 2065.2s（**+362%**），token 27.6K → 112.5K。

**根因**（`docs/benchmark.md` v2.1 节，2026-11-08）：该样本 reviewer 连续 5 轮
不满意，每轮触发**全文重写**（4-6 min/轮）。快速通道只消除了「修订轮重复完整
搜索」，没有消除「修订 = 全文重写」本身——砍掉的耗时被重写耗时掩盖后反超。

**对策**（已定位，未实施）：修订改为按 critique 定点改写（refiner 式）或分章
并行撰写（Send API map-reduce），把单轮修订成本从全文重写降为增量修订。

**教训**：性能优化必须跑**全量样本**而不是只看目标样本——只测 600196 会得出
「-78% 全面胜利」的假结论；离群恶化样本往往暴露的是下一层瓶颈。
