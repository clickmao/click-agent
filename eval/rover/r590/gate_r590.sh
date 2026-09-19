#!/usr/bin/env bash
# R590 起手闸（只读轮仍行使）。派生自 `eval/rover/r589/gate_r589.sh`，**仅改一处自由度 = 余量条款**（候选④）：
#   ① 条款缺分支补全: prev_swing_effective = 在飞窗振幅优先；**只读轮（零臂）无在飞窗 ⇒ 取该轮起手前采样振幅**
#   ② 条款写了「起手前样本 极差 ≤ 50MB」而 r589 实现**未落**（r589 实测极差 361MB 仍被放行）
#      ⇒ 本轮把它实现成 fail-closed 闸
#   ③ 报 cap 是否 binding（binding ⇒ 振幅项退化，不得宣称条款收紧）
set -uo pipefail
REPO=/home/agentuser/AgentFramework
HARNESS=$HOME/.agentframework/harness
D=${D:-$HARNESS/runs/r590}
PDIR=$REPO/eval/rover/r590
GATE=$REPO/eval/rover/r483/preflight_gate.py
MEM_ONCE=$REPO/eval/rover/r571/mem_sample_once.py
GATE_MB=${GATE_MB:-2650}
FLOOR=${FLOOR:-60}
MAXSPREAD=${MAXSPREAD:-50}
PREV_RUN=${PREV_RUN:-r589}
mkdir -p "$D/logs" "$PDIR"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/gate.txt"; }

# ---- ① 余量来源派生（在飞窗优先；只读轮回退到起手前采样）----
DER=$(python3 - "$PREV_RUN" <<'PY'
import json,io,os,sys
prev=sys.argv[1]
base=os.path.expanduser("~/.agentframework/harness/runs/%s/logs"%prev)
def sw(p):
    if not os.path.isfile(p): return None,0
    v=[]
    for ln in io.open(p,encoding="utf-8",errors="replace"):
        ln=ln.strip()
        if not ln: continue
        try: d=json.loads(ln)
        except Exception: continue
        m=d.get("mem_available_mb")
        if isinstance(m,(int,float)): v.append(float(m))
    return (int(max(v)-min(v)) if len(v)>1 else None), len(v)
s1,n1=sw(os.path.join(base,"run-samples.jsonl"))
s2,n2=sw(os.path.join(base,"pre-samples.jsonl"))
if s1 is not None: print("%d in_run %d"%(s1,n1))
elif s2 is not None: print("%d pre_sample_only %d"%(s2,n2))
else: print("None unavailable 0")
PY
)
PREV_SWING=$(echo "$DER" | awk '{print $1}')
SWING_BRANCH=$(echo "$DER" | awk '{print $2}')
SWING_N=$(echo "$DER" | awk '{print $3}')
if [ "$PREV_SWING" = "None" ]; then log "[致命] 上一轮在飞窗与起手前采样均不可估 ⇒ 条款无来源 (fail-closed)"; exit 2; fi

# ---- ② 起手前采样 3 次，机检「极差 ≤ $MAXSPREAD」（条款条件落地）----
: > "$D/logs/pre-samples.jsonl"
for i in 1 2 3; do python3 "$MEM_ONCE" "$D/logs/pre-samples.jsonl" >/dev/null 2>&1; sleep 1; done
read -r CEIL SPREAD <<<"$(python3 - "$D/logs/pre-samples.jsonl" <<'PY'
import json,io,sys
v=[json.loads(l)["mem_available_mb"] for l in io.open(sys.argv[1],encoding="utf-8",errors="replace") if l.strip()]
print(max(v), max(v)-min(v))
PY
)"
log "起手前采样: n=3 ceiling=$CEIL spread=$SPREAD (条件: ≤ $MAXSPREAD)"
if [ "$SPREAD" -gt "$MAXSPREAD" ]; then
  log "[致命] 起手前样本极差 $SPREADMB > $MAXSPREADMB ⇒ 非同态样本 ⇒ 窗口不可开 (fail-closed; r589 此条件未落)"
  echo "{\"rc\":2,\"reason\":\"pre_sample_spread\",\"spread_mb\":$SPREAD,\"max_spread_mb\":$MAXSPREAD}" > "$PDIR/gate-r590-status.json"
  exit 2
