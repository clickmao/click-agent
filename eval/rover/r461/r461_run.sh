#!/usr/bin/env bash
# R461 实跑: 同夹具/同 6 轮/同模型/同开关, 唯一差异 = 二进制 (R460 → R461) + ADAPTER_DUMP_FULL=1。
set -uo pipefail
A=/home/agentuser/AgentFramework
E=/tmp/r461_env
OUT=$E/logs
BIN=/tmp/pub_r461/agenthost
mkdir -p "$OUT/adapter"
cd "$A"

echo "=== 起手闸 (MemAvailable MB) ==="
free -m | awk 'NR==2{print "  "$7}'
echo "=== 夹具 md5 ==="
md5sum $E/agent/work/* | awk '{print $1}' | sort | md5sum | sed 's/^/  agent(pristine): /'

echo "=== 密钥 ==="
set -a; . "$A/.env.local"; set +a
test -n "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" && echo "  keys: SET" || echo "  keys: MISSING"

echo "=== 适配器 (ADAPTER_DUMP_FULL=1) ==="
pkill -f "[a]dapter_tools.py" 2>/dev/null; sleep 1
mkdir -p /tmp/cxprobe; cd /tmp/cxprobe
DEMO_OUT=$OUT/adapter ADAPTER_DUMP_FULL=1 setsid nohup python3 -u "$A/eval/rover/r455/adapter_tools.py" 48615 > "$OUT/adapter/adapter.log" 2>&1 &
echo $! > /tmp/cxprobe/adapter.pid; sleep 3
echo "  adapter pid=$(cat /tmp/cxprobe/adapter.pid)"

echo "=== 我方 host (R461: 契约声明不上前台 + 空产物标(空) + 记忆/召回块瘦身) ==="
cd $E/agent/work
AGENTFRAMEWORK_FRONTEND_TOKEN=r461-token AGENTFRAMEWORK_CONFIG=$E/agent/cfg \
  AGENTFRAMEWORK_WORKSPACE=$E/agent/work \
  AGENTFRAMEWORK_ACTION_LOOP=on \
  AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH=on \
  AGENTFRAMEWORK_ACTION_AUDIT="$OUT/audit" \
  setsid nohup $BIN --frontend-api 48617 > "$OUT/host-agent.log" 2>&1 &
echo $! > "$OUT/host-agent.pid"
sleep 15
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=r461-token timeout 900 python3 -u eval/rover/r430/drive_task.py 48617 \
  $E/suite-turns.json "$OUT/agent-turns.jsonl" > "$OUT/agent-drive.log" 2>&1
echo "[agent] rc=$?"
kill -9 "$(cat "$OUT/host-agent.pid")" 2>/dev/null
pkill -f "[a]dapter_tools.py" 2>/dev/null

echo "=== 产物 ==="
for f in count.txt merged.txt stats.txt first.txt; do
  printf '  %-11s = %s\n' "$f" "$(cat $E/agent/work/$f 2>/dev/null | head -3 | tr '\n' '|')"
done
echo "=== 判分 ==="
python3 "$A/eval/rover/r461/judge_r461.py" 2>&1 | head -40
echo "=== done ==="
