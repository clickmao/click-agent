#!/usr/bin/env bash
# R441 阶段一全臂（顺序，避免 llama-server 端口竞争）
#   窗口下界: W8(1/8=12.5%) → W20(1/20=5%) ; 位置曲线: M20(中簇 7/20)
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r441
cd /home/agentuser/AgentFramework || exit 1
echo "[$(date -Iseconds)] R441 run_all_s1 start  launcher_pid=$$"
for spec in "A W8 48100 48102" "BRJ W8 48104 48106" \
            "A W20 48108 48110" "BRJ W20 48112 48114" \
            "A M20 48116 48118" "BRJ M20 48120 48122"; do
  set -- $spec
  echo "[$(date -Iseconds)] >>> arm=$1 grid=$2 stub=$3 api=$4"
  R441_GRID=$2 bash "$DIR/run_arm.sh" "$1" "$3" "$4"
  echo "[$(date -Iseconds)] <<< arm=$1 grid=$2 rc=$?"
done
echo "[$(date -Iseconds)] R441 run_all_s1 done"
