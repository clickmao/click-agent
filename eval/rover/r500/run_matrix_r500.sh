#!/usr/bin/env bash
# R500 起手: 连续 2 次起手闸 PASS ⇒ 起 R499 冻结的 4 臂矩阵 (C + P1/P2/P3)
set -u
cd /home/agentuser/AgentFramework
LOG=/tmp/r500_gate.txt
: >"$LOG"
ok=0
for i in 1 2 3 4; do
  python3 eval/rover/r483/preflight_gate.py --round R500 --out /tmp/pf_r500_$i.json >>"$LOG" 2>&1
  line=$(python3 - /tmp/pf_r500_$i.json <<'PY'
import io, json, sys
try:
    d = json.load(io.open(sys.argv[1], encoding="utf-8-sig"))
except Exception as e:
    print("PARSE_FAIL", e); raise SystemExit
print("%s mem=%s cause=%s src_writes=%s" % (d.get("verdict"), d.get("mem_available_mb"),
      d.get("blocker_cause"), d.get("recent_src_writes_120s")))
PY
)
  echo "采样 $i: $line" | tee -a "$LOG"
  case "$line" in PASS*) ok=$((ok+1));; *) ok=0;; esac
  [ "$ok" -ge 2 ] && { echo "连续 2 次 PASS ⇒ 起跑" | tee -a "$LOG"; break; }
  sleep 45
done
[ "$ok" -ge 2 ] || { echo "[致命] 起手闸未连续 2 次通过 ⇒ 让行" | tee -a "$LOG"; exit 3; }
bash eval/rover/r499/run_rest_r499.sh 2>&1 | tee /tmp/r500_arms.log
rc=${PIPESTATUS[0]}
echo "MATRIX_RC=$rc" | tee -a /tmp/r500_arms.log
exit "$rc"
