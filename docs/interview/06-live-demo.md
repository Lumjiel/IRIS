# 06 · 现场演示脚本（Live Demo）

> 原则：面试现场跑真 API，不靠录屏、不靠预制答案。配额每日 5 次研究请求（`DAILY_RESEARCH_QUOTA=5`，`routes.py:207`），演示按配额预算设计。

## 0. 环境事实（2026-11-11 核验）

| 项 | 值 | 来源 |
|---|---|---|
| 演示入口 | `http://119.45.122.221/`（Nginx 80 → frontend-next/dist） | `/etc/nginx/conf.d/iris-ip.conf` |
| 后端 | 本机 uvicorn `127.0.0.1:8082`，`/api` 反代 | 同上 |
| 数据源 | 同花顺 L0 + 腾讯行情补充，`data_online:true` | `curl :8082/api/status` |
| LLM | DashScope compatible-mode，主备双模型 | `/var/www/IRIS/backend/.env` |
| 单次研究延迟 | 5-15+ 分钟：benchmark 中位 436s；reviewer 连续打回时实测 >15min（2026-11-11 两次真实跑，600s/900s 客户端超时均未看到终态，服务端跑完后修订上限生效） | `docs/benchmark.md` + `/root/tmp/iris-m1-e2e/` SSE 原始流 |

## 1. 预检清单（开场前 2 分钟跑一次）

```bash
bash deploy/precheck_demo.sh
```

四项全绿才开讲：① 数据源在线（非 Mock）② LLM key 可用（无熔断）③ 前端页面 200 ④ 今日配额有余量。

## 2. 演示路径 A：标准全流程（主线，1 次配额）

1. 手机或笔记本打开 `http://119.45.122.221/`，输入 **600519**。
2. **边跑边讲**（时间线实时可见，这是设计好的等待体验）：
   - planner 拆 3-5 个检索方向 → 讲「LLM 规划而非固定模板」；
   - search_agent ⇄ search_tools 循环 → 讲「Function Calling，LLM 自己决定搜什么」；
   - data_collector → 讲「同花顺 L0 → 东财 → 雪球/新浪 → Mock 四层降级，现场点开 `/api/status` 证明当前落在哪层」；
   - writer 逐章产出 → 讲「表格由 financial_data JSON 直接渲染，不经 LLM 改写——防幻觉的关键」；
   - reviewer → 讲「不合格会真打回，revision_search 定向补搜后重写」。
3. 报告完成后指三处：**来源标注**（`[来源: 同花顺官方API]` / `[来源: 网络搜索]`）、**⚠️ 数据不足，暂不评价**（诚实报告）、**免责声明**。

## 3. 演示路径 B：多轮追问（0.5 次配额成本，REFINE 分支）

报告完成后追问：**「把投资建议改成给保守型投资者的三条理由」** → 走 refiner 分支（不重跑研究管线），秒级返回。讲：意图路由 NEW_TOPIC/REFINE + conversation_summary 跨轮记忆。

## 4. 演示路径 C：降级韧性（不耗研究配额）

问「如果同花顺挂了会怎样」→ 当场把 `.env` 里 `ENABLE_HITHINK` 关掉重启（或直接口头讲 + 展示 `test_fault_injection.py` 16 条故障注入全绿 + 全链挂掉时降级到 Mock 且 `degraded=true`、来源标「内置模拟数据」不冒充真实）。**推荐口头讲+跑测试**，现场不动 `.env`（重启后端有风险）。

## 5. 已知边界（主动交底，防止现场翻车尴尬）

- 三大指数区当前为空：同花顺 L0 快照端点不支持指数代码（`000001.SH` → `Target not found`，2026-11-11 实测）。行情页个股正常。
- `/api/aihot/news` 可能返回「AI 资讯服务暂时不可用」（fail-open 如实降级）。
- 单次研究 5-15+ 分钟（reviewer 对本样本曾连续打回 3 次到修订上限）：演示节奏按「边跑边讲」设计，不要干等；**开场先跑 A 路径，讲到报告时大概率已完成**。
- **Reviewer 一次通过率是诚实数据**：600519 样本实测 0/1 通过（3 次打回），不是 bug 是严格审查的体现——被问「为什么这么慢」时的标准答案。
- 每日配额 5 次：A 路径 1 次 + 备用 1 次 + 上午自检 1 次，留 2 次余量。

## 6. 备份预案

- 若现场网络挂：`/root/tmp/iris-m1-e2e/sse_600519_full.txt` 有 2026-11-11 真实全链 SSE 原始流，可回放事件序列（如实说明是回放）。
- 若后端挂：预检脚本会红，直接讲架构图 + 跑 299 条测试。
