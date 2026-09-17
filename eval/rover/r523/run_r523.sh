#!/usr/bin/env bash
# R523 主轮: n=3 同窗对照 (reps>=3) —— 每窗三臂 A0-off(纪律关,消融控制) / A1-on(纪律开,交付面) / C-codex(外部真值)。
# 目的: ① (主线 R413 判据) 给出**可验收**的 n=3 读数 (调用数/新算 prompt/completion/质量), 逐窗 + 中位数 + 极差
#       ② (R522 §7 候选①) 检验「19→4 调用」是窗口方差还是纪律作用 (A1 vs A0 各 3 窗)
# 硬门: ① 题面 sha256 == 预注册钉 (逐字节同输入) ② 起手闸 ×2 PASS ③ 产物树非空 fail-closed
#       ④ 挂载机检 (纪律真进实发 prompt) ⑤ 铁律 11 前置器收口 (rc!=0 ⇒ 降幅一律标「参考(未可验收)」)
# 铁律: 禁 push; 2 vCPU/3.57 GiB ⇒ 三窗**串行**, 每窗独立 adapter 端口; 每跑次独立 session。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r523
R522=$REPO/eval/rover/r522
DS=${R523_DS:-$(date +%m%d-%H%M%S)}
CFGSRC=/tmp/r455_env/agent/cfg
AGENT_BIN=${R523_AGENT_BIN:-/tmp/pub_r522/agenthost}
AGENT_SHA_PIN=${R523_AGENT_SHA:-cc611646e76a5810604f5a8ce44bf85dd4456f3fd436c93fa2331c9bd28580e7}
CODEX_BIN=${R523_CODEX_BIN:-$HOME/.agentframework/tools/codex-env/node_modules/.bin/codex}
TMO=${R523_TIMEOUT:-2400}
TASKSET=$R/taskset-r523.json
PIN_PROMPT=516f3208963c6e66fac1d2da516b9116f1409080bfd25cf50c61480d5ef3aca3
WINDOWS=${R523_WINDOWS:-"w1 w2 w3"}
declare -A PORTOF=([w1]=48700 [w2]=48701 [w3]=48702)

