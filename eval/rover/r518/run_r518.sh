#!/usr/bin/env bash
# R518 主轮: 双包规模面三臂对照 (A=本侧单轮 / C=codex 外部真值 / O=编排器 7 节点)
# 铁律 11: 收口前必跑 exec_precondition --round R518; rc!=0 ⇒ 读数标「参考(未可验收)」。
# 铁律: 禁 push; 内存硬约束 ⇒ 禁并发 (三臂串行); 后台长跑由调用方用 background=true。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r518
PORT=${R518_ADAPTER_PORT:-48694}
DS=${R518_DS:-$(date +%m%d-%H%M%S)}
D=${R518_RUN_DIR:-/tmp/r518/run-$DS}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R518_AGENT_BIN:-/tmp/pub_r518/agenthost}
CODEX_BIN=${R518_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
TASKS=${R518_TASKS:-p3,p4}
WIN=${R518_WINDOW:-w1}
NODE_STEPS=${R518_NODE_STEPS:-6}
NODE_ESC=${R518_NODE_ESCALATIONS:-1}
TMO=${R518_TIMEOUT:-900}
log(){ echo "[$(date +%H:%M:%S)] $*"; }

# --- 0 守卫 ---------------------------------------------------------------
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { log "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { log "[致命] 缺 codex $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { log "[致命] 端口 $PORT 被占用"; exit 4; }
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent" "$D/orch"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT tasks=$TASKS node_steps=$NODE_STEPS esc=$NODE_ESC ts=$(date -Is)" > "$D/.owner-r518"
# 全臂共用: 模型端点必须指到计量 adapter (缺此项 ⇒ 请求绕过 adapter = 无读数; R518 自抓)
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
export AGENTFRAMEWORK_PY_RUN=1

# --- 1 起臂前自检 (fail-closed): 题集 / 计划 / 范围契约 / 预注册 ------------
python3 "$R/build_taskset_r518.py" --check > "$D/logs/taskset-check.txt" 2>&1
trc=$?; tail -3 "$D/logs/taskset-check.txt"
[ "$trc" -eq 0 ] || { log "[致命] 题集自检失败 rc=$trc (禁改题⇒停手)"; exit 3; }

python3 "$R/gen_plan_r518.py" --check > "$D/logs/plan-check.txt" 2>&1
prc=$?; tail -3 "$D/logs/plan-check.txt"
[ "$prc" -eq 0 ] || { log "[致命] 计划/范围契约机检失败 rc=$prc (禁起臂: R517 事故复现防护)"; exit 3; }

[ -f "$R/prereg-r518.json" ] || { log "[致命] 缺预注册 prereg-r518.json (验收面须先写再跑)"; exit 3; }
python3 -c "import json,io;d=json.load(io.open('$R/prereg-r518.json',encoding='utf-8'));assert d['evidence_scope']['require'],'no require';print('PREREG_OK require=%s'%d['evidence_scope']['require'])"

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R518 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 3 adapter (起手后沉降) -----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.log" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do
  curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
sleep 3
log "adapter 就绪 (pid=$APID, dump=$D/adapter)"

maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }

# --- 4 三臂串行 ------------------------------------------------------------
# A: 本侧单轮 (链路默认步数)
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side agent --arm A-r1 --out "$D/A-r1" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" \
  --taskset "$R/taskset-r518.json" --tasks "$TASKS" --timeout "$TMO" \
  > "$D/logs/run-A.txt" 2>&1
log "臂 A-r1 rc=$? (tail: $(tail -1 "$D/logs/run-A.txt" 2>/dev/null))"

# C: 外部真值 codex (同题面)
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-r1 --out "$D/C-r1" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
  --taskset "$R/taskset-r518.json" --tasks "$TASKS" --timeout "$TMO" \
  > "$D/logs/run-C.txt" 2>&1
log "臂 C-r1 rc=$? (tail: $(tail -1 "$D/logs/run-C.txt" 2>/dev/null))"

# O: 编排器 7 节点 (新链代码: 预算自适应)
# cwd 必须是**仓库根**: 宿主自身状态 (data/**: sessions/telemetry/guardrails) 按 cwd 相对落盘;
# 若 cwd=节点工作区 ⇒ 宿主自写文件会被节点 diff 判 out_of_scope ⇒ 整链 fail-closed (R518 自抓事故 2)。
W="$D/orch/ws"; mkdir -p "$W"
I0=$(maxidx)
cd "$REPO" || exit 3
AGENTFRAMEWORK_WORKSPACE="$W" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
"$AGENT_BIN" --orchestrate "$R/plan-p3p4-r518.txt" --scope "$R/scope-p3p4-r518.txt" \
  --node-steps "$NODE_STEPS" --node-escalations "$NODE_ESC" --max-nodes 12 \
  --workspace "$W" --report "$D/orch/report.json" --session "r518s-orch-$DS" \
  > "$D/logs/arm-O.txt" 2>&1
orc=$?
I1=$(maxidx)

cd "$REPO" || exit 3
echo "$I0 $I1" > "$D/orch/idx-range.txt"
log "臂 O-r1 rc=$orc adapter_range=[$((I0+1)),$I1]"

# --- 5 判分 + 冻结 (铁律 11 前置器入口) ------------------------------------
python3 "$REPO/eval/rover/r513/aggregate_r513.py" --run-dir "$D" --json "$D/report.json" \
  > "$D/logs/report.txt" 2>&1
log "聚合 rc=$? → $D/report.json"

python3 "$R/freeze_snapshot_r518.py" --run-dir "$D" --window "$WIN" --write --json "$D/report.json" \
  --map A-r1=agentA --map C-r1=codex > "$D/logs/freeze.txt" 2>&1
frc=$?; tail -2 "$D/logs/freeze.txt"
[ "$frc" -eq 0 ] || { log "[致命] 冻结($WIN A/C) rc=$frc"; }

python3 "$R/freeze_orch_r518.py" --run-dir "$D" --orch-dir "$D/orch" --window "$WIN" --snapshot-dir agentO \
  --tag O --arm O-r1 --tasks "$TASKS" --idx-before "$I0" --idx-after "$I1" \
  --adapter-dir "$D/adapter" --write --append > "$D/logs/freeze-orch.txt" 2>&1
orc_f=$?; tail -2 "$D/logs/freeze-orch.txt"
log "冻结(w1 O) rc=$orc_f"

# --- 6 铁律 11 收口器 -----------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round R518 > "$D/logs/precond.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$D/logs/precond.txt"
tail -25 "$D/logs/precond.txt"
log "PRECOND_RC=$prc (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 7 收口 ----------------------------------------------------------------
kill "$APID" 2>/dev/null
sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{
  echo "R518 收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"
  echo "arms: A-r1 (agent) / C-r1 (codex) / O-r1 (orchestrator ${NODE_STEPS}步+${NODE_ESC}次升预算)"
  echo "precond_rc=$prc"; echo "idx_range=$I0,$I1"
  echo "--- src shas ---"; sha256sum "$AGENT_BIN" "$R/taskset-r518.json" "$R/plan-p3p4-r518.txt" "$R/scope-p3p4-r518.txt" "$R/prereg-r518.json"
} > "$D/SUMMARY-r518.txt" 2>&1
log "完成: $D"
exit 0
