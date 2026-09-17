#!/usr/bin/env bash
# R524 主轮: **prompt 前缀纪律** —— 用户 2026-09-17 定向 (「你往中间塞东西了？」/「上下文几乎不涨才是对的」)。
# 改动 (链代码, 非机制轮): ① 工作区文件召回不再算「会话静态」⇒ 只进本轮 user 追加区, system 段跨运行逐字节常量;
#   ② 自指遥测路径闸 (data/activity、*.jsonl、/telemetry/) 不得被自动召回; ③ 单工具回灌缺省压到 600 字符 (硬顶 8192 可调);
#   ④ 纪律补「零过渡叙述 / 回执按需取全文」。臂: A0-off(纪律关, 同二进制对照) / A1-on(处理) / C-codex(外部真值参照)。
# 轮内硬门: ① 题面 sha256 钉 ② 前缀稳定性机检 (常量 system + 首调用命中 + 步间涨幅 + 回执) ③ 空产物 fail-closed
#           ④ 铁律 11 前置器收口 (rc!=0 ⇒ 一律标「参考(未可验收)」)。铁律: 禁 push; 三臂串行 (2 vCPU/3.57 GiB)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r524
PORT=${R524_ADAPTER_PORT:-48796}
DS=${R524_DS:-$(date +%m%d-%H%M%S)}
D=${R524_RUN_DIR:-$R/run-$DS}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R524_AGENT_BIN:-/tmp/pub_r524/agenthost}
CODEX_BIN=${R524_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
WIN=${R524_WINDOW:-w1}
TMO=${R524_TIMEOUT:-2400}
TASKSET=$R/taskset-r524.json
PIN_PROMPT=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
ALSO=${R524_ALSO:-}
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/run.txt"; }

# --- 0 守卫 (fail-closed) --------------------------------------------------
[ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
ss -ltn 2>/dev/null | grep -q ":$PORT " && { echo "[致命] 端口 $PORT 被占用"; exit 4; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$R/prereg-r524.json" ] || { echo "[致命] 缺预注册 (验收面须先写再跑)"; exit 3; }
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent"
cp -r "$CFGSRC" "$D/agent/cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT bin=$AGENT_BIN ts=$(date -Is)" > "$D/.owner-r524"
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"      # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
export AGENTFRAMEWORK_PY_RUN=1
export ADAPTER_DUMP_FULL=1
cd "$REPO" || exit 3

# --- 1 同输入硬门 ----------------------------------------------------------
python3 - "$TASKSET" "$PIN_PROMPT" > "$D/logs/input-pins.txt" 2>&1 <<'PY'
import hashlib, io, json, sys
ts, pin = sys.argv[1], sys.argv[2]
d = json.load(io.open(ts, encoding="utf-8"))
t = d["tasks"][0] if isinstance(d.get("tasks"), list) else d
p = t.get("prompt") or ""
h = hashlib.sha256(p.encode()).hexdigest()
cases = t.get("hidden_cases")
cases = len(cases) if isinstance(cases, list) else (int(cases) if isinstance(cases, int) else 0)
print("taskset=%s" % ts)
print("prompt_sha256=%s pin=%s same=%s" % (h, pin, h == pin))
print("cases_total=%d" % cases)
sys.exit(0 if h == pin else 3)
PY
prc=$?; cat "$D/logs/input-pins.txt"
[ "$prc" -eq 0 ] || { log "[致命] 题面 sha256 与预注册钉不同 rc=$prc ⇒ 非同输入, 停手"; exit 3; }
log "同输入硬门 PASS"

# --- 2 起手闸: 连续 2 次 PASS ---------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R524 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
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
    --taskset "$TASKSET" --tasks g1 --timeout "$TMO" > "$D/logs/run-$1.txt" 2>&1
  local rc=$?
  i1=$(maxidx)
  log "臂 $1 rc=$rc adapter_range=[$((i0+1)),$i1] ($(tail -1 "$D/logs/run-$1.txt" 2>/dev/null))"
  if [ -z "$(find "$2" -path '*/work/*' -type f -print -quit 2>/dev/null)" ]; then
    log "[致命] 臂 $1 产物树为空 (工具面/落盘失效) ⇒ 该臂按 fail-closed 记账, 不得当绿"
  fi
  echo "$1 $((i0+1)) $i1" >> "$D/logs/idx.txt"
}

# --- 4 三臂串行 (基线在前, 避免开窗冷启偏差记到处理臂) ----------------------
run_arm A0-off "$D/A0-off" "AGENTFRAMEWORK_ACTION_DISCIPLINE=off"
run_arm A1-on  "$D/A1-on"  ""
python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-codex --out "$D/C-codex" \
  --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
  --taskset "$TASKSET" --tasks g1 --timeout "$TMO" > "$D/logs/run-C-codex.txt" 2>&1
log "臂 C-codex rc=$? ($(tail -1 "$D/logs/run-C-codex.txt" 2>/dev/null))"

# --- 5 前缀稳定性机检 (常量 system + 首调用命中 + 步间涨幅 + 回执) ----------
A0R=$(awk '$1=="A0-off"{print $2","$3}' "$D/logs/idx.txt")
A1R=$(awk '$1=="A1-on"{print $2","$3}' "$D/logs/idx.txt")
ADIRS=""; for a in $ALSO; do ADIRS="$ADIRS --adapter-dir $a"; done
python3 "$R/prefix_check_r524.py" --adapter-dir "$D/adapter" $ADIRS \
  --range "A0-off=$A0R" --range "A1-on=$A1R" --treatment A1-on \
  --out "$D/logs/prefix-check.json" > "$D/logs/prefix-check.txt" 2>&1
mrc=$?; cat "$D/logs/prefix-check.txt"
log "前缀机检 rc=$mrc (0=M1..M5 全过; 非 0 ⇒ 本轮不得宣称任何降幅) [range A0=$A0R A1=$A1R also=$ALSO]"

# --- 6 冻结 (判分只吃仓内不可变快照) + 分列 KPI ------------------------------
python3 "$R/freeze_r524.py" --run-dir "$D" --window "$WIN" --adapter-dir "$D/adapter" \
  --map A0-off=agentA0 --map A1-on=agentA1 --map C-codex=codex --write > "$D/logs/freeze.txt" 2>&1
frc=$?; grep -E "^冻结" "$D/logs/freeze.txt" | head -4; log "冻结/汇总 rc=$frc"
python3 "$R/kpi_r524.py" --report "$R/evidence/windows/$WIN/report.json" --prereg "$R/prereg-r524.json" \
  --out "$D/logs/kpi-r524.json" > "$D/logs/kpi.txt" 2>&1
krc=$?; cat "$D/logs/kpi.txt"
log "KPI 分列判据 rc=$krc"

# --- 7 铁律 11 收口器 ------------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r524 > "$D/logs/precond.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$D/logs/precond.txt"
tail -12 "$D/logs/precond.txt"
log "PRECOND_RC=$prc (0=可验收 / 1=未可验收 / 3=输入缺失)"

# --- 8 收口 ---------------------------------------------------------------
kill "$APID" 2>/dev/null; sleep 1
for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口已释放"
{ echo "R524 收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN"
  echo "arms: A0-off(纪律关) / A1-on(处理: 前缀纪律+回执压缩) / C-codex(外部真值参照)"
  echo "prefix_rc=$mrc kpi_rc=$krc precond_rc=$prc"
  echo "idx: $(cat "$D/logs/idx.txt" 2>/dev/null | tr '\n' ' ')"
  sha256sum "$TASKSET" "$R/prereg-r524.json" "$REPO/eval/rover/r519/grade_r519.py"; } \
  > "$D/SUMMARY-$WIN.txt" 2>&1
cp -f "$D/SUMMARY-$WIN.txt" "$R/evidence/SUMMARY-r524-$WIN.txt" 2>/dev/null
log "完成: $D"
exit 0
