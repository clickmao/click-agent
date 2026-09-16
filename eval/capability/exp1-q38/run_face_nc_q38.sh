#!/usr/bin/env bash
# EXP1-Q38 候选④: 成员类混合注入面 —— 跑**全量**成员清单 (旧 4 个注入模式都是 --only 定向跑, 看不见信息项成员)。
# 记录落各自命名空间 (instruments-check-class-mixed.json / -class-info-only.json, 见 FACE_OUTPUTS 白名单)。
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"; export PATH="$DOTNET_ROOT:$PATH"
unset AGENTFRAMEWORK_PY_RUN AGENTFRAMEWORK_ARTIFACT_REPAIR
MODE=${1:?inject-mode}
T=${2:?tag}
echo "=== RUN $T ($MODE) START $(date -Is) TREE=$(git rev-parse --short HEAD) ==="
/usr/bin/time -f "TIME_$T wall=%es maxrss=%MkB" \
  python3 -u eval/capability/instruments_check.py "$MODE" > /tmp/q38_$T.out 2>&1
echo "RC_$T=$?"
tail -7 /tmp/q38_$T.out
echo "=== RUN $T END $(date -Is) ==="
