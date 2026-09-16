#!/usr/bin/env bash
# R457 负控 C3(真机): 无 API key ⇒ 必须"可见失败"(非静默空回复)。零上游调用。
set -uo pipefail
A=/home/agentuser/AgentFramework
E=/tmp/r457_nokey
rm -rf "$E"; mkdir -p "$E/cfg/base" "$E/work/data" "$E/logs"
cp $A/config/base/*.yaml "$E/cfg/base/"
python3 - <<'PY'
import json
json.dump({"turns": ["当前目录下一共有几个 .py 文件？"]},
          open('/tmp/r457_nokey/turn1.json', 'w', encoding='utf-8'), ensure_ascii=False)
PY
cd "$E/work"
env -i PATH=/usr/bin:/bin HOME="$HOME" \
  AGENTFRAMEWORK_FRONTEND_TOKEN=nk-token \
  AGENTFRAMEWORK_CONFIG="$E/cfg" \
  AGENTFRAMEWORK_WORKSPACE="$E/work" \
  setsid nohup /tmp/pub_r457/agenthost --frontend-api 48618 > "$E/logs/host.log" 2>&1 &
echo $! > "$E/logs/host.pid"
sleep 14
cd "$A"
AGENTFRAMEWORK_FRONTEND_TOKEN=nk-token timeout 120 python3 -u eval/rover/r430/drive_task.py 48618 "$E/turn1.json" "$E/logs/turns.jsonl" > "$E/logs/drive.log" 2>&1
echo "drive rc=$?"
kill -9 "$(cat "$E/logs/host.pid")" 2>/dev/null
echo "=== 回复(真值) ==="
python3 - <<'PY'
import json, os
p = '/tmp/r457_nokey/logs/turns.jsonl'
d = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None
ts = d['turns'] if isinstance(d, dict) and 'turns' in d else (d or [])
for i, t in enumerate(ts, 1):
    r = t.get('reply') or t.get('content') or ''
    print(f"  turn{i} len={len(r)} reply={r[:200]!r}")
PY
echo "=== 上游调用数(适配器侧, 应为 0) ==="
ls /tmp/r457_env/logs/adapter/side-agent-*.json 2>/dev/null | wc -l
echo "=== host 告警行 ==="
grep -c "model_unavailable" "$E/logs/host.log" 2>/dev/null || echo 0
