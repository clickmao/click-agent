#!/usr/bin/env bash
# R516 真机 E2E: 「节点成功必须绑产物证据」—— 前态(旧AOT) / 新 AOT 三臂 / 负控 (起臂前拒收)
#
#   RED : 旧 AOT (R515)         plan-red.txt  (零产物节点)                     ⇒ 期望 Completed/空 (假绿前态)
#   G1  : 新 AOT + --scope      plan-red.txt  + scope-red.txt                  ⇒ 期望 rc=1, Failed(no_artifact)
#   G2  : 新 AOT + --scope      plan-write.txt + scope-write.txt               ⇒ 期望 rc=0, Completed + A out/hello.py (不误杀)
#   G3  : 新 AOT + --scope      plan-outside.txt + scope-write.txt             ⇒ 期望 rc=1, Failed(out_of_scope)
#   N   : 新 AOT + --scope      plan-overlap.txt + scope-overlap.txt           ⇒ 期望 rc=2 且 adapter 零新增调用
#
# 纪律: 起手闸连续 2 PASS 才起臂; 每臂独立会话 (R509); adapter 起手后沉降 5 s; 判分只读落盘 (check_r516.py)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r516
PORT=${R516_ADAPTER_PORT:-48700}
TS=${R516_TS:-$(date +%m%d-%H%M%S)}
D=${R516_RUN_DIR:-/tmp/r516/run-$TS}
BIN=${R516_AGENT_BIN:-/tmp/pub_r516/agenthost}
OLDBIN=${R516_OLD_BIN:-/tmp/pub_r515/agenthost}
CFGSRC=${R516_CFG_SEED:-/tmp/r455_env/agent/cfg}
log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- 0 守卫 ---------------------------------------------------------------
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺本侧新 AOT $BIN"; exit 3; }
[ -x "$OLDBIN" ] || { log "[致命] 缺前态 AOT $OLDBIN"; exit 3; }
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 被占用"; exit 4; fi
mkdir -p "$D"/{adapter,logs} "$D/agent" "$D/red/ws" "$D/g1/ws" "$D/g2/ws" "$D/g3/ws" "$D/n/ws"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态守卫失败 (疑似嵌套)"; exit 3; }
echo "run=$D port=$PORT bin=$BIN oldbin=$OLDBIN ts=$(date -Is)" > "$D/.owner-r516"

# 夹具指纹 (同窗可比性: 两臂同一计划文件 ⇒ 逐字节同输入)
python3 - "$D/evidence-fixture.json" "$R" "$D" <<'PY'
import hashlib, json, os, sys
def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
R, D = sys.argv[2], sys.argv[3]
out = {}
for k in ("plan-red.txt", "plan-write.txt", "plan-outside.txt", "plan-overlap.txt",
          "scope-red.txt", "scope-write.txt", "scope-overlap.txt"):
    try:
        out[k + "_sha12"] = sha(os.path.join(R, k))
    except OSError:
        out[k + "_sha12"] = None
for k, p in (("bin_new", os.environ.get("R516_AGENT_BIN", "/tmp/pub_r516/agenthost")),
             ("bin_old", os.environ.get("R516_OLD_BIN", "/tmp/pub_r515/agenthost"))):
    try:
        out[k + "_sha12"] = sha(p)
    except OSError:
        out[k + "_sha12"] = None
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
PY

# --- 1 起手闸: 连续 2 次 PASS --------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R516 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2 adapter (起手后沉降) ----------------------------------------------
set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" \
  > "$D/logs/adapter.txt" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do
  curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5
done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
log "adapter up pid=$APID port=$PORT"; sleep 5

maxidx() { python3 - "$D/adapter" <<'PY'
import os, re, sys
d = sys.argv[1]; m = 0
try:
    for fn in os.listdir(d):
        r = re.match(r"^side-[A-Za-z0-9_]+-(\d+)\.json$", fn)
        if r: m = max(m, int(r.group(1)))
except OSError: pass
print(m)
PY
}

export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
export AGENTFRAMEWORK_PY_RUN=1

