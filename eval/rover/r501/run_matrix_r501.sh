#!/usr/bin/env bash
# R501 臂矩阵: C(改写关, 1 跑) + P1,P2,P3(改写开, n=3) —— 形状与 R499 完全相同
# 判据: 每臂 argv 必须**恰好 4 项** (R500 自伤: 5 实参 ⇒ relay PORT=int('r499') ValueError)
set -u
cd /home/agentuser/AgentFramework || exit 1
DIR=eval/rover/r501
LOG=/tmp/r501_arms.log
GATE=/tmp/r501_gate.txt
: >"$GATE"
ok=0
for i in 1 2 3 4; do
  python3 eval/rover/r483/preflight_gate.py --out /tmp/pf_r501.json --round R501 2>&1 | tee /tmp/pf_r501_last.txt >>"$GATE"
  v=$(python3 -c "import json;d=json.load(open('/tmp/pf_r501.json'));print(d.get('verdict',''),d.get('mem_available_mb',''))" 2>/dev/null)
  echo "sample$i: verdict,mem=$v"
  case "$v" in PASS*) ok=$((ok+1));; *) ok=0;; esac
  [ "$ok" -ge 2 ] && break
  sleep 20
done
if [ "$ok" -lt 2 ]; then echo "[致命] 起手闸未连续 2 次 PASS ⇒ 让行" | tee -a "$GATE"; exit 3; fi
echo "[闸] 连续 $ok 次 PASS" | tee -a "$GATE"

declare -a ARMS=( 'C|""|50110|50112' 'P|1|50120|50122' 'P|2|50130|50132' 'P|3|50140|50142' )
: >"$LOG"
for spec in "${ARMS[@]}"; do
  IFS='|' read -r -a f <<< "$spec"
  if [ "${#f[@]}" -ne 4 ]; then echo "[致命] 臂 argv 不是 4 项: $spec"; exit 2; fi
  arm="${f[0]}"; tag="${f[1]}"; rp="${f[2]}"; ap="${f[3]}"
  tag_eval=$(eval echo "$tag")
  echo "== ARM $arm TAG=$tag_eval RELAY=$rp API=$ap ==" | tee -a "$LOG"
  bash "$DIR/run_arm_real_r501.sh" "$arm" "$tag_eval" "$rp" "$ap" >>"$LOG" 2>&1
  rc=$?
  echo "-- rc=$rc --" | tee -a "$LOG"
  if [ "$rc" -ne 0 ]; then echo "[致命] 臂 $arm$tag_eval rc=$rc ⇒ 中止矩阵" | tee -a "$LOG"; exit 4; fi
done
echo "== 完整性 ==" | tee -a "$LOG"
python3 - "$DIR" <<'PY' | tee -a "$LOG"
import io, json, os, sys
d = sys.argv[1]
bad = []
for arm, sfx in [("C", ""), ("P", "1"), ("P", "2"), ("P", "3")]:
    for stem in ("calls-", "usage-", "turns-"):
        p = os.path.join(d, "%s%s%s.jsonl" % (stem, arm, sfx))
        if not (os.path.isfile(p) and os.path.getsize(p) > 0):
            bad.append(p)
    t = os.path.join(d, "teardown-%s%s.json" % (arm, sfx))
    if os.path.isfile(t):
        v = json.load(io.open(t, encoding="utf-8-sig"))
        print("teardown %s%s: %s" % (arm, sfx, json.dumps(v, ensure_ascii=False)[:160]))
    else:
        bad.append(t)
print("MISSING=" + ",".join(bad))
sys.exit(1 if bad else 0)
PY
echo "MATRIX_RC=$?"
