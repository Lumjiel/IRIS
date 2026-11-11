# IRIS 审计发现台账

> 每轮审计把新发现追加到这里。卡必须引用这里的 ID（如 IRIS-A001）。
> 状态：open / carded / fixed / wontfix

| ID | 透镜 | 严重度 | 位置 | 发现 | 特性 | 状态 |
|:--|:--|:--|:--|:--|:--|:--|
| IRIS-A001 | 性能/异步 | 高 | app/api/routes.py:849,870,925,946 | async 路由里调同步 requests.get，阻塞事件循环，一个慢请求拖住全进程 | F-004 | open |
| IRIS-A002 | 结构 | 中 | app/api/routes.py（1196 行 / 28 路由） | 所有路由挤一个文件，改一个接口要读全部 | F-001 | open |
| IRIS-A003 | 测试质量 | 中 | app/utils/memory.py 13.8% / streaming.py 24.7% | 核心链路无测试，改坏没人知道 | F-003 | open |
| IRIS-A004 | 可观测性 | 中 | 全局 | 无 /healthz、无结构化日志、无请求耗时统计 | F-005 | open |
| IRIS-A005 | 前端 | 低 | frontend-next/ | 前端只 build 不测、不进 CI | F-009 | open |

## 已扫过、确认干净
裸 except 0 处 · TODO/FIXME 0 处 · 硬编码密钥 0 处（2026-11-09 快扫）
