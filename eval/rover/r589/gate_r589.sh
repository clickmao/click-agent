#!/usr/bin/env bash
# R589 起手闸（只读轮仍行使；MARGIN := min(prev_swing, ceiling − GATE − floor) 夹取上界）
#   PREV_SWING 由 R588 实测振幅**派生**（不硬编码）: r588/logs/run-samples.jsonl mem_available_mb 极差
set -uo pipefail
REPO=/home/agentuser/AgentFramework
HARNESS=$HOME/.agentframework/harness
D=${D:-$HARNESS/runs/r589}
PDIR=$REPO/eval/rover/r589
GATE=$REPO/eval/rover/r483/preflight_gate.py
MEM_ONCE=$REPO/eval/rover/r571/mem_sample_once.py
GATE_MB=${GATE_MB:-2650}
mkdir -p "$D/logs" "$PDIR"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/gate.txt"; }

PREV_SWING=$(python3 - <<'PY'
import json,io,os
p=os.path.expanduser("~/.agentframework/harness/runs/r588/logs/run-samples.jsonl")
v=[]
for ln in io.open(p,encoding="utf-8",errors="replace"):
    ln=ln.strip()
    if not ln: continue
    try: d=json.loads(ln)
    except Exception: continue
    m=d.get("mem_available_mb")
    if isinstance(m,(int,float)): v.append(float(m))
print(int(max(v)-min(v)) if len(v)>1 else 60)
PY
)
PY_MEM=$(python3 "$MEM_ONCE" "$D/logs/pre-samples.jsonl" | sed 's/.*=//')
CEIL=${PY_MEM%.*}; CEIL=${CEIL:-0}
MARGIN=$(( PREV_SWING > 60 ? PREV_SWING : 60 ))
CAP=$(( CEIL - GATE_MB - 60 ))
[ "$MARGIN" -gt "$CAP" ] && MARGIN=$CAP
if [ "$MARGIN" -lt 60 ]; then log "[致命] 顶棚 $CEIL 装不下下限 60MB ⇒ 窗口不可开 (fail-closed)"; exit 2; fi
REQ=$(( GATE_MB + MARGIN ))
log "起手闸条款: ceiling=$CEIL prev_swing=$PREV_SWING (=R588 实测振幅, n=$(wc -l < $HARNESS/runs/r588/logs/run-samples.jsonl)) margin=$MARGIN REQ=$REQ (cap=$CAP)"

for i in 1 2; do
  python3 "$GATE" --round R589 --gate-mb "$REQ" --out "$D/gate-A$i.json" > "$D/logs/gate-A$i.txt" 2>&1
  v=$(python3 -c "import json;print(json.load(open('$D/gate-A$i.json')).get('verdict'))" 2>/dev/null)
  m=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  log "起手闸 A$i: $v (mem=${m}MB, REQ=${REQ}MB)"
  [ "$v" = "PASS" ] || { log "[致命] 起手闸 A$i 未过 ⇒ 不起臂"; exit 2; }
done

# 判别力成对控制 (同内存态: 基础门槛 PASS 而条款 GATE_BLOCKED)
BAND=$((GATE_MB + (REQ - GATE_MB) / 2))
HOGMB=$(( CEIL - BAND )); [ "$HOGMB" -lt 0 ] && HOGMB=0
if [ "$HOGMB" -gt 0 ]; then
  python3 -c "import time,sys
n=int(sys.argv[1]); b=bytearray(n*1024*1024); b[::4096]=b'\x01'*len(b[::4096]); time.sleep(45)" "$HOGMB" &
  HOG=$!; sleep 4
  mdisc=$(python3 "$MEM_ONCE" "$D/logs/disc-sample.jsonl" | sed 's/.*=//')
  python3 "$GATE" --round R589DISC --gate-mb "$GATE_MB" --out "$D/gate-disc-base.json" >/dev/null 2>&1
  python3 "$GATE" --round R589DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
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
  log "判别力成对控制: 压制量 0 ⇒ 未行使, 如实登记"
  echo '{"true_discrimination": false, "rc": 3, "note": "压制量 0 ⇒ 未行使 (已登记)"}' > "$D/gate-disc-pair.json"
fi

python3 "$REPO/eval/rover/r507pre/exec_precondition.py" --leak-selfcheck --out "$D/leak-selfcheck.json" > "$D/logs/leak-selfcheck.txt" 2>&1
log "起手闸 B (leak-selfcheck): rc=$?"
log "R589 起手闸完成"
