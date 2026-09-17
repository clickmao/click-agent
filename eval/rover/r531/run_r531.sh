#!/usr/bin/env bash
# R531 主轮: **第三题族(数学) + 合批轴(第7条纪律) 同窗对照 + 预注册窗声明面机读化 + 真值侧伪影假设机检证伪**。
#
# 与 R529 主轮的差别:
#  ① 题集三题: g1 = F1 锚 (58 隐藏用例, 题面逐字节复用) / t1 = F2 (toolkit 多文件包, 30) /
#     m1 = F3 新族 (mathkit 数学 5 算子 4 模块, 30 隐藏用例)
#  ② 四臂: A0-off(纪律关) / A1-on(纪律开, 合批关) / A2-merge(合批开) / C-codex(外部真值)
#     ⇒ 单变量轴 = AGENTFRAMEWORK_ACTION_MERGE; A2-merge vs A1-on 为合批轴对照
#  ③ **步骤 0.5 预注册声明面硬闸** (本轮新器): prereg_scope_gate v2 读 prereg.window_plan.windows[]
#     机读窗计划; 缺机读窗 ⇒ rc=3 fail-closed ⇒ 不起臂
#  ④ 同输入硬门钉三题 (F1 钉 sha 常量; F2 钉 R529 题集同值; F3 自述 sha 自洽)
# 铁律: 禁 push; 四臂串行 (2 vCPU/3.57 GiB); 链代码已改 ⇒ 本轮 AOT 为 /tmp/pub_r531 (IL 警告 0)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r531
PORT=${R531_ADAPTER_PORT:-48999}
DS=${R531_DS:-$(date +%m%d-%H%M%S)}
D=${R531_RUN_DIR:-$R/run-$DS}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R531_AGENT_BIN:-/tmp/pub_r531/agenthost}
CODEX_BIN=${R531_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
WIN=${R531_WINDOW:-w1}
TMO=${R531_TIMEOUT:-2400}
TASKSET=$R/taskset-r531.json
PIN_F1=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
TASKS="g1,t1,m1"
ALSO=${R531_ALSO:-}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) --------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$R/prereg-r531.json" ] || { echo "[致命] 缺预注册 (验收面/策略须先写再跑)"; exit 3; }
[ -f "$TASKSET" ] || { echo "[致命] 缺题集 $TASKSET"; exit 3; }
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent"
cp -r "$CFGSRC" "$D/agent/cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN ts=$(date -Is)" > "$D/.owner-r531"
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"      # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
cd "$REPO" || exit 3

# --- 0.5 预注册声明面硬闸 (R531 新器): 窗计划必须机读, 否则 fail-closed -------------
python3 "$REPO/eval/rover/r507pre/prereg_scope_gate.py" --prereg "$R/prereg-r531.json" \
  --out "$D/logs/scope-gate.json" > "$D/logs/scope-gate.txt" 2>&1
grc=$?
cat "$D/logs/scope-gate.txt"
[ "$grc" -eq 0 ] || { log "[致命] 预注册窗声明面闸 rc=$grc ⇒ 不起臂 (fail-closed)"; exit 3; }
log "预注册窗声明面闸 PASS (windows 源=prereg.window_plan.windows)"

# --- 1 同输入硬门 (三题) ---------------------------------------------------
python3 - "$TASKSET" "$PIN_F1" "$REPO/eval/rover/r529/taskset-r529.json" > "$D/logs/input-pins.txt" 2>&1 <<'PY'
import hashlib, io, json, sys
ts, pin_f1, ts529 = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(io.open(ts, encoding="utf-8"))
old = {t["tid"]: t for t in json.load(io.open(ts529, encoding="utf-8"))["tasks"]}
ok = True
for t in d["tasks"]:
    p = t.get("prompt") or ""
    h = hashlib.sha256(p.encode()).hexdigest()
    decl = t.get("prompt_sha256")
    same = (h == decl)
    tid = t["tid"]
    if tid == "g1":
        anchor = (h == pin_f1)
        tag = "F1 钉锚常量"
    elif tid == "t1":
        anchor = (h == old["t1"]["prompt_sha256"])
        tag = "F2 钉 R529 题集同值(同输入)"
    else:
        anchor = same
        tag = "F3 自述 sha 自洽"
    print("tid=%s family=%s prompt_sha256=%s declared=%s self_consistent=%s anchor_ok=%s (%s) cases=%s" %
          (tid, t.get("family"), h[:16], (decl or "")[:16], same, anchor, tag, t.get("hidden_cases")))
    ok = ok and same and anchor
