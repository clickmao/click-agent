#!/usr/bin/env bash
# R509 补跑 (修缺陷后): 仅重跑本侧臂 A(默认)/D(显式硬上限=3) ×REPS。
# 缺陷: 首版 mkdir 造出 $D/agent/cfg ⇒ cp 嵌套 cfg/cfg ⇒ 模型目录为空 ⇒ 臂 0 调用(全废)。
# 本脚本: ① 形态守卫; ② 起手闸连续 2 PASS; ③ 同窗口同 adapter 目录(与 codex dumps 合并, 文件名不冲突)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
D=${D:-/tmp/r509/run-r509b}
PORT=${PORT:-48672}
REPS=${REPS:-3}
TASKS=${TASKS:-p3}
BIN=${BIN:-/tmp/pub_r508b/agenthost}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
[ -d "$D" ] || { log "[致命] 缺 $D"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占"; exit 4; }
rm -rf "$D/agentA" "$D/agentD"; rm -rf "$D/agent/cfg"
cp -r /tmp/r455_env/agent/cfg "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态错"; exit 3; }
grep -rl 48615 "$D/agent/cfg" 2>/dev/null | xargs -r sed -i "s/48615/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
log "== 起手闸 =="
for i in 1 2; do
  python3 "$R/r483/preflight_gate.py" --round R509 --out "$D/gate-rerun-$i.json" > "$D/logs/gate-rerun-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-rerun-$i.json'))['verdict'])" 2>/dev/null)
  log "  闸$i: $v"; [ "$v" = "PASS" ] || { log "[致命] 闸未过"; exit 2; }
done
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
DEMO_OUT="$D/adapter" setsid nohup python3 "$R/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter2.log" 2>&1 &
APID=$!
ok=0; for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5; done
[ "$ok" = 1 ] || { log "[致命] adapter 未就绪"; exit 3; }
log "adapter2 up pid=$APID port=$PORT"; sleep 5
run_one(){ # arm rep maxsteps
  local out="$D/$1/rep$2" ms="${3:-}" extra=()
  [ -n "$ms" ] && extra=(--max-steps "$ms")
  log "  臂 $1 rep$2 max-steps=${ms:-默认}"
  python3 "$R/r508/proj_run_side.py" --side agent --arm "$1" --out "$out" --adapter-dir "$D/adapter" \
    --adapter-port "$PORT" --agent-bin "$BIN" --tasks "$TASKS" "${extra[@]}" 2>&1 | tail -1
}
for i in $(seq 1 "$REPS"); do run_one agentA "$i"; done
for i in $(seq 1 "$REPS"); do run_one agentD "$i" 3; done
kill "$APID" 2>/dev/null; sleep 1
log "== 聚合 =="
python3 "$R/r509/aggregate_repeats_r509.py" --run-dir "$D" --tasks "$TASKS" --reps "$REPS" --json "$D/report.json" 2>&1 | tail -25
log "DONE RERUN"
