#!/usr/bin/env bash
# R515 增补臂 (事后增补, 非主验收依据): 规模臂 — 双包长任务 (p3 kvsvc + p4 tasksvc, 6 文件/24 隐藏用例)
#   arm single2: 两包契约一次成型 (6 步硬预算)
#   arm orch2  : 编排器 7 节点链 (每层 ≤1 远端 + 本地自测, 每节点 6 步 ⇒ 预算上界 42 步)
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r515
PORT=${R515S_ADAPTER_PORT:-48691}
TS=${R515S_TS:-$(date +%m%d-%H%M%S)}
D=${R515S_RUN_DIR:-/tmp/r515/scale-$TS}
BIN=${R515_AGENT_BIN:-/tmp/pub_r515/agenthost}
CFGSRC=${R515_CFG_SEED:-/tmp/r455_env/agent/cfg}
NODESTEPS=${R515_NODE_STEPS:-6}
log() { echo "[$(date +%H:%M:%S)] $*"; }

[ -e "$D" ] && { log "[致命] $D 已存在(禁覆盖)"; exit 4; }
[ -d "$CFGSRC" ] || { log "[致命] 缺 cfg 雏形 $CFGSRC"; exit 3; }
[ -x "$BIN" ] || { log "[致命] 缺本侧 AOT $BIN"; exit 3; }
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[致命] 端口 $PORT 被占用"; exit 4; fi
mkdir -p "$D"/{adapter,logs} "$D/agent" "$D/single2/ws" "$D/orch2/ws"
cp -r "$CFGSRC" "$D/agent/cfg" || { log "[致命] cfg 拷贝失败"; exit 3; }
grep -rl '486[0-9][0-9]' "$D/agent/cfg" 2>/dev/null | xargs -r sed -i -E "s/486[0-9][0-9]/$PORT/g"
[ -f "$D/agent/cfg/base/models.yaml" ] || { log "[致命] cfg 形态守卫失败"; exit 3; }
echo "run=$D port=$PORT node_steps=$NODESTEPS $(date -Is)" > "$D/.owner-r515-scale"

# 两包合并题面 (两臂逐字节同输入)
python3 - "$D/both-prompt.txt" <<'PY'
import json, sys
ts = json.load(open("/home/agentuser/AgentFramework/eval/rover/r511/taskset-r511.json", encoding="utf-8"))
g = lambda t: next(x for x in ts["tasks"] if x["tid"] == t)["prompt"]
txt = (g("p3") + "\n\n===== 第二个交付物 (同一工作区) =====\n\n" + g("p4") +
       "\n\n两个交付物都必须落在工作区根下的包目录里 (kvsvc/ 与 tasksvc/), 互相独立, 各自可运行。")
open(sys.argv[1], "w", encoding="utf-8").write(txt)
print("BOTH_BYTES=%d" % len(txt.encode()))
PY

for i in 1 2; do
  python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R515 --out "$D/gate-$i.json" > "$D/logs/gate-$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-$i.json')).get('verdict'))" 2>/dev/null)
  log "起手闸 $i: $v"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 $i 未过"; exit 2; }
done

set -a; . "$REPO/.env.local"; set +a
DEMO_OUT="$D/adapter" setsid nohup python3 "$REPO/eval/rover/r455/adapter_tools.py" "$PORT" > "$D/logs/adapter.txt" 2>&1 &
APID=$!
ok=0
for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && { ok=1; break; }; sleep 0.5; done
[ "$ok" = "1" ] || { log "[致命] adapter 未就绪"; kill "$APID" 2>/dev/null; exit 3; }
log "adapter up pid=$APID port=$PORT"; sleep 5

maxidx() { python3 - "$D/adapter" "$1" <<'PY'
import os, re, sys
m = 0
try:
    for fn in os.listdir(sys.argv[1]):
        r = re.match(r"^side-[A-Za-z0-9_]+-(\d+)\.json$", fn)
        if r: m = max(m, int(r.group(1)))
except OSError: pass
open(sys.argv[2], "w").write(str(m)); print(m)
PY
}

export AGENTFRAMEWORK_CONFIG="$D/agent/cfg"
export AGENTFRAMEWORK_PY_RUN=1
PROMPT=$(cat "$D/both-prompt.txt")

