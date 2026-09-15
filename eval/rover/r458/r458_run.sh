#!/usr/bin/env bash
# R458 实跑: 同夹具/同 6 轮/同模型(deepseek-flash 经 48615 适配器)/同开关, 唯一差异 = 二进制 (R457 → R458)。
set -uo pipefail
A=/home/agentuser/AgentFramework
E=/tmp/r458_env
OUT=$E/logs
mkdir -p "$OUT/adapter"
cd "$A"

echo "=== 夹具 md5 (与 R457 同源) ==="
md5sum $E/agent/work/* | awk '{print $1}' | sort | md5sum | sed 's/^/  agent(pristine): /'

echo "=== 密钥 ==="
set -a; . "$A/.env.local"; set +a
test -n "${AGENTFRAMEWORK_KEYS_DEEPSEEK:-}" && echo "  keys: SET" || echo "  keys: MISSING"

echo "=== 适配器 ==="
pkill -f "[a]dapter_tools.py" 2>/dev/null; sleep 1
mkdir -p /tmp/cxprobe; cd /tmp/cxprobe
DEMO_OUT=$OUT/adapter setsid nohup python3 -u "$A/eval/rover/r455/adapter_tools.py" 48615 > "$OUT/adapter/adapter.log" 2>&1 &
echo $! > /tmp/cxprobe/adapter.pid; sleep 3
echo "  adapter pid=$(cat /tmp/cxprobe/adapter.pid)";

echo "=== 我方 host (R458: 承接轮接地块 + 人话承接 + 兜底收口) ==="
cd $E/agent/work
AGENTFRAMEWORK_FRONTEND_TOKEN=r458-token AGENTFRAMEWORK_CONFIG=$E/agent/cfg \
  AGENTFRAMEWORK_WORKSPACE=$E/agent/work \
  AGENTFRAMEWORK_ACTION_LOOP=on \
  AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH=on \
  AGENTFRAMEWORK_ACTION_AUDIT="$OUT/audit" \
  setsid nohup /tmp/pub_r458/agenthost --frontend-api 48617 > "$OUT/host-agent.log" 2>&1 &
echo $! > "$OUT/host-agent.pid"
sleep 15
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=r458-token timeout 900 python3 -u eval/rover/r430/drive_task.py 48617 \
  $E/suite-turns.json "$OUT/agent-turns.jsonl" > "$OUT/agent-drive.log" 2>&1
echo "[agent] rc=$?"
kill -9 "$(cat "$OUT/host-agent.pid")" 2>/dev/null
pkill -f "[a]dapter_tools.py" 2>/dev/null

echo "=== 产物 ==="
for f in count.txt merged.txt stats.txt first.txt; do
  printf '  %-11s = %s\n' "$f" "$(cat $E/agent/work/$f 2>/dev/null | head -3 | tr '\n' '|')"
done
echo "=== 动作环审计 (args_head 原文) ==="
tail -8 "$OUT/audit/action_loop.jsonl" 2>/dev/null | cut -c1-200
echo "=== R458 新增遥测 (承接轮) ==="
for p in "$E/agent/work/data/telemetry/host.jsonl" "$OUT/host.jsonl" "$A/data/telemetry/host.jsonl"; do
  [ -f "$p" ] && { echo "  [$p]"; grep -ho '"event":"[a-z_]*"' "$p" | sort | uniq -c | sort -rn | head -12; break; }
done
echo "=== done ==="
