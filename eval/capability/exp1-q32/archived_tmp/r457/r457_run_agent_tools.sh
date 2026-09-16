#!/usr/bin/env bash
# R457 —— 效果收口复跑: 同夹具/同 6 轮输入/同模型(deepseek-flash 经 48615 适配器)。
# 与 R456 差别: 二进 /tmp/pub_r457(含台账回灌/未落槽转路径/无候选可见失败) + 适配器落 tool_calls + 审计落 args_head。
set -uo pipefail
A=/home/agentuser/AgentFramework
E=/tmp/r457_env
OUT=$E/logs
mkdir -p "$OUT/adapter"
cd "$A"

echo "=== 夹具 md5 (两侧逐字节同) ==="
md5sum $E/agent/work/*.py $E/agent/work/*.txt $E/agent/work/notes.md | awk '{print $1}' | sort | md5sum | sed 's/^/  agent: /'
md5sum $E/codex/work/*.py $E/codex/work/*.txt $E/codex/work/notes.md | awk '{print $1}' | sort | md5sum | sed 's/^/  codex: /'

echo "=== 环境(密钥) ==="
set -a; . "$A/.env.local"; set +a
test -n "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" && echo "  keys: SET" || echo "  keys: MISSING"

echo "=== 适配器(我方侧落 tool_calls) ==="
if [ -f /tmp/cxprobe/adapter.pid ]; then kill -9 "$(cat /tmp/cxprobe/adapter.pid)" 2>/dev/null; fi
pkill -f "[a]dapter_tools.py" 2>/dev/null
sleep 1
mkdir -p /tmp/cxprobe
cd /tmp/cxprobe
DEMO_OUT=$OUT/adapter setsid nohup python3 -u "$A/eval/rover/r455/adapter_tools.py" 48615 > "$OUT/adapter/adapter.log" 2>&1 &
echo $! > /tmp/cxprobe/adapter.pid
sleep 3
echo "  adapter pid=$(cat /tmp/cxprobe/adapter.pid)"; tail -2 "$OUT/adapter/adapter.log" 2>/dev/null

echo "=== 我方 host (动作环 on, 续跑不落槽转路径 on) ==="
cd $E/agent/work
AGENTFRAMEWORK_FRONTEND_TOKEN=r457-token AGENTFRAMEWORK_CONFIG=$E/agent/cfg \
  AGENTFRAMEWORK_WORKSPACE=$E/agent/work \
  AGENTFRAMEWORK_ACTION_LOOP=on \
  AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH=on \
  AGENTFRAMEWORK_ACTION_AUDIT="$OUT/audit" \
  setsid nohup /tmp/pub_r457/agenthost --frontend-api 48617 > "$OUT/host-agent.log" 2>&1 &
echo $! > "$OUT/host-agent.pid"
sleep 15
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=r457-token timeout 900 python3 -u eval/rover/r430/drive_task.py 48617 \
  $E/suite-turns.json "$OUT/agent-turns.jsonl" > "$OUT/agent-drive.log" 2>&1
echo "[agent] rc=$?"
kill -9 "$(cat "$OUT/host-agent.pid")" 2>/dev/null
echo "=== 产物 ==="
ls $E/agent/work | tr '\n' ' '; echo
for f in count.txt merged.txt stats.txt first.txt; do
  printf '  %-11s = %s\n' "$f" "$(cat $E/agent/work/$f 2>/dev/null | head -3 | tr '\n' '|')"
done
echo "=== 动作环审计(args_head 原文) ==="
tail -8 "$OUT/audit/action_loop.jsonl" 2>/dev/null | cut -c1-260
echo "=== 适配器落盘的 tool_calls 面 ==="
ls "$OUT/adapter" | head -5
