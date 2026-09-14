#!/usr/bin/env bash
# R439 全臂执行（顺序，避免 llama-server 端口竞争）:
#   1) A-p8   分母复跑（冻结基线复现性）
#   2) A-V20  长任务分母（20 轮）
#   3) BRJ-p8 修复后复测（p12 之外的第二网格 ⇒ 泛化）
#   4) BRJ-V20 长任务治疗臂（≥30% 降幅的域扩展）
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r439
cd /home/agentuser/AgentFramework || exit 1
echo "[$(date -Iseconds)] R439 run_all start  launcher_pid=$$"
for spec in "A p8 47990 47992" "A V20 47994 47996" "BRJ p8 47998 48000" "BRJ V20 48002 48004"; do
  set -- $spec
  echo "[$(date -Iseconds)] >>> arm=$1 grid=$2"
  R439_GRID=$2 bash "$DIR/run_arm.sh" "$1" "$3" "$4"
  echo "[$(date -Iseconds)] <<< arm=$1 grid=$2 rc=$?"
done
echo "[$(date -Iseconds)] R439 run_all done"
