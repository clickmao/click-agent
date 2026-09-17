#!/usr/bin/env bash
# R509 重复臂: 同题(p3) × 同夹具 × 多次重复 ⇒ 分离「摆动」与「预算效应」+ 给 codex 外部真值区间。
# 铁律: 起手闸连续 2 PASS; 起手前沉降; 串行(内存硬约束); 判分只吃产物真实行为(铁律11 前置)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover
D=${D:-/tmp/r509/run-r509a}
PORT=${PORT:-48670}
REPS=${REPS:-3}
CODEX_REPS=${CODEX_REPS:-2}
BIN=${BIN:-/tmp/pub_r508b/agenthost}
CODEX=${CODEX:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
TASKS=${TASKS:-p3}
log(){ echo "[$(date +%H:%M:%S)] $*"; }
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
[ -x "$CODEX" ] || { log "[致命] 缺 codex"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占"; exit 4; }
mkdir -p "$D"/{agent,adapter,evidence,logs}
cp -r /tmp/r455_env/agent/cfg "$D/agent/cfg" 2>/dev/null || { log "[致命] 缺 cfg 雏形"; exit 3; }
# 形态守卫 (R509 实测: mkdir 先造出 $D/agent/cfg 会让 cp 嵌套成 cfg/cfg ⇒ 模型目录为空)
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态错: 缺 base/models.yaml"; exit 3; }
grep -rl 48615 "$D/agent/cfg" | xargs -r sed -i "s/48615/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
log "== 起手闸 (需连续 2 PASS) =="
for i in 1 2; do
  python3 "$R/r483/preflight_gate.py" --round R509 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json'))['verdict'])" 2>/dev/null)
  log "  闸$i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸未过"; exit 2; }
done
set -a; . "$REPO/.env.local"; set +a
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
DEMO_OUT="$D/adapter" setsid nohup python3 "$R/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.log" 2>&1 &
APID=$!
for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break; sleep 0.5; done
curl -s -m 3 "http://127.0.0.1:$PORT/v1/models" >/dev/null || { log "[致命] adapter 未就绪"; exit 3; }
sleep 5
run_agent(){ # $1=arm  $2=rep  $3=max_steps(空=默认)
  local out="$D/$1/rep$2" extra=() ms="${3:-}"
  [ -n "$ms" ] && extra=(--max-steps "$ms")
  log "  臂 $1 rep$2 (max-steps=${ms:-默认})"
  python3 "$R/r508/proj_run_side.py" --side agent --arm "$1" --out "$out" --adapter-dir "$D/adapter" \
     --adapter-port "$PORT" --agent-bin "$BIN" --tasks "$TASKS" "${extra[@]}" 2>&1 | tail -1
}
run_codex(){
  log "  codex rep$1"
  python3 "$R/r508/proj_run_side.py" --side codex --arm codex --out "$D/codex/rep$1" --adapter-dir "$D/adapter" \
     --adapter-port "$PORT" --codex-bin "$CODEX" --tasks "$TASKS" 2>&1 | tail -1
}
log "== 本侧默认臂 ×$REPS =="
for i in $(seq 1 "$REPS"); do run_agent agentA "$i"; done
log "== 本侧 显式硬上限=3 ×$REPS =="
for i in $(seq 1 "$REPS"); do run_agent agentD "$i" 3; done
log "== codex ×$CODEX_REPS =="
for i in $(seq 1 "$CODEX_REPS"); do run_codex "$i"; done
kill "$APID" 2>/dev/null; sleep 1; pkill -f "adapter_tools.py $PORT" 2>/dev/null
log "== 判分+聚合 =="
python3 "$R/r509/aggregate_repeats_r509.py" --run-dir "$D" --tasks "$TASKS" --reps "$REPS" \
   --json "$D/report.json" 2>&1 | tail -30
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[告警] 端口未释放" || log "端口已释放"
log "DONE RUN_DIR=$D"