run_arm() {   # $1=臂名 $2=二进制 $3=计划 $4=node-steps $5=scope(可空)
  local arm=$1 bin=$2 plan=$3 steps=$4 scope=$5
  local ws="$D/$arm/ws"; local sess="r516-$arm-$TS"
  maxidx > "$D/$arm/idx-before.txt"
  echo "IDX=$(cat "$D/$arm/idx-before.txt")" > "$D/$arm/idx-before.rc"
  local extra=()
  [ -n "$scope" ] && extra=(--scope "$scope")
  AGENTFRAMEWORK_WORKSPACE="$ws" AGENTFRAMEWORK_ACTION_AUDIT="$D/$arm/audit" \
  timeout 900 "$bin" --orchestrate "$plan" --node-steps "$steps" "${extra[@]}" \
    --workspace "$ws" --report "$D/$arm/report.json" --session "$sess" \
    > "$D/$arm/stdout.txt" 2> "$D/$arm/stderr.txt"
  echo "${arm}_RC=$?" | tee "$D/logs/$arm.txt"
  maxidx > "$D/$arm/idx-after.txt"
  echo "IDX=$(cat "$D/$arm/idx-after.txt")" > "$D/$arm/idx-after.rc"
  sleep 3
}

# --- 3 臂 RED (前态: 旧 AOT, 零产物节点) ---------------------------------
log "== 臂 RED (旧 AOT, 零产物节点, 1 步) =="
run_arm red "$OLDBIN" "$R/plan-red.txt" 1 ""

# --- 4 臂 G1 (新 AOT + scope, 同计划) ------------------------------------
log "== 臂 G1 (新 AOT + scope, 零产物 ⇒ 期望 Failed) =="
run_arm g1 "$BIN" "$R/plan-red.txt" 1 "$R/scope-red.txt"

# --- 5 臂 G2 (真干活, 不误杀) -------------------------------------------
log "== 臂 G2 (新 AOT + scope, 写 out/hello.py ⇒ 期望 Completed) =="
run_arm g2 "$BIN" "$R/plan-write.txt" 3 "$R/scope-write.txt"

# --- 6 臂 G3 (越界写) ---------------------------------------------------
log "== 臂 G3 (新 AOT + scope, 写 outside/rogue.py ⇒ 期望 Failed) =="
run_arm g3 "$BIN" "$R/plan-outside.txt" 3 "$R/scope-write.txt"

# --- 7 臂 N (负控: 同层重叠 ⇒ 起臂前拒收) -------------------------------
log "== 臂 N (负控, 同层重叠 scope ⇒ 期望 rc=2 且零 adapter 调用) =="
BEFORE_N=$(maxidx); echo "IDX=$BEFORE_N" > "$D/n/idx-before.rc"; echo "$BEFORE_N" > "$D/n/idx-before.txt"
AGENTFRAMEWORK_WORKSPACE="$D/n/ws" "$BIN" --orchestrate "$R/plan-overlap.txt" --node-steps 1 \
  --scope "$R/scope-overlap.txt" --workspace "$D/n/ws" --report "$D/n/report.json" --session "r516-n-$TS" \
  > "$D/n/stdout.txt" 2> "$D/n/stderr.txt"
echo "N_RC=$?" | tee "$D/logs/n.txt"
AFTER_N=$(maxidx); echo "$AFTER_N" > "$D/n/idx-after.txt"; echo "IDX=$AFTER_N" > "$D/n/idx-after.rc"

# --- 8 判定 --------------------------------------------------------------
python3 "$R/check_r516.py" --run-dir "$D" --json "$D/verdict.json" 2>&1 | tee "$D/logs/verdict.txt"
VRC=${PIPESTATUS[0]}

# --- 9 teardown ----------------------------------------------------------
kill "$APID" 2>/dev/null
sleep 2
pkill -f "adapter_tools.py $PORT" 2>/dev/null
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[告警] 端口 $PORT 未释放"; else log "端口已释放"; fi
# 夹具收口: 残留子进程按命名空间扫 (pkill -P 会漏杀孙子进程)
pgrep -af "r516|$PORT" | grep -v "$$" | head -5 || true
log "VERDICT_RC=$VRC DONE RUN_DIR=$D"
exit "$VRC"
