#!/usr/bin/env bash
# R521 主轮: 游戏类多文件长任务 (games-longtask-v1, 58 用例) **三臂同窗**对照 + 硬前门.
#   臂 A = 本侧单轮 (AOT /tmp/pub_r520) / 臂 C = 外部真值 codex-cli (同一真实模型) / 臂 O = 编排器 5 节点×8 步 + --scope
# 铁律 11: 收口前必跑 exec_precondition --round r521; rc!=0 ⇒ 降幅标「参考(未可验收)」。
# 铁律: 禁 push; 三臂串行 (内存硬约束, 禁并发)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r521
R519=$REPO/eval/rover/r519
PORT=${R521_ADAPTER_PORT:-48695}
DS=${R521_DS:-$(date +%m%d-%H%M%S)}
D=${R521_RUN_DIR:-$R/run-$DS}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R521_AGENT_BIN:-/tmp/pub_r520/agenthost}
CODEX_BIN=${R521_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
WIN=${R521_WINDOW:-w1}
TMO=${R521_TIMEOUT:-2400}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) --------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent" "$D/orch"
cp -r "$CFGSRC" "$D/agent/cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN ts=$(date -Is)" > "$D/.owner-r521"
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"      # 缺此项 ⇒ 请求绕过计量 adapter = 无读数 (R518 自抓)
export AGENTFRAMEWORK_PY_RUN=1
cd "$REPO" || exit 3                                # cwd 必须=仓根 (宿主自写 data/** 否则被判节点越界)

# --- 1 起臂前硬前门 (候选③: 契约机检接入轮脚本) ---------------------------
python3 "$R/build_taskset_r521.py" --check > "$D/logs/taskset-check.txt" 2>&1
trc=$?; tail -2 "$D/logs/taskset-check.txt"
[ "$trc" -eq 0 ] || { log "[致命] 题集自检失败 rc=$trc (禁改题)"; exit 3; }

# 同输入铁律: 计划/范围与 R519 逐字节相同 (md5 机检, 不许漂移)
mp=$(md5sum "$R/plan-games-longtask.txt" "$R519/plan-games-longtask.txt" | awk '{print $1}' | uniq | wc -l)
ms=$(md5sum "$R/scope-games-longtask.txt" "$R519/scope-games-longtask.txt" | awk '{print $1}' | uniq | wc -l)
{ echo "plan_md5=$(md5sum "$R/plan-games-longtask.txt" | awk '{print $1}')"; echo "scope_md5=$(md5sum "$R/scope-games-longtask.txt" | awk '{print $1}')"; } | tee "$D/logs/input-pins.txt"
[ "$mp" -eq 1 ] && [ "$ms" -eq 1 ] || { log "[致命] 计划/范围与 R519 不同 ⇒ 非同输入, 停手"; exit 3; }

python3 "$REPO/eval/rover/r518/check_plan_contract.py" --plan "$R/plan-games-longtask.txt" \
  --scope "$R/scope-games-longtask.txt" --out "$D/logs/contract-gate.json" > "$D/logs/contract-gate.txt" 2>&1
crc=$?; tail -6 "$D/logs/contract-gate.txt"
[ "$crc" -eq 0 ] || { log "[致命] 计划/范围契约机检 rc=$crc (禁起臂: R517 事故复现防护)"; exit 3; }
log "契约硬前门 PASS (rc=0)"

[ -f "$R/prereg-r521.json" ] || { log "[致命] 缺预注册 (验收面须先写再跑)"; exit 3; }
python3 -c "import json,io;d=json.load(io.open('$R/prereg-r521.json',encoding='utf-8'));assert d['evidence_scope']['require'],'no require';print('PREREG_OK require=%s nonrequired=%s'%(d['evidence_scope']['require'],[e['pattern'] for e in d['evidence_scope'].get('nonrequired',[])]))"

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R521 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 3 adapter -------------------------------------------------------------
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
# 臂 A: 单轮. 必带 --max-steps>0 (R521 缺陷复盘: 缺此参 ⇒ 工具面关闭 ⇒ CLI 退回纯对话 ⇒ 0 产物)
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side agent --arm A-r1 --out "$D/A-r1" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
  --taskset "$R/taskset-r521.json" --tasks g1 --timeout "$TMO" > "$D/logs/run-A.txt" 2>&1
log "臂 A-r1 rc=$? ($(tail -1 "$D/logs/run-A.txt" 2>/dev/null))"
if [ -z "$(find "$D/A-r1" -path '*/work/*' -type f -print -quit 2>/dev/null)" ]; then
  log "[致命] 臂 A-r1 产物树为空 (工具面/落盘失效) ⇒ 该臂按 fail-closed 记账, 不得当绿"
fi

python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-r1 --out "$D/C-r1" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
  --taskset "$R/taskset-r521.json" --tasks g1 --timeout "$TMO" > "$D/logs/run-C.txt" 2>&1
log "臂 C-r1 rc=$? ($(tail -1 "$D/logs/run-C.txt" 2>/dev/null))"

W="$D/orch/ws"; mkdir -p "$W"
I0=$(maxidx)
AGENTFRAMEWORK_WORKSPACE="$W" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
"$AGENT_BIN" --orchestrate "$R/plan-games-longtask.txt" --scope "$R/scope-games-longtask.txt" \
  --node-steps 8 --max-nodes 12 --workspace "$W" --report "$D/orch/report.json" \
  --session "r521-orch-$DS" > "$D/logs/arm-O.txt" 2>&1
orc=$?
I1=$(maxidx)
cd "$REPO" || exit 3
log "臂 O-r1 rc=$orc adapter_range=[$((I0+1)),$I1]"
python3 "$REPO/eval/rover/r520/shadow_check_r520.py" --root "$W" > "$D/logs/shadow-check.txt" 2>&1
log "影子机检 rc=$? ($(head -1 "$D/logs/shadow-check.txt"))"
python3 "$R/../r519/grade_r519.py" --dir "$W" --out "$D/grade-orch-live.json" > "$D/logs/grade-orch.txt" 2>&1
log "编排臂活判分 rc=$? (仅参考, 判分权威 = 快照) "

# --- 5 冻结 (判分只吃仓内不可变快照) + 汇总 --------------------------------
python3 "$R/freeze_r521.py" --run-dir "$D" --window "$WIN" --adapter-dir "$D/adapter" \
  --map A-r1=agentA --map C-r1=codex --orch-run O-r1 --orch-snap agentO --orch-ws "$W" \
  --orch-idx "$I0,$I1" --orch-rc "$orc" --write > "$D/logs/freeze.txt" 2>&1
frc=$?; tail -6 "$D/logs/freeze.txt"
log "冻结/汇总 rc=$frc"

# --- 6 铁律 11 收口器 -----------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r521 > "$D/logs/precond.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$D/logs/precond.txt"
tail -22 "$D/logs/precond.txt"
log "PRECOND_RC=$prc (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 7 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R521 收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "arms: A-r1(单轮) / C-r1(codex 外部真值) / O-r1(编排 5×8 + --scope)"
  echo "precond_rc=$prc"; echo "idx A/C/O=$I0,$I1"
  sha256sum "$R/taskset-r521.json" "$R/prereg-r521.json" "$R/plan-games-longtask.txt" "$R/scope-games-longtask.txt"; } \
  > "$D/SUMMARY-r521.txt" 2>&1
cp -f "$D/SUMMARY-r521.txt" "$R/evidence/SUMMARY-r521.txt" 2>/dev/null
log "完成: $D"
exit 0
