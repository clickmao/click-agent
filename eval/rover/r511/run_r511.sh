#!/usr/bin/env bash
# R511 规模探界跑器: 同环境·同输入·同模型; 两臂 = 默认预算(6) vs 显式 12 步; 每跑次独立会话 (R509 铁律)。
# 起手: 连续 2 次 PASS 才起臂; 单变量 (仅 AGENTFRAMEWORK_ACTION_MAX_STEPS 不同); 判分只吃产物真实行为。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r511
PORT=${R511_ADAPTER_PORT:-48680}
TS=${R511_TS:-$(date +%m%d-%H%M%S)}
D=${R511_RUN_DIR:-/tmp/r511/run-$TS}
AGENT_BIN=${R511_AGENT_BIN:-/tmp/pub_r510/agenthost/agenthost}
CFGSRC=${R511_CFG_SEED:-/tmp/r455_env/agent/cfg}
TASKS=${R511_TASKS:-p3,p4}
REPS=${R511_REPS:-2}
S12=${R511_MAXSTEP_S12:-12}
log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- 0 守卫 ---------------------------------------------------------------
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$AGENT_BIN" ] || { log "[致命] 缺本侧 AOT $AGENT_BIN"; exit 3; }
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 被占用"; exit 4; fi
mkdir -p "$D"/{adapter,evidence,logs} "$D/agent"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
grep -rq "$PORT" "$D/agent/cfg" || { log "[致命] cfg 端口未替换"; exit 3; }
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态守卫失败 (缺 base/models.yaml ⇒ 疑似嵌套)"; exit 3; }
echo "run=$D port=$PORT tasks=$TASKS reps=$REPS ts=$(date -Is)" > "$D/.owner-r511"
# 夹具指纹 (同窗可比性)
python3 - "$D/evidence/fixture.json" <<'PY'
import hashlib, json, sys
out = {"taskset": "/home/agentuser/AgentFramework/eval/rover/r511/taskset-r511.json",
       "cases_p4": "/home/agentuser/AgentFramework/eval/rover/r511/cases/p4_cases.py",
       "ref_p4": "/home/agentuser/AgentFramework/eval/rover/r511/ref/p4"}
for k, p in list(out.items()):
    try:
        out[k + "_sha12"] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
    except OSError:
        out[k + "_sha12"] = None
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
PY

# --- 1 起手闸: 连续 2 次 PASS --------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R511 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2 adapter (起手后沉降) ---------------------------------------------
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

# --- 3 两臂 × reps 串行 (内存硬约束: 禁并发) ----------------------------
export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
run_arm() { # tag reps [extra...]
  local tag=$1 reps=$2; shift 2
  for k in $(seq 1 "$reps"); do
    local out="$D/$tag-r$k"
    log "== 臂 $tag-r$k =="
    python3 "$R/proj_run_side.py" --side agent --arm "$tag-r$k" --out "$out" --adapter-dir "$D/adapter" \
      --adapter-port "$PORT" --agent-bin "$AGENT_BIN" --taskset "$R/taskset-r511.json" --tasks "$TASKS" \
      "$@" > "$D/logs/arm-$tag-r$k.txt" 2>&1
    local rc=$?
    echo "arm=$tag-r$k rc=$rc" >> "$D/logs/arm-$tag-r$k.txt"
    log "臂 $tag-r$k rc=$rc"
    sleep 3
  done
}
run_arm dflt "$REPS"
run_arm s12 "$REPS" --max-steps "$S12"

# --- 4 汇总判分 ---------------------------------------------------------
python3 "$R/aggregate_r511.py" --run-dir "$D" --json "$D/report.json" 2>&1 | tee "$D/logs/report.txt"
echo "REPORT_RC=${PIPESTATUS[0]}" >> "$D/logs/report.txt"

# --- 5 可验收前置 (铁律 11) --------------------------------------------
python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --round R511 \
  > "$D/logs/precond.txt" 2>&1
echo "PRECOND_RC=$?" | tee -a "$D/logs/precond.txt"

# --- 6 teardown ---------------------------------------------------------
kill "$APID" 2>/dev/null
sleep 2
pkill -f "adapter_tools.py $PORT" 2>/dev/null
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[告警] 端口 $PORT 未释放"; else log "端口已释放"; fi
log "DONE RUN_DIR=$D"
