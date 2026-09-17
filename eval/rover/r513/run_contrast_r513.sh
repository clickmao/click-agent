#!/usr/bin/env bash
# R513 项目级对照跑器 (题面 v2 修订后重测): 同环境·同输入·同模型; 两臂 = 本侧 agent(默认预算) vs codex-cli。
# 每跑次独立会话; 起手闸连续 2 PASS; 起手前沉降; 单变量 (仅实现体不同); 判分只吃产物真实行为。
# 窗口: w1 = {A-r1→agentA, C-r1→codex} / w2 = {A-r2→agentA, C-r2→codex}; 快照入库后跑铁律11 前置器。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r513
PORT=${R513_ADAPTER_PORT:-48692}
TS=${R513_TS:-$(date +%m%d-%H%M%S)}
D=${R513_RUN_DIR:-/tmp/r513/run-$TS}
AGENT_BIN=${R513_AGENT_BIN:-/tmp/pub_r511/agenthost}
CODEX_BIN=${R513_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
CFGSRC=${R513_CFG_SEED:-/tmp/r455_env/agent/cfg}
TASKS=${R513_TASKS:-p4}
REPS=${R513_REPS:-2}
TMO=${R513_TIMEOUT:-1500}
log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- 0 守卫 ---------------------------------------------------------------
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { log "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex $CODEX_BIN"; exit 3; }
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 被占用"; exit 4; fi
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态守卫失败 (缺 base/models.yaml ⇒ 疑似嵌套)"; exit 3; }
echo "run=$D port=$PORT tasks=$TASKS reps=$REPS ts=$(date -Is)" > "$D/.owner-r513"

# --- 1 题集自检 + 预注册 (起臂前, fail-closed) -----------------------------
python3 "$R/build_taskset_r513.py" --check > "$D/logs/taskset-check.txt" 2>&1
trc=$?; tail -2 "$D/logs/taskset-check.txt"
[ "$trc" -eq 0 ] || { log "[致命] 题面自检失败 rc=$trc (禁改题⇒停手)"; exit 3; }
python3 "$R/make_prereg_r513.py" --write --out "$R/prereg-r513.json" > "$D/logs/prereg.txt" 2>&1
prc=$?; tail -1 "$D/logs/prereg.txt"
[ "$prc" -eq 0 ] || { log "[致命] 预注册失败 rc=$prc"; exit 3; }

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R513 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 3 adapter (起手后沉降) ------------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.log" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do
  curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
log "adapter up pid=$APID port=$PORT"; sleep 5

# --- 4 两臂 × reps 串行 (内存硬约束: 禁并发) ------------------------------
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
run_arm() { # tag side reps [extra...]
  local tag=$1 side=$2 reps=$3; shift 3
  for k in $(seq 1 "$reps"); do
    local out="$D/$tag-r$k"
    log "== 臂 $tag-r$k ($side) =="
    python3 "$R/../r511/proj_run_side.py" --side "$side" --arm "$tag-r$k" --out "$out" \
      --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --codex-bin "$CODEX_BIN" \
      --taskset "$R/taskset-r513.json" --tasks "$TASKS" --timeout "$TMO" \
      > "$D/logs/arm-$tag-r$k.txt" 2>&1
    local rc=$?
    echo "arm=$tag-r$k rc=$rc" >> "$D/logs/arm-$tag-r$k.txt"
    log "臂 $tag-r$k rc=$rc"
    sleep 3
  done
}
run_arm A agent "$REPS"
run_arm C codex "$REPS"

# --- 5 汇总判分 -----------------------------------------------------------
python3 "$R/aggregate_r513.py" --run-dir "$D" --json "$D/report.json" 2>&1 | tee "$D/logs/report.txt"
echo "REPORT_RC=${PIPESTATUS[0]}" >> "$D/logs/report.txt"
cp "$D/report.json" "$D/evidence/report.json" 2>/dev/null

# --- 6 快照入库 (不可变) + 铁律11 前置器 ----------------------------------
for k in $(seq 1 "$REPS"); do
  python3 "$R/freeze_snapshot_r513.py" --run-dir "$D" --window "w$k" --write --json "$D/report.json" \
    --map "A-r$k=agentA" --map "C-r$k=codex" 2>&1 | tee "$D/logs/freeze-w$k.txt"
done
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round R513 > "$D/logs/precond.txt" 2>&1
echo "PRECOND_RC=$?" | tee -a "$D/logs/precond.txt"

# --- 7 teardown (按命名空间扫 /proc + 端口断言) ---------------------------
kill "$APID" 2>/dev/null
sleep 2
pkill -f "adapter_tools.py $PORT" 2>/dev/null
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[告警] 端口 $PORT 未释放"; else log "端口已释放"; fi
log "DONE RUN_DIR=$D"
