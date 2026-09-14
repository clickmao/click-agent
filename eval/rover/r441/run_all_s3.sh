#!/usr/bin/env bash
# R441 阶段三：V2b 复现对（正确调用式: 网格走 R441_GRID 环境变量, run_arm 只吃 3 个位置参数）
# 教训: 阶段二脚本把网格当第 4 位置参数传入 => 被忽略, 默认 GRID=W8 ⇒ 误跑 W8-b2(已登记为意外复现对)
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r441
export R441_GRID="V2b"
export R441_NS="-c2"
cd /home/agentuser/AgentFramework
echo "=== S3 start $(date -Iseconds) grid=$R441_GRID ns=$R441_NS ==="
bash "$DIR/run_arm.sh" A   48100 48112 || echo "[S3] A-V2b rc=$?"
bash "$DIR/run_arm.sh" BRJ 48100 48122 || echo "[S3] BRJ-V2b rc=$?"
echo "=== S3 end $(date -Iseconds) ==="