log "== 臂 single2 (两包一次成型, 6 步) =="
maxidx "$D/single2/idx-before" > /dev/null
AGENTFRAMEWORK_WORKSPACE="$D/single2/ws" AGENTFRAMEWORK_ACTION_MAX_STEPS=6 \
AGENTFRAMEWORK_ACTION_AUDIT="$D/single2/audit" \
timeout 1200 "$BIN" -q "$PROMPT" --output-mode text --session-id "r515s-single-$TS" \
  > "$D/single2/reply.txt" 2> "$D/single2/stderr.txt"
echo "SINGLE2_RC=$?" | tee "$D/logs/single2.txt"
maxidx "$D/single2/idx-after" > /dev/null
sleep 3

log "== 臂 orch2 (编排器 7 节点 × $NODESTEPS 步) =="
maxidx "$D/orch2/idx-before" > /dev/null
AGENTFRAMEWORK_WORKSPACE="$D/orch2/ws" AGENTFRAMEWORK_ACTION_AUDIT="$D/orch2/audit" \
"$BIN" --orchestrate "$R/plan-p3p4.txt" --node-steps "$NODESTEPS" --max-nodes 12 \
  --workspace "$D/orch2/ws" --report "$D/orch2/report.json" --session "r515s-orch-$TS" \
  > "$D/orch2/stdout.txt" 2> "$D/orch2/stderr.txt"
echo "ORCH2_RC=$?" | tee "$D/logs/orch2.txt"
maxidx "$D/orch2/idx-after" > /dev/null
sleep 3

# 判分: 两包分判, 只判副本 (每包独立目录, 避免 no_temp_residue 交叉干扰)
for arm in single2 orch2; do
  for t in p3 p4; do
    pkg=$([ "$t" = "p3" ] && echo kvsvc || echo tasksvc)
    rm -rf "$D/grade-$arm-$t"; mkdir -p "$D/grade-$arm-$t"
    [ -d "$D/$arm/ws/$pkg" ] && cp -r "$D/$arm/ws/$pkg" "$D/grade-$arm-$t/"
    python3 "$REPO/eval/rover/r511/grade_r511.py" --task "$t" --dir "$D/grade-$arm-$t" \
      --json "$D/grade-$arm-$t.json" > "$D/logs/grade-$arm-$t.txt" 2>&1
    echo "GRADE_${arm}_${t}_RC=$?" | tee -a "$D/logs/grade-$arm-$t.txt"
  done
done

python3 - "$D" <<'PY'
import json, os, sys
d = sys.argv[1]
print("== R515 增补臂 (规模) 读数 ==")
for arm in ("single2", "orch2"):
    tot = ok = 0
    for t in ("p3", "p4"):
        try: g = json.load(open(os.path.join(d, "grade-%s-%s.json" % (arm, t)), encoding="utf-8"))
        except Exception: g = {}
        print("  %-8s %s 用例 %s/%s rc=%s" % (arm, t, g.get("cases_passed"), g.get("cases_total"), g.get("rc")))
        tot += g.get("cases_total") or 0; ok += g.get("cases_passed") or 0
    print("  %-8s 合计 %d/%d" % (arm, ok, tot))
r = os.path.join(d, "orch2/report.json")
if os.path.exists(r):
    o = json.load(open(r, encoding="utf-8"))
    print("编排器: state=%s 节点=%d 预算上界=%s 重叠=%sms" % (o.get("state"), len(o.get("nodes") or []), o.get("budget_ceiling"), o.get("overlap_ms")))
    for n in o.get("nodes") or []:
        print("   %-3s L%-2s %-7s %-10s %6sms files=%s %s" % (n.get("node_id"), n.get("level"), n.get("location"), n.get("state"),
              n.get("elapsed_ms"), ",".join(n.get("files") or []) or "-", n.get("error") or ""))
PY

kill "$APID" 2>/dev/null; sleep 2
pkill -f "adapter_tools.py $PORT" 2>/dev/null
if ss -ltn 2>/dev/null | grep -q ":$PORT "; then log "[告警] 端口 $PORT 未释放"; else log "端口已释放"; fi
log "DONE SCALE_RUN_DIR=$D"
