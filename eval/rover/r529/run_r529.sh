#!/usr/bin/env bash
# R529 主轮: **主线扩面 (第二题族, 非游戏) + 外部真值失败窗 unreliable 判据化 + completion 按类分解**。
#
# 与 R528 主轮的差别 (仅评测面, 链代码与 AOT 二进制逐字节不变 ⇒ 与 R528 同二进制, 可对照):
#  ① 题集两题: g1 = F1 锚 (58 隐藏用例, 题面逐字节复用 r528) / t1 = F2 新族 (toolkit 多文件包, 30 隐藏用例)
#  ② 三臂均跑两题 (--tasks g1,t1); 快照目录名 = 自报臂标签 (agentA0-off/agentA1-on/codex) ⇒ 消除 claim_unmapped
#  ③ 同输入硬门把**两题**都钉 (F1 钉 sha 常量, F2 钉 taskset 自述 sha) 
#  ④ 收口走 unreliable 策略 (J2/J3): 策略在 prereg 内**起臂前**声明, 前置器机检 policy_declared_ts <= artifacts mtime
# 铁律: 禁 push; 三臂串行 (2 vCPU/3.57 GiB); 臂后必 AOT 无关 (本轮不改链代码)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r529
PORT=${R529_ADAPTER_PORT:-48799}
DS=${R529_DS:-$(date +%m%d-%H%M%S)}
D=${R529_RUN_DIR:-$R/run-$DS}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R529_AGENT_BIN:-/tmp/pub_r528/agenthost}
CODEX_BIN=${R529_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
WIN=${R529_WINDOW:-w1}
TMO=${R529_TIMEOUT:-2400}
TASKSET=$R/taskset-r529.json
PIN_F1=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
ALSO=${R529_ALSO:-}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) --------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$R/prereg-r529.json" ] || { echo "[致命] 缺预注册 (验收面/策略须先写再跑)"; exit 3; }
[ -f "$TASKSET" ] || { echo "[致命] 缺题集 $TASKSET"; exit 3; }
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent"
cp -r "$CFGSRC" "$D/agent/cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN ts=$(date -Is)" > "$D/.owner-r529"
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"      # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 (两题) ---------------------------------------------------
python3 - "$TASKSET" "$PIN_F1" > "$D/logs/input-pins.txt" 2>&1 <<'PY'
import hashlib, io, json, sys
ts, pin_f1 = sys.argv[1], sys.argv[2]
d = json.load(io.open(ts, encoding="utf-8"))
ok = True
for t in d["tasks"]:
    p = t.get("prompt") or ""
    h = hashlib.sha256(p.encode()).hexdigest()
    decl = t.get("prompt_sha256")
    same = (h == decl)
    is_f1 = (t["tid"] == "g1")
    pin_ok = (h == pin_f1) if is_f1 else same
    print("tid=%s family=%s prompt_sha256=%s declared=%s self_consistent=%s anchor_pin_ok=%s cases=%s" %
          (t["tid"], t.get("family"), h[:16], (decl or "")[:16], same, pin_ok, t.get("hidden_cases")))
    ok = ok and same and pin_ok
print("INPUT_PINS_OK=%s" % ok)
sys.exit(0 if ok else 3)
PY
prc=$?; cat "$D/logs/input-pins.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (F1 钉锚 + F2 自述 sha 一致)"

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R529 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
log "adapter 就绪 (pid=$APID, dump=$D/adapter, FULL=1)"
maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }
run_arm(){  # $1=run名 $2=out目录 $3=附加env
  local i0 i1
  i0=$(maxidx)
  env $3 python3 "$REPO/eval/rover/r511/proj_run_side.py" --side agent --arm "$1" --out "$2" \
    --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
    --taskset "$TASKSET" --tasks g1,t1 --timeout "$TMO" > "$D/logs/run-$1.txt" 2>&1
  local rc=$?
  i1=$(maxidx)
  log "臂 $1 rc=$rc adapter_range=[$((i0+1)),$i1] ($(tail -1 "$D/logs/run-$1.txt" 2>/dev/null))"
  local empty=0
  for tid in g1 t1; do
    if [ -z "$(find "$2/$tid/work" -type f -print -quit 2>/dev/null)" ]; then
      log "[警告] 臂 $1/$tid 产物树为空 (工具面/落盘失效) ⇒ 该臂-题按 fail-closed 记账, 不得当绿"
      empty=$((empty+1))
    fi
  done
  echo "$1 $((i0+1)) $i1 $empty" >> "$D/logs/idx.txt"
}

