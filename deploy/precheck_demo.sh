#!/usr/bin/env bash
# IRIS 现场演示预检 —— 四项全绿才开讲（配合 docs/interview/06-live-demo.md）
# 用法：bash deploy/precheck_demo.sh [API_BASE]   # 默认 http://127.0.0.1:8082
set -u
API="${1:-http://127.0.0.1:8082}"
FRONT="${2:-http://127.0.0.1/}"
fail=0

say() { printf '%-14s %s\n' "$1" "$2"; }

# ① 数据源在线且非 Mock
s=$(curl -s -m 8 "$API/api/status" 2>/dev/null)
if echo "$s" | grep -q '"data_online":true' && ! echo "$s" | grep -q '模拟'; then
    say "①数据源" "OK — $(echo "$s" | grep -ao '"data_source":"[^"]*"' | head -1)"
else
    say "①数据源" "FAIL — $s"; fail=1
fi

# ② LLM 无熔断
if echo "$s" | grep -q '"llm_degraded":false'; then
    say "②LLM" "OK — $(echo "$s" | grep -ao '"primary_model":"[^"]*"' | head -1)"
else
    say "②LLM" "FAIL — 主模型熔断中（TTL 5min 自动恢复，或查 .env key 余额）"; fail=1
fi

# ③ 前端页面可达
code=$(curl -s -o /dev/null -w '%{http_code}' -m 8 "$FRONT")
if [ "$code" = "200" ]; then
    say "③前端" "OK — $FRONT → 200"
else
    say "③前端" "FAIL — $FRONT → HTTP $code"; fail=1
fi

# ④ 今日配额（去后端日志/数据库查今天的请求数；简化：探测 429 不出现即视为有余量）
today=$(date +%F)
n=$(sqlite3 /var/www/IRIS/backend/checkpoints.db \
    "SELECT count(*) FROM rate_limits WHERE key LIKE 'daily:%' AND ts >= strftime('%s','now') - 86400;" \
    2>/dev/null || echo "?")
if [ "$n" = "?" ]; then
    say "④配额" "WARN — 无法读取限流表（sqlite3 缺失或表名变更），人工确认今天没用超 5 次"
elif [ "$n" -lt 4 ]; then
    say "④配额" "OK — 今日已用 $n/5 次"
else
    say "④配额" "FAIL — 今日已用 $n/5 次，剩 1 次以下，慎用主线演示"; fail=1
fi

echo "----"
[ $fail -eq 0 ] && echo "ALL GREEN — 可以开讲" || echo "有 FAIL 项 — 先排障再开讲"
exit $fail
