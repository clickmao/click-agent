#!/usr/bin/env bash
# R519: 真任务 —— 游戏类**多文件长任务**(5 模块 / 40 步上界) × 三臂同窗 (单轮32步 / 编排器5×8+scope / codex)
set -u
REPO=/home/agentuser/AgentFramework; R=$REPO/eval/rover/r519
D=$R/run-$(date +%m%d-%H%M%S); mkdir -p "$D"/{logs,adapter} "$D/orch/ws" "$D/single/ws" "$D/codex"
BIN=${R519_AGENT_BIN:-/tmp/pub_r516/agenthost}
CODEX_BIN=${R519_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
PORT=${R519_ADAPTER_PORT:-48691}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }
[ -x "$BIN" ] || { log "[致命] 缺 AOT $BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex $CODEX_BIN"; exit 3; }
echo "run=$D bin=$BIN task=games-longtask-v1" > "$D/.owner-r519"

TS=$(date +%H%M%S)
python3 "$R/mk_taskset_r519.py" > "$D/logs/taskset.txt" 2>&1; TRC=$?
cat "$D/logs/taskset.txt"
[ "$TRC" -eq 0 ] || { log "[致命] 夹具生成失败 rc=$TRC"; exit 3; }

for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R519 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.txt" 2>&1 &
APID=$!
ok=0; for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5; done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill $APID 2>/dev/null; exit 3; }
log "adapter up pid=$APID port=$PORT"; sleep 5
cleanup(){ pkill -f "adapter_tools.py $PORT" 2>/dev/null; log "端口已释放"; log "DONE RUN_DIR=$D"; }
trap cleanup EXIT
set -a; . "$REPO/.env.local"; set +a

PROMPT=$(python3 -c "import json;print(json.load(open('$R/taskset-r519.json',encoding='utf-8'))['tasks'][0]['prompt'])")

log "== 臂 S: 单轮 (硬顶 32 步; 任务上界 40 步) =="
AGENTFRAMEWORK_WORKSPACE="$D/single/ws" AGENTFRAMEWORK_ACTION_MAX_STEPS=32 \
AGENTFRAMEWORK_ACTION_AUDIT="$D/single/audit" \
  timeout 2400 "$BIN" -q "$PROMPT" --output-mode text --session-id "r519-single-$TS" \
  > "$D/logs/arm-S.txt" 2>&1
log "ARM_S_RC=$?"

log "== 臂 O: 编排器 5 节点 × 8 步 + --scope =="
AGENTFRAMEWORK_WORKSPACE="$D/orch/ws" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
  timeout 3000 "$BIN" --orchestrate "$R/plan-games-longtask.txt" --scope "$R/scope-games-longtask.txt" \
  --node-steps 8 --workspace "$D/orch/ws" --session "r519-orch" --report "$D/orch/report.json" \
  > "$D/logs/arm-O.txt" 2>&1
log "ARM_O_RC=$?"

log "== 臂 C: codex-cli (外部真值, 同题面) =="
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-r1 --out "$D/codex/C-r1" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$BIN" --codex-bin "$CODEX_BIN" \
  --taskset "$R/taskset-r519.json" --tasks g1 --timeout 2400 \
  > "$D/logs/arm-C.txt" 2>&1
log "ARM_C_RC=$?"

for arm in single orch; do
  python3 "$R/grade_r519.py" --dir "$D/$arm/ws" --out "$D/grade-$arm.json" \
    > "$D/logs/grade-$arm.txt" 2>&1
  echo "GRADE_${arm}_RC=$?" >> "$D/logs/grade-$arm.txt"
done
GWS=$(find "$D/codex" -type d -name games 2>/dev/null | head -1)
if [ -n "$GWS" ]; then
  python3 "$R/grade_r519.py" --dir "$(dirname "$GWS")" --out "$D/grade-codex.json" \
    > "$D/logs/grade-codex.txt" 2>&1
else
  echo '{"cases":[],"rc":1,"note":"codex 工作区无 games 包"}' > "$D/grade-codex.json"
fi
echo "GRADE_codex_RC=$?" >> "$D/logs/grade-codex.txt"

python3 - "$D" <<'PY' | tee "$D/summary.txt"
import json,sys
d=sys.argv[1]
for arm in ('single','orch','codex'):
    try: j=json.load(open(f'{d}/grade-{arm}.json',encoding='utf-8'))
    except Exception as e: print(f"臂 {arm}: 无判分 {e}"); continue
    cs=j.get('cases') or []
    print(f"臂 {arm}: {sum(1 for c in cs if c.get('ok'))}/{len(cs)} public={j.get('public')} hidden={j.get('hidden')} rc={j.get('rc')}")
PY
log "ALL DONE"
