#!/usr/bin/env bash
# R517: 主线回归 (编排器 × codex 外部真值, 同题面·同窗·同模型) —— 三臂 = agent 单轮6步 / agent 编排器3节点×6步(+--scope) / codex-cli
set -u
REPO=/home/agentuser/AgentFramework; R=$REPO/eval/rover/r517
D=$R/run-$(date +%m%d-%H%M%S); mkdir -p "$D"/{logs,adapter} "$D/orch/ws" "$D/single/ws" "$D/codex"
BIN=${R517_AGENT_BIN:-/tmp/pub_r516/agenthost}
CODEX_BIN=${R517_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
PORT=${R517_ADAPTER_PORT:-48690}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex $CODEX_BIN"; exit 3; }
echo "run=$D bin=$BIN" > "$D/.owner-r517"

# --- 0 题面同源断言 (fail-closed): r512 taskset p4 题面 vs r511 (本侧计划源) ---
TS=$(date +%H%M%S)
python3 "$R/mk_taskset_r517.py" > "$D/logs/taskset.txt" 2>&1; TRC=$?
cat "$D/logs/taskset.txt"
[ "$TRC" -eq 0 ] || { log "[致命] 题面同源断言失败 rc=$TRC"; exit 3; }

# --- 1 起手闸: 连续 2 次 PASS ---
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R517 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2 adapter (起手后沉降) ---
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.txt" 2>&1 &
APID=$!
ok=0; for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5; done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill $APID 2>/dev/null; exit 3; }
log "adapter up pid=$APID port=$PORT"; sleep 5
cleanup(){ pkill -f "adapter_tools.py $PORT" 2>/dev/null; log "端口已释放"; log "DONE RUN_DIR=$D"; }
trap cleanup EXIT
set -a; . "$REPO/.env.local"; set +a

# --- 3 三臂串行 (内存硬约束: 禁并发) ---
PROMPT=$(python3 -c "import json;print(json.load(open('$R/taskset-r517.json',encoding='utf-8'))['tasks'][0]['prompt'])")
log "== 臂 S: 单轮一次成型 6 步 =="
AGENTFRAMEWORK_WORKSPACE="$D/single/ws" AGENTFRAMEWORK_ACTION_MAX_STEPS=6 \
AGENTFRAMEWORK_ACTION_AUDIT="$D/single/audit" \
  timeout 900 "$BIN" -q "$PROMPT" --output-mode text --session-id "r517-single-$TS" \
  > "$D/logs/arm-S.txt" 2>&1
log "ARM_S_RC=$?"

log "== 臂 O: 编排器 3 节点 × 6 步 + --scope =="
AGENTFRAMEWORK_WORKSPACE="$D/orch/ws" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
  timeout 1200 "$BIN" --orchestrate "$R/plan-p4-v3.txt" --scope "$R/scope-p4.txt" \
  --node-steps 6 --workspace "$D/orch/ws" --session "r517-orch" --report "$D/orch/report.json" \
  > "$D/logs/arm-O.txt" 2>&1
log "ARM_O_RC=$?"

log "== 臂 C: codex-cli (外部真值) =="
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-r1 --out "$D/codex/C-r1" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$BIN" --codex-bin "$CODEX_BIN" \
  --taskset "$R/taskset-r517.json" --tasks p4 --timeout 1500 \
  > "$D/logs/arm-C.txt" 2>&1
log "ARM_C_RC=$?"

# --- 4 判分 (只判副本) ---
for arm in single orch; do
  rm -rf "$D/grade-$arm"; mkdir -p "$D/grade-$arm"
  [ -d "$D/$arm/ws/tasksvc" ] && cp -r "$D/$arm/ws/tasksvc" "$D/grade-$arm/"
  python3 "$REPO/eval/rover/r511/grade_r511.py" --task p4 --dir "$D/grade-$arm" \
    --json "$D/grade-$arm.json" > "$D/logs/grade-$arm.txt" 2>&1
  echo "GRADE_${arm}_RC=$?" >> "$D/logs/grade-$arm.txt"
done
WS=$(find "$D/codex" -type d -name tasksvc 2>/dev/null | head -1)
rm -rf "$D/grade-codex"; mkdir -p "$D/grade-codex"
[ -n "$WS" ] && cp -r "$WS" "$D/grade-codex/"
python3 "$REPO/eval/rover/r511/grade_r511.py" --task p4 --dir "$D/grade-codex" \
  --json "$D/grade-codex.json" > "$D/logs/grade-codex.txt" 2>&1
echo "GRADE_codex_RC=$?" >> "$D/logs/grade-codex.txt"

python3 - "$D" <<'PY' | tee "$D/summary.txt"
import json,sys,os
d=sys.argv[1]
for arm in ('single','orch','codex'):
    p=f'{d}/grade-{arm}.json'
    try: j=json.load(open(p,encoding='utf-8'))
    except Exception as e: print(f"臂 {arm}: 无判分 {e}"); continue
    cases=j.get('cases') or j.get('results') or []
    ok=sum(1 for c in cases if c.get('ok') or c.get('pass'))
    print(f"臂 {arm}: {ok}/{len(cases)} rc={j.get('rc')}")
PY
python3 "$REPO/eval/rover/r515/summarize_r515.py" "$D" 2>/dev/null | tail -3
log "ALL DONE"