fi

MARGIN=$(( PREV_SWING < FLOOR ? FLOOR : PREV_SWING ))
CAP=$(( CEIL - GATE_MB - FLOOR ))
CAP_BINDING=false
if [ "$MARGIN" -gt "$CAP" ]; then MARGIN=$CAP; CAP_BINDING=true; fi
if [ "$MARGIN" -lt "$FLOOR" ]; then
  log "[致命] 顶棚 $CEIL 装不下下限 $FLOOR MB (cap=$CAP) ⇒ 窗口不可开 (fail-closed)"; exit 2
fi
REQ=$(( GATE_MB + MARGIN ))
log "条款: ceiling=$CEIL spread=$SPREAD prev_swing=$PREV_SWING src=$SWING_BRANCH(n=$SWING_N) margin=$MARGIN REQ=$REQ cap=$CAP cap_binding=$CAP_BINDING"

for i in 1 2; do
  python3 "$GATE" --round R590 --gate-mb "$REQ" --out "$D/gate-A$i.json" > "$D/logs/gate-A$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-A$i.json')).get('verdict'))" 2>/dev/null)
  m=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done

# ---- 判别力成对控制（同内存态: 基础门槛 PASS 而条款 GATE_BLOCKED）----
BAND=$((GATE_MB + (REQ - GATE_MB) / 2))
HOGMB=$(( CEIL - BAND )); [ "$HOGMB" -lt 0 ] && HOGMB=0
if [ "$HOGMB" -gt 0 ]; then
  python3 -c "import time,sys
n=int(sys.argv[1]); b=bytearray(n*1024*1024); b[::4096]=b'\x01'*len(b[::4096]); time.sleep(40)" "$HOGMB" &
  HOG=$!; sleep 4
  mdisc=$(python3 "$MEM_ONCE" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
  python3 "$GATE" --round R590DISC --gate-mb "$GATE_MB" --out "$D/gate-disc-base.json" >/dev/null 2>&1
  python3 "$GATE" --round R590DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
  kill $HOG 2>/dev/null; wait $HOG 2>/dev/null
  python3 - "$D" "$mdisc" "$REQ" "$GATE_MB" <<'PY'
import io, json, sys
D, mem, req, base = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
vb = json.load(io.open(D + "/gate-disc-base.json")).get("verdict")
vc = json.load(io.open(D + "/gate-disc-clause.json")).get("verdict")
in_band = base <= mem < req
truth = bool(in_band and vb == "PASS" and vc == "GATE_BLOCKED")
json.dump({"mem_mb": mem, "base": vb, "clause": vc, "in_band": in_band,
           "true_discrimination": truth, "rc": 0 if truth else 3},
          io.open(D + "/gate-disc-pair.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("disc rc=%d mem=%.0f base=%s clause=%s truth=%s" % (0 if truth else 3, mem, vb, vc, truth))
PY
else
  log "判别力成对控制: 压制量 0 ⇒ 未行使，如实登记"
  echo '{"true_discrimination": false, "rc": 3, "note": "压制量 0 ⇒ 未行使 (已登记)"}' > "$D/gate-disc-pair.json"
fi

python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
log "起手闸 B (leak-selfcheck): rc=$?"
python3 - "$PDIR/gate-r590-status.json" "$CEIL" "$SPREAD" "$PREV_SWING" "$SWING_BRANCH" "$MARGIN" "$REQ" "$CAP" "$CAP_BINDING" <<'PY'
import io, json, sys
p, ceil, spread, ps, br, mg, req, cap, bind = sys.argv[1:10]
json.dump({"rc": 0, "ceiling_mb": int(ceil), "spread_mb": int(spread),
           "prev_swing": int(ps), "prev_swing_branch": br, "margin": int(mg),
           "req": int(req), "cap": int(cap), "cap_binding": bind == "true"},
          io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
log "R590 起手闸完成"
