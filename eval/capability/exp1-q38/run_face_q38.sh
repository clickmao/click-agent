#!/usr/bin/env bash
# EXP1-Q37 T10: 全量面记录单跑 (同树态; 窗口内本侧零仓内写入 —— 输出与日志全落 /tmp)
# 前置: 必须先过 precheck_occupancy.sh (占用核验落盘再读) ⇒ 本脚本只跑面, 不做任何判断
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
unset AGENTFRAMEWORK_PY_RUN AGENTFRAMEWORK_ARTIFACT_REPAIR
T=${1:-t10}
OUT=/tmp/q38_face_$T
echo "=== RUN $T START $(date -Is) TREE=$(git rev-parse --short HEAD) ==="
/usr/bin/time -f "TIME_$T wall=%es maxrss=%MkB" \
  python3 -u eval/capability/instruments_check.py --out $OUT.json > $OUT.out 2>&1
echo "RC_$T=$?"
tail -8 $OUT.out
echo "=== RUN $T END $(date -Is) ==="
