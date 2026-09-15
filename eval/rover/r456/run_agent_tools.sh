#!/usr/bin/env bash
# R456 —— 动作环 E2E: 同夹具/同 6 轮输入/同模型(deepseek-flash, 经 48615 适配器), 我方单会话 6 轮。
# 与 R455 的差别: 仅我方二进制(/tmp/pub_r456) + 动作环开(AGENTFRAMEWORK_ACTION_LOOP=on) + 工作区端口。
set -uo pipefail
A=/home/agentuser/AgentFramework
OUT=/tmp/r456_env/logs
mkdir -p "$OUT/adapter"
cd "$A"

echo "=== 夹具(与 codex 侧逐字节同) ==="
for f in /tmp/r456_env/agent/work/*.py /tmp/r456_env/agent/work/*.txt /tmp/r456_env/agent/work/notes.md; do
  [ -f "$f" ] && md5sum "$f"
done | awk '{print $1}' | sort | md5sum | sed 's/^/  agent fixture md5: /'
for f in /tmp/r455_env/codex/work/*.py /tmp/r455_env/codex/work/*.txt /tmp/r455_env/codex/work/notes.md; do
  [ -f "$f" ] && md5sum "$f"
done | awk '{print $1}' | sort | md5sum | sed 's/^/  codex fixture md5: /'

echo "=== 我方 host (动作环 on) ==="
set -a; . "$A/.env.local"; set +a
test -n "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" && echo "  keys: SET" || echo "  keys: MISSING"
cd /tmp/r456_env/agent/work
AGENTFRAMEWORK_FRONTEND_TOKEN=r456-token AGENTFRAMEWORK_CONFIG=/tmp/r456_env/agent/cfg \
  AGENTFRAMEWORK_WORKSPACE=/tmp/r456_env/agent/work \
  AGENTFRAMEWORK_ACTION_LOOP=on \
  AGENTFRAMEWORK_ACTION_AUDIT="$OUT/audit" \
  setsid nohup /tmp/pub_r456/agenthost --frontend-api 48617 > "$OUT/host-agent.log" 2>&1 &
echo $! > "$OUT/host-agent.pid"
sleep 15
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=r456-token timeout 900 python3 -u eval/rover/r430/drive_task.py 48617 \
  /tmp/r456_env/suite-turns.json "$OUT/agent-turns.jsonl" > "$OUT/agent-drive.log" 2>&1
echo "[agent] rc=$?"
kill -9 "$(cat "$OUT/host-agent.pid")" 2>/dev/null
echo "=== 产物 ==="
ls /tmp/r456_env/agent/work | tr '\n' ' '; echo
for f in count.txt merged.txt stats.txt first.txt; do
  printf '  %-11s = %s\n' "$f" "$(cat /tmp/r456_env/agent/work/$f 2>/dev/null | head -3 | tr '\n' '|')"
done
echo "=== 动作环审计 ==="
ls "$OUT/audit" 2>/dev/null && tail -6 "$OUT/audit/action_loop.jsonl" 2>/dev/null | cut -c1-200
