#!/usr/bin/env bash
# R460 实跑: 同夹具/同 6 轮/同模型/同开关, 唯一差异 = 二进制 (R458 → R460) + ADAPTER_DUMP_FULL=1 (器具面: 全量实发文本)。
set -uo pipefail
A=/home/agentuser/AgentFramework
E=/tmp/r460_env
OUT=$E/logs
BIN=/tmp/pub_r460/agenthost
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

echo "=== 我方 host (R460: 承接块 8→3 项 + 菜单单源 + 插入语瘦身) ==="
cd $E/agent/work
AGENTFRAMEWORK_FRONTEND_TOKEN=r460-token AGENTFRAMEWORK_CONFIG=$E/agent/cfg \
  AGENTFRAMEWORK_WORKSPACE=$E/agent/work \
  AGENTFRAMEWORK_ACTION_LOOP=on \
  AGENTFRAMEWORK_PLAN_RESUME_FALLTHROUGH=on \
  AGENTFRAMEWORK_ACTION_AUDIT="$OUT/audit" \
  setsid nohup $BIN --frontend-api 48617 > "$OUT/host-agent.log" 2>&1 &
echo $! > "$OUT/host-agent.pid"
sleep 15
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=r460-token timeout 900 python3 -u eval/rover/r430/drive_task.py 48617 \
  $E/suite-turns.json "$OUT/agent-turns.jsonl" > "$OUT/agent-drive.log" 2>&1
echo "[agent] rc=$?"
kill -9 "$(cat "$OUT/host-agent.pid")" 2>/dev/null
pkill -f "[a]dapter_tools.py" 2>/dev/null

echo "=== 产物 ==="
for f in count.txt merged.txt stats.txt first.txt; do
  printf '  %-11s = %s\n' "$f" "$(cat $E/agent/work/$f 2>/dev/null | head -3 | tr '\n' '|')"
done
echo "=== 归因 (实发文本) ==="
python3 "$A/eval/rover/r460/attr_r460.py" "$OUT/adapter" 2>&1 | head -40
echo "=== done ==="