# --- 4 三臂串行 (基线在前, 避免开窗冷启偏差记到处理臂) ----------------------
run_arm A0-off "$D/A0-off" "AGENTFRAMEWORK_ACTION_DISCIPLINE=off"
run_arm A1-on  "$D/A1-on"  ""
C0=$(ls "$D/adapter" 2>/dev/null | grep -c '^side-codex-' || true)
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-codex --out "$D/C-codex" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
  --taskset "$TASKSET" --tasks g1,t1 --timeout "$TMO" > "$D/logs/run-C-codex.txt" 2>&1
crc=$?
C1=$(ls "$D/adapter" 2>/dev/null | grep -c '^side-codex-' || true)
echo "C-codex $((C0+1)) $C1 0" >> "$D/logs/idx.txt"
log "臂 C-codex rc=$crc adapter_range=[$((C0+1)),$C1] ($(tail -1 "$D/logs/run-C-codex.txt" 2>/dev/null))"

# --- 5 前缀稳定性机检 (常量 system + 首调用命中 + 步间涨幅 + 回执) ----------
A0R=$(awk '$1=="A0-off"{print $2","$3}' "$D/logs/idx.txt")
A1R=$(awk '$1=="A1-on"{print $2","$3}' "$D/logs/idx.txt")
ADIRS=""; for a in $ALSO; do ADIRS="$ADIRS --adapter-dir $a"; done
python3 "$R/structure_check_r529.py" --adapter-dir "$D/adapter" $ADIRS \
  --range "A0-off=$A0R" --range "A1-on=$A1R" --treatment A1-on \
  --out "$D/logs/prefix-check.json" > "$D/logs/prefix-check.txt" 2>&1
mrc=$?; cat "$D/logs/prefix-check.txt"
log "前缀机检 rc=$mrc (0=M1..M5 全过; 非 0 ⇒ 本轮不得宣称任何降幅) [range A0=$A0R A1=$A1R also=$ALSO]"

# --- 6 冻结 (判分只吃仓内不可变快照) + 分列 KPI ------------------------------
python3 "$R/freeze_r529.py" --run-dir "$D" --window "$WIN" --adapter-dir "$D/adapter" \
  --map A0-off=agentA0-off --map A1-on=agentA1-on --map C-codex=codex --write > "$D/logs/freeze.txt" 2>&1
frc=$?; grep -E "^冻结|^WROTE" "$D/logs/freeze.txt" | head -8; log "冻结/汇总 rc=$frc"
python3 "$R/kpi_r529.py" --report "$R/evidence/windows/$WIN/report.json" --prereg "$R/prereg-r529.json" \
  --out "$D/logs/kpi-r529.json" > "$D/logs/kpi.txt" 2>&1
krc=$?; cat "$D/logs/kpi.txt"
log "KPI 分列判据 rc=$krc"

# --- 7 铁律 11 收口器 (含 unreliable 策略, 策略由 prereg 声明) ---------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r529 > "$D/logs/precond.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$D/logs/precond.txt"
tail -16 "$D/logs/precond.txt"
log "PRECOND_RC=$prc (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 8 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R529 收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "arms: A0-off(纪律关/基线) / A1-on(处理) / C-codex(外部真值) —— 三臂各跑 g1(F1 锚58) + t1(F2 新族30)"
  echo "prefix_rc=$mrc kpi_rc=$krc precond_rc=$prc"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  sha256sum "$TASKSET" "$R/prereg-r529.json" "$R/cases/run_cases_r529.py" "$R/cases/cases-r521.json" "$REPO/eval/rover/r519/grade_r519.py"; } \
  > "$D/SUMMARY-$WIN.txt" 2>&1
cp -f "$D/SUMMARY-$WIN.txt" "$R/evidence/SUMMARY-r529-$WIN.txt" 2>/dev/null
log "完成: $D"
exit 0
