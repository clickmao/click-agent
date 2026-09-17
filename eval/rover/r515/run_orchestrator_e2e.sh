#!/usr/bin/env bash
# R515 真机 E2E: 长任务编排器 vs 单轮 (同窗口·同题面·同模型·同环境)
#   臂 single : 一次成型 (全题面一条消息, AGENTFRAMEWORK_ACTION_MAX_STEPS=6)      —— 内窗基线
#   臂 orch   : 编排器 (p4 拆 4 节点: n1/n2 同层并发 + n3 依赖整合 + n4 本地自测与 n2 重叠)
# 判分: 只判副本 (R512 教训); 每臂独立会话 (R509 铁律); 起手闸连续 2 PASS (R515 铁律沿用)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r515
PORT=${R515_ADAPTER_PORT:-48690}
TS=${R515_TS:-$(date +%m%d-%H%M%S)}
D=${R515_RUN_DIR:-/tmp/r515/run-$TS}
BIN=${R515_AGENT_BIN:-/tmp/pub_r515/agenthost}
CFGSRC=${R515_CFG_SEED:-/tmp/r455_env/agent/cfg}
NODESTEPS=${R515_NODE_STEPS:-6}
log() { echo "[$(date +%H:%M:%S)] $*"; }

# --- 0 守卫 ---------------------------------------------------------------
[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺本侧 AOT $BIN"; exit 3; }
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 被占用"; exit 4; fi
mkdir -p "$D"/{adapter,logs} "$D/agent" "$D/single/ws" "$D/orch/ws"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态守卫失败 (疑似嵌套)"; exit 3; }
echo "run=$D port=$PORT node_steps=$NODESTEPS ts=$(date -Is)" > "$D/.owner-r515"

# 夹具指纹 (同窗可比性)
python3 - "$D/evidence-fixture.json" <<'PY'
import hashlib, json, os, sys
def sha_path(p):
    if os.path.isdir(p):
        h = hashlib.sha256()
        for root, dirs, files in os.walk(p):
            dirs.sort(); files.sort()
            for fn in files:
                fp = os.path.join(root, fn)
                h.update(os.path.relpath(fp, p).encode())
                h.update(open(fp, "rb").read())
        return h.hexdigest()[:12]
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12]
out = {}
for k, p in {"taskset_r511": "/home/agentuser/AgentFramework/eval/rover/r511/taskset-r511.json",
             "cases_p4": "/home/agentuser/AgentFramework/eval/rover/r511/cases/p4_cases.py",
             "ref_p4": "/home/agentuser/AgentFramework/eval/rover/r511/ref/p4",
             "grade_r511": "/home/agentuser/AgentFramework/eval/rover/r511/grade_r511.py",
             "plan_p4": "/home/agentuser/AgentFramework/eval/rover/r515/plan-p4.txt"}.items():
    try:
        out[k + "_sha12"] = sha_path(p)
    except OSError:
        out[k + "_sha12"] = None
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
PY

# 题面 (与 R513 v2 同源; 两臂逐字节同输入)
python3 - "$D/p4-prompt.txt" <<'PY'
import json, sys
ts = json.load(open("/home/agentuser/AgentFramework/eval/rover/r511/taskset-r511.json", encoding="utf-8"))
p4 = next(t for t in ts["tasks"] if t["tid"] == "p4")
open(sys.argv[1], "w", encoding="utf-8").write(p4["prompt"])
print("PROMPT_SHA12=%s BYTES=%d" % (__import__("hashlib").sha256(p4["prompt"].encode()).hexdigest()[:12], len(p4["prompt"].encode())))
PY

# --- 1 起手闸: 连续 2 次 PASS --------------------------------------------
for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R515 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过 ⇒ 不起臂"; exit 2; }
done

# --- 2 adapter (起手后沉降) ---------------------------------------------
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

maxidx() { python3 - "$D/adapter" "$1" <<'PY'
import os, re, sys
d = sys.argv[1]; m = 0
try:
    for fn in os.listdir(d):
        r = re.match(r"^side-[A-Za-z0-9_]+-(\d+)\.json$", fn)
        if r: m = max(m, int(r.group(1)))
except OSError: pass
open(sys.argv[2], "w").write(str(m))
print(m)
PY
}

export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
export AGENTFRAMEWORK_PY_RUN=1
PROMPT=$(cat "$D/p4-prompt.txt")

# --- 3 臂 single: 一次成型 (6 步硬预算) ---------------------------------
log "== 臂 single (一次成型, 6 步) =="
maxidx "$D/single/idx-before" > /dev/null
AGENTFRAMEWORK_WORKSPACE="$D/single/ws" AGENTFRAMEWORK_ACTION_MAX_STEPS=${R515_SINGLE_STEPS:-6} \
AGENTFRAMEWORK_ACTION_AUDIT="$D/single/audit" \
timeout 900 "$BIN" -q "$PROMPT" --output-mode text --session-id "r515-single-$TS" \
  > "$D/single/reply.txt" 2> "$D/single/stderr.txt"
echo "SINGLE_RC=$?" | tee "$D/logs/single.txt"
maxidx "$D/single/idx-after" > /dev/null
sleep 3

# --- 4 臂 orch: 编排器 (4 节点, 每节点 6 步) -----------------------------
log "== 臂 orch (编排器 4 节点 × $NODESTEPS 步) =="
maxidx "$D/orch/idx-before" > /dev/null
AGENTFRAMEWORK_WORKSPACE="$D/orch/ws" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch/audit" \
"$BIN" --orchestrate "${R515_PLAN:-$R/plan-p4.txt}" --node-steps "$NODESTEPS" \
  --workspace "$D/orch/ws" --report "$D/orch/report.json" --session "r515-orch-$TS" \
  > "$D/orch/stdout.txt" 2> "$D/orch/stderr.txt"
echo "ORCH_RC=$?" | tee "$D/logs/orch.txt"
maxidx "$D/orch/idx-after" > /dev/null
sleep 3

# --- 5 判分 (只判副本) ---------------------------------------------------
for arm in single orch; do
  rm -rf "$D/grade-$arm"; mkdir -p "$D/grade-$arm"
  [ -d "$D/$arm/ws/tasksvc" ] && cp -r "$D/$arm/ws/tasksvc" "$D/grade-$arm/"
  python3 "$REPO/eval/rover/r511/grade_r511.py" --task p4 --dir "$D/grade-$arm" \
    --json "$D/grade-$arm.json" > "$D/logs/grade-$arm.txt" 2>&1
  echo "GRADE_${arm}_RC=$?" | tee -a "$D/logs/grade-$arm.txt"
done

# --- 6 读数汇总 ---------------------------------------------------------
python3 "$R/summarize_r515.py" --run-dir "$D" --json "$D/report.json" 2>&1 | tee "$D/logs/summary.txt"

# --- 7 teardown ---------------------------------------------------------
kill "$APID" 2>/dev/null
sleep 2
pkill -f "adapter_tools.py $PORT" 2>/dev/null
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[告警] 端口 $PORT 未释放"; else log "端口已释放"; fi
log "DONE RUN_DIR=$D"
