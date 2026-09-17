#!/usr/bin/env bash
# R509 正式重复臂 (修正版): 每跑次独立会话 (--arm 带 -r<N> ⇒ session-id 唯一),
# 规避窗口 b 的「会话态污染」(rep1 共享 session ⇒ 首个调用退化, 0/12)。
# 臂 A = 默认预算; 臂 D = 显式 AGENTFRAMEWORK_ACTION_MAX_STEPS=3。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
BIN=${BIN:-/tmp/pub_r508b/agenthost}
D=${D:-/tmp/r509/run-r509c}
PORT=${PORT:-48674}
REPS=${REPS:-3}
TASKS=${TASKS:-p3}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$D"/{agent,adapter,evidence,logs}
[ -d "$D/agent/cfg" ] || cp -r /tmp/r455_env/agent/cfg "$D/agent/cfg"
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态 (base/models.yaml 缺)"; exit 3; }
grep -rl "486[0-9][0-9]" "$D/agent/cfg" | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺 bin $BIN"; exit 3; }
for i in 1 2; do
  python3 "$R/r483/preflight_gate.py" --round R509 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json'))['verdict'])" 2>/dev/null)
  log "闸$i: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过"; exit 2; }
done
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
DEMO_OUT="$D/adapter" setsid nohup python3 "$R/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 & APID=$!
ok=0; for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 1; done
[ "$ok" = 1 ] || { log "[致命] adapter 未就绪"; kill $APID 2>/dev/null; exit 3; }
log "adapter up port=$PORT"; sleep 8
cd "$REPO"
run_one(){ local arm="$1" rep="$2" ms="${3:-}" extra=() out="$D/$1/rep$2"
  [ -n "$ms" ] && extra=(--max-steps "$ms")
  log "  臂 $arm rep$rep (ms=${ms:-默认})"
  python3 "$R/r508/proj_run_side.py" --side agent --tasks "$TASKS" --out "$out" \
    --agent-bin "$BIN" --cwd "$REPO" --arm "$arm-r$rep" --timeout 600 --adapter-dir "$D/adapter" \
    "${extra[@]}" 2>&1 | tail -1
}
for i in $(seq 1 "$REPS"); do run_one agentA "$i"; done
for i in $(seq 1 "$REPS"); do run_one agentD "$i" 3; done
kill $APID 2>/dev/null; sleep 1
log "== 聚合 =="
python3 "$R/r509/aggregate_repeats_r509.py" --run-dir "$D" --tasks "$TASKS" --reps "$REPS" --json "$D/report.json" | tail -20
log "DONE"
