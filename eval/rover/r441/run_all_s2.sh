#!/usr/bin/env bash
# R441 阶段二：V2b 确定性复现对（与 R440 同 sha 二进制同网格 ⇒ 应逐位复现, 判据 C7）
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r441
export R441_NS="-b2"   # 避开 REFUSE_NS_COLLISION（同 NS 下已有 W8/W20/M20 判词）
cd /home/agentuser/AgentFramework
echo "=== S2 start $(date -Iseconds) ==="
if [ -f "$DIR/grid/task-V2b.json" ]; then
  bash "$DIR/run_arm.sh" A   48100 48112 V2b  || echo "[S2] A-V2b rc=$?"
  bash "$DIR/run_arm.sh" BRJ 48100 48122 V2b  || echo "[S2] BRJ-V2b rc=$?"
else
  echo "[S2] SKIP: missing grid/task-V2b.json"
  ls -la "$DIR/grid"
fi
echo "=== S2 end $(date -Iseconds) ==="