# --- 0 全局守卫 (fail-closed) ----------------------------------------------
[ -d "$CFGSRC" ] || { echo "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { echo "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
sha256sum -c <<<"$AGENT_SHA_PIN  $AGENT_BIN" >/dev/null || { echo "[致命] 二进制 sha256 与预注册钉不符 ⇒ 非同二进制, 停手"; exit 3; }
[ -x "$CODEX_BIN" ] || { echo "[致命] 缺 codex $CODEX_BIN"; exit 3; }
[ -f "$REPO/.env.local" ] || { echo "[致命] 缺 .env.local"; exit 3; }
[ -f "$R/prereg-r523.json" ] || { echo "[致命] 缺预注册 (验收面须先写再跑)"; exit 3; }
for w in $WINDOWS; do
  D=$R/run-$DS-$w
  [ -e "$D" ] && { echo "[致命] $D 已存在(禁覆盖)"; exit 4; }
  ss -ltn 2>/dev/null | grep -q ":${PORTOF[$w]} " && { echo "[致命] 端口 ${PORTOF[$w]} 被占用"; exit 4; }
done
echo "R523 起手 $(date -Is) DS=$DS windows='$WINDOWS' bin=$AGENT_BIN"

# --- 1 同输入硬门 (题面逐字节同源, 禁漂移) ---------------------------------
python3 - "$TASKSET" "$PIN_PROMPT" <<'PY' || exit 3
import hashlib, io, json, sys
ts, pin = sys.argv[1], sys.argv[2]
d = json.load(io.open(ts, encoding="utf-8"))
t = d["tasks"][0] if isinstance(d.get("tasks"), list) else d
h = hashlib.sha256(t["prompt"].encode()).hexdigest()
print("taskset=%s\nprompt_sha256=%s\npin=%s\nsame=%s\ncases_total=%s"
      % (ts, h, pin, h == pin, t.get("hidden_cases")))
sys.exit(0 if h == pin else 3)
PY
echo "[同输入硬门] PASS (题面 sha256 == pin)"

# --- 2 端口/配置准备 --------------------------------------------------------
set -a; . "$REPO/.env.local"; set +a

run_window(){  # $1=win
  local WIN=$1 PORT=${PORTOF[$1]} D=$R/run-$DS-$1 APID mrc frc krc
  mkdir -p "$D"/{adapter,evidence,logs} "$D/agent"
  cp -r "$CFGSRC" "$D/agent/cfg" || { echo "[致命] cfg 拷贝失败"; exit 3; }
  grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
  grep -rq "$PORT" "$D/agent/cfg" || { echo "[致命] cfg 端口未替换"; exit 3; }
  [ -f "$D/agent/cfg/base/models.yaml" ] || { echo "[致命] cfg 形态守卫失败"; exit 3; }
  echo "win=$WIN run=$D port=$PORT bin=$AGENT_BIN ts=$(date -Is)" > "$D/.owner-r523"
  export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"   # 缺此项 ⇒ 请求绕过计量 adapter = 无读数
  export AGENTFRAMEWORK_PY_RUN=1
  export ADAPTER_DUMP_FULL=1                    # 挂载机检要读实发正文
  cd "$REPO" || exit 3
  log(){ echo "[$(date +%H:%M:%S)][$WIN] $*" | tee -a "$D/logs/run.txt"; }

  # 起手闸: 连续 2 次 PASS
  local i v
  for i in 1 2; do
    python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R523 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
    v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
    log "起手闸 $i: $v"
    [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 本窗不起臂"; return 2; }
  done

  DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
    > "$D/logs/adapter.log" 2>&1 &
  APID=$!
  local ok=0
  for i in $(seq 1 40); do
    curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
  done
  [ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; return 3; }
  sleep 3
  log "adapter 就绪 (pid=$APID port=$PORT)"

  maxidx(){ ls "$D/adapter" 2>/dev/null | grep -c '^side-agent-' || true; }
  run_arm(){  # $1=run名 $2=out目录 $3=附加env
    local i0 i1 rc
    i0=$(maxidx)
    env $3 python3 "$REPO/eval/rover/r511/proj_run_side.py" --side agent --arm "$1" --out "$2" \
      --adapter-dir "$D/adapter" --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --max-steps 32 \
      --taskset "$TASKSET" --tasks g1 --timeout "$TMO" > "$D/logs/run-$1.txt" 2>&1
    rc=$?
    i1=$(maxidx)
    log "臂 $1 rc=$rc adapter_range=[$((i0+1)),$i1] ($(tail -1 "$D/logs/run-$1.txt" 2>/dev/null))"
    if [ -z "$(find "$2" -path '*/work/*' -type f -print -quit 2>/dev/null)" ]; then
      log "[致命] 臂 $1 产物树为空 (工具面/落盘失效) ⇒ 按 fail-closed 记账, 不得当绿"
    fi
    echo "$1 $((i0+1)) $i1" >> "$D/logs/idx.txt"
  }

  run_arm A0-off "$D/A0-off" "AGENTFRAMEWORK_ACTION_DISCIPLINE=off"
  run_arm A1-on  "$D/A1-on"  ""
  python3 "$REPO/eval/rover/r511/proj_run_side.py" --side codex --arm C-codex --out "$D/C-codex" \
    --adapter-dir "$D/adapter" --adapter-port "$PORT" --codex-bin "$CODEX_BIN" \
    --taskset "$TASKSET" --tasks g1 --timeout "$TMO" > "$D/logs/run-C-codex.txt" 2>&1
  log "臂 C-codex rc=$? ($(tail -1 "$D/logs/run-C-codex.txt" 2>/dev/null))"

  python3 "$R522/mount_check_r522.py" --adapter-dir "$D/adapter" \
    --arm "A0-off=$(awk '$1=="A0-off"{print $2","$3}' "$D/logs/idx.txt")" \
    --arm "A1-on=$(awk '$1=="A1-on"{print $2","$3}' "$D/logs/idx.txt")" \
    --out "$D/logs/mount-check.json" > "$D/logs/mount-check.txt" 2>&1
  mrc=$?; tail -3 "$D/logs/mount-check.txt"
  log "挂载机检 rc=$mrc (0=纪律确已生效)"

  python3 "$R/freeze_r523.py" --run-dir "$D" --window "$WIN" --adapter-dir "$D/adapter" \
    --map A0-off=agentA0-off --map A1-on=agentA1-on --map C-codex=codex --write > "$D/logs/freeze.txt" 2>&1
  frc=$?; grep -E "^冻结" "$D/logs/freeze.txt" | head -4; log "冻结/判分 rc=$frc"

  kill "$APID" 2>/dev/null; sleep 1
  for p in $(pgrep -f "adapter_tools.py $PORT" 2>/dev/null); do kill "$p" 2>/dev/null; done
  sleep 1
  ss -ltn 2>/dev/null | grep -q ":$PORT " && log "[警告] 端口 $PORT 未释放" || log "端口 $PORT 已释放"
  { echo "R523 窗口 $WIN 收口 $(date -Is)"; echo "run=$D"; echo "agent_bin=$AGENT_BIN"; sha256sum "$AGENT_BIN";
    echo "arms: A0-off/A1-on/C-codex"; echo "mount_rc=$mrc freeze_rc=$frc"; } > "$D/SUMMARY-$WIN.txt" 2>&1
  return 0
}

RC_ALL=0
for w in $WINDOWS; do
  run_window "$w" || { echo "[致命] 窗口 $w 未完成 rc=$? ⇒ 后续窗口停手"; RC_ALL=3; break; }
done

# --- 3 汇总: KPI (n=3) -----------------------------------------------------
cd "$REPO" || exit 3
python3 "$R/kpi_r523.py" --out "$R/evidence/kpi-r523.json" > "$R/evidence/kpi-r523.txt" 2>&1
krc=$?
cat "$R/evidence/kpi-r523.txt"
echo "[KPI] rc=$krc (主判据 = C3 调用数下降 ∧ C2 质量不降)"

# --- 4 铁律 11 收口器 ------------------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round r523 > "$R/evidence/precond-r523.txt" 2>&1
prc=$?
echo "PRECOND_RC=$prc" >> "$R/evidence/precond-r523.txt"
tail -14 "$R/evidence/precond-r523.txt"
echo "[PRECOND] rc=$prc (0=可验收 / 1=未可验收 / 3=输入缺失)"

{ echo "R523 收口 $(date -Is)"; echo "DS=$DS windows='$WINDOWS'";
  echo "kpi_rc=$krc precond_rc=$prc"; sha256sum "$TASKSET" "$R/prereg-r523.json"; } \
  > "$R/evidence/SUMMARY-r523.txt" 2>&1
echo "R523 完成 rc_all=$RC_ALL"
exit 0
