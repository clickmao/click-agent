#!/usr/bin/env bash
# R589 判别力成对控制（**修后版**）：定因 = R589 自捕 #3 —— 首版用**本侧采样器**读数做 in_band，
#   而闸自报的 mem_available_mb 系统性高于本侧采样器（实测 2725 vs 2820，+95MB，因闸内部有
#   settle/reap 段）⇒ 两个仪器混用 ⇒ 判据恒不可行（rc=3 假「未行使」）。
#   修法 = in_band **只用闸自己的落盘读数**（同仪器可比），并把首版读数（rc=3）留档不翻案。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
D=${D:-$HOME/.agentframework/harness/runs/r589}
GATE=$REPO/eval/rover/r483/preflight_gate.py
GATE_MB=${GATE_MB:-2650}
REQ=${REQ:-2795}
mkdir -p "$D/logs"
TARGET=$(( GATE_MB + (REQ - GATE_MB) / 2 ))
PY_MEM=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
HOGMB=$(( PY_MEM - TARGET )); [ "$HOGMB" -lt 0 ] && HOGMB=0
echo "disc: free_now=${PY_MEM}MB target=${TARGET}MB hog=${HOGMB}MB"
if [ "$HOGMB" -gt 0 ]; then
  python3 -c "import time,sys
n=int(sys.argv[1]); b=bytearray(n*1024*1024); b[::4096]=b'\x01'*len(b[::4096]); time.sleep(90)" "$HOGMB" &
  HOG=$!; sleep 5
  python3 "$GATE" --round R589DISC --gate-mb "$GATE_MB" --out "$D/gate-disc-base.json" >/dev/null 2>&1
  python3 "$GATE" --round R589DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
  kill $HOG 2>/dev/null; wait $HOG 2>/dev/null
fi
python3 - "$D" "$REQ" "$GATE_MB" <<'PY'
import io, json, sys
D, req, base = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
db = json.load(io.open(D + "/gate-disc-base.json"))
dc = json.load(io.open(D + "/gate-disc-clause.json"))
mb, mc = db.get("mem_available_mb"), dc.get("mem_available_mb")
vb, vc = db.get("verdict"), dc.get("verdict")
in_band = (mb is not None and base <= float(mb) < req) or (mc is not None and base <= float(mc) < req)
truth = bool(in_band and vb == "PASS" and vc == "GATE_BLOCKED")
out = {"instrument": "in_band 用闸自报 mem_available_mb (同仪器可比; R589 自捕 #3 修法)",
       "mem_base_mb": mb, "mem_clause_mb": mc, "base": vb, "clause": vc,
       "in_band": in_band, "true_discrimination": truth, "rc": 0 if truth else 3,
       "v1_archived": {"file": "gate-disc-pair-v1crossinstrument.json",
                       "why": "首版混用本侧采样器读数 ⇒ rc=3 假未行使 (不翻案)"}}
json.dump(out, io.open(D + "/gate-disc-pair.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("disc rc=%d mem_base=%s mem_clause=%s base=%s clause=%s truth=%s" % (
    0 if truth else 3, mb, mc, vb, vc, truth))
PY
