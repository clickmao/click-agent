#!/usr/bin/env bash
# R568 候选④ 判别带**成对控制** (确定性压制到带内, 非靠等状态)
# 目的: 证明条款 (REQ=2753) 相对基础门槛 (2650) 在**同一内存态**下确实更严 ⇒ 条款有牙。
# 零开发: 只调既有闸 (preflight_gate.py --gate-mb)。
set -u
REPO=/home/agentuser/AgentFramework
PDIR="$REPO/eval/rover/r568"
D=/tmp/r568
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$D/logs/gate-c.txt"; }
REQ=$(python3 -c "import json;print(int(json.load(open('$PDIR/gate-margin-r568.json'))['required_mb']))")
MID=$(( (2650 + REQ) / 2 ))
log "目标带 = [2650, $REQ) 中点 = $MID"

cur=$(python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/disc-sample-c.jsonl" | sed 's/.*=//')
HOG=$(( cur - MID )); [ "$HOG" -lt 0 ] && HOG=0
log "当前 $cur MB ⇒ 需占用 $HOG MB"
python3 -c "import time,sys
n=int(sys.argv[1])
b=bytearray(n*1024*1024)
b[::4096]=b'\x01'*len(b[::4096])
time.sleep(300)" "$HOG" &
HOGPID=$!
sleep 6
now=$(python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/disc-sample-c.jsonl" | sed 's/.*=//')
log "压制后节点内读数 = $now MB"

python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568DISC --gate-mb 2650 --out "$D/gate-disc-base2650.json" >/dev/null 2>&1
python3 "$REPO/eval/rover/r483/preflight_gate.py" --round R568DISC --gate-mb "$REQ" --out "$D/gate-disc-clause.json" >/dev/null 2>&1
kill $HOGPID 2>/dev/null; wait $HOGPID 2>/dev/null
sleep 3
after=$(python3 "$REPO/eval/rover/r567/mem_sample_once.py" "$D/logs/disc-sample-c.jsonl" | sed 's/.*=//')
log "已释放占用; 收尾读数 = $after MB"

python3 - "$D" "$PDIR" "$REQ" "$now" "$after" <<'PY'
import io, json, os, sys
D, PDIR, req, now, after = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
def g(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}
b, c = g(D + "/gate-disc-base2650.json"), g(D + "/gate-disc-clause.json")
mb, mc = b.get("mem_available_mb"), c.get("mem_available_mb")
in_band = MB = False
if mb is not None:
    MB = 2650.0 <= mb < req
disc = bool(MB and b.get("verdict") == "PASS" and c.get("verdict") == "GATE_BLOCKED")
rec = {"round": "R568", "candidate": "④ 起手闸判别带成对控制 (确定性压制)",
       "planned_band": [2650, req], "sample_before_hog_mb": None, "state_after_pressure_mb": now,
       "state_after_release_mb": after,
       "base": {"gate_mb": 2650, "mem_mb": mb, "verdict": b.get("verdict"), "blockers": b.get("blockers")},
       "clause": {"gate_mb": req, "mem_mb": mc, "verdict": c.get("verdict"), "blockers": c.get("blockers")},
       "state_in_band": MB, "true_discrimination": disc,
       "teeth": ("同一内存态 (base 调用读到 %sMB): 基础门槛 PASS ∧ 条款 GATE_BLOCKED ⇒ 条款严格更严 (有牙)" % mb
                 if disc else "未落在判别带 ⇒ 判别力未行使 (如实记, 不得据此刻度)"),
       "rc": (3 if mb is None or mc is None else (0 if disc else 2)),
       "rc_semantics": "0 判别力为真 / 2 未行使 / 3 输入缺失"}
json.dump(rec, io.open(os.path.join(PDIR, "gate-disc-c-r568.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(rec, ensure_ascii=False))
PY
exit 0