print("INPUT_PINS_OK=%s" % ok)
sys.exit(0 if ok else 3)
PY
prc=$?; cat "$D/logs/input-pins.txt"
[ "$prc" -eq 0 ] || { log "[致命] 同输入硬门失败 rc=$prc ⇒ 停手"; exit 3; }
log "同输入硬门 PASS (三题: F1 钉锚 + F2 钉 R529 同值 + F3 自洽)"

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R531 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
    --taskset "$TASKSET" --tasks "$TASKS" --timeout "$TMO" > "$D/logs/run-$1.txt" 2>&1
  local rc=$?
  i1=$(maxidx)
  log "臂 $1 rc=$rc adapter_range=[$((i0+1)),$i1] ($(tail -1 "$D/logs/run-$1.txt" 2>/dev/null))"
  local empty=0
  for tid in g1 t1 m1; do
    if [ -z "$(find "$2/$tid/work" -type f -print -quit 2>/dev/null)" ]; then
      log "[警告] 臂 $1/$tid 产物树为空 (工具面/落盘失效) ⇒ 该臂-题按 fail-closed 记账, 不得当绿"
      empty=$((empty+1))
    fi
  done
  echo "$1 $((i0+1)) $i1 $empty" >> "$D/logs/idx.txt"
}

# --- 4 四臂串行 (基线在前, 避免开窗冷启偏差记到处理臂) ----------------------
run_arm A0-off  "$D/A0-off"  "AGENTFRAMEWORK_ACTION_DISCIPLINE=off"
run_arm A1-on   "$D/A1-on"   ""
run_arm A2-merge "$D/A2-merge" "AGENTFRAMEWORK_ACTION_MERGE=on"
C0=$(ls "$D/adapter" 2>/dev/null | grep -c '^side-codex-' || true)
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-codex --out "$D/C-codex" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
  --taskset "$TASKSET" --tasks "$TASKS" --timeout "$TMO" > "$D/logs/run-C-codex.txt" 2>&1
crc=$?
C1=$(ls "$D/adapter" 2>/dev/null | grep -c '^side-codex-' || true)
echo "C-codex $((C0+1)) $C1 0" >> "$D/logs/idx.txt"
log "臂 C-codex rc=$crc adapter_range=[$((C0+1)),$C1] ($(tail -1 "$D/logs/run-C-codex.txt" 2>/dev/null))"

# --- 5 前缀稳定性机检 (常量 system + 首调用命中 + 步间涨幅 + 回执) ----------
A0R=$(awk '$1=="A0-off"{print $2","$3}' "$D/logs/idx.txt")
A1R=$(awk '$1=="A1-on"{print $2","$3}' "$D/logs/idx.txt")
A2R=$(awk '$1=="A2-merge"{print $2","$3}' "$D/logs/idx.txt")
ADIRS=""; for a in $ALSO; do ADIRS="$ADIRS --adapter-dir $a"; done
python3 "$R/structure_check_r531.py" --adapter-dir "$D/adapter" $ADIRS \
  --range "A0-off=$A0R" --range "A1-on=$A1R" --range "A2-merge=$A2R" --treatment A2-merge \
  --out "$D/logs/prefix-check.json" > "$D/logs/prefix-check.txt" 2>&1
mrc=$?; cat "$D/logs/prefix-check.txt"
log "前缀机检 rc=$mrc (0=M1..M5 全过; 非 0 ⇒ 本轮不得宣称任何降幅)"

# --- 6 冻结 (判分只吃仓内不可变快照) + 分列 KPI ------------------------------
python3 "$R/freeze_r531.py" --run-dir "$D" --window "$WIN" --adapter-dir "$D/adapter" \
  --map A0-off=agentA0-off --map A1-on=agentA1-on --map A2-merge=agentA2-merge --map C-codex=codex \
  --write > "$D/logs/freeze.txt" 2>&1
frc=$?; grep -E "^冻结|^WROTE" "$D/logs/freeze.txt" | head -8; log "冻结/汇总 rc=$frc"
python3 "$R/kpi_r531.py" --report "$R/evidence/windows/$WIN/report.json" --prereg "$R/prereg-r531.json" \
  --out "$D/logs/kpi-r531.json" > "$D/logs/kpi.txt" 2>&1
krc=$?; cat "$D/logs/kpi.txt"
log "KPI 分列判据 rc=$krc"

# --- 7 铁律 11 收口器 (含 unreliable 策略, 策略由 prereg 声明) ---------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r531 > "$D/logs/precond.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$D/logs/precond.txt"
tail -16 "$D/logs/precond.txt"
log "PRECOND_RC=$prc (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 8 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R531 收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "arms: A0-off(纪律关) / A1-on(纪律开) / A2-merge(合批开) / C-codex(外部真值) —— 各跑 g1(F1 58) + t1(F2 30) + m1(F3 数学 30)"
  echo "scope_gate_rc=$grc prefix_rc=$mrc freeze_rc=$frc kpi_rc=$krc precond_rc=$prc"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  sha256sum "$TASKSET" "$R/prereg-r531.json" \
    "$R/cases/run_cases_r521.py" "$R/cases/run_cases_r529.py" "$R/cases/run_cases_r531_math.py" \
    "$R/cases/cases-r521.json" "$R/cases/cases-r529-f2.json" "$R/cases/cases-r531-f3.json"; } \
  > "$D/SUMMARY-$WIN.txt" 2>&1
cp -f "$D/SUMMARY-$WIN.txt" "$R/evidence/SUMMARY-r531-$WIN.txt" 2>/dev/null
log "完成: $D"
exit 0
