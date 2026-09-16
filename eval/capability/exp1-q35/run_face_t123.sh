#!/usr/bin/env bash
# EXP1-Q35 T1..T3: 同树态连续三跑 (窗口内本侧零仓内写入) —— D1a/D1b 的测量体
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
unset AGENTFRAMEWORK_PY_RUN AGENTFRAMEWORK_ARTIFACT_REPAIR
for t in t1 t2 t3; do
  echo "=== RUN $t START $(date -Is) ==="
  /usr/bin/time -f "TIME_$t wall=%es maxrss=%MkB" \
    python3 -u eval/capability/instruments_check.py --out eval/capability/exp1-q35/face_q35_$t.json \
    > eval/capability/exp1-q35/face_q35_$t.out 2>&1
  echo "RC_$t=$?"
  tail -3 eval/capability/exp1-q35/face_q35_$t.out
  echo "=== RUN $t END $(date -Is) ==="
done
echo "ALLDONE $(date -Is)"
