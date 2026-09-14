#!/usr/bin/env bash
# R436 第二网格 (p8, 8 轮) 三臂: A(分母) / B(门+J远端) / BRJ(门+J本地)
# 目的: 与 p12 同二进制同器具, 得「降幅随任务构成」的区间（30% 目标是否只在某一构成上成立）
set -u
cd /home/agentuser/AgentFramework/eval/rover/r436
LOG=/home/agentuser/AgentFramework/eval/rover/r436/arms-run-p8.log
: > "$LOG"
run() {
  echo "===== $(date +%H:%M:%S) ARM=$1 GRID=p8 NS=${2:-} =====" | tee -a "$LOG"
  R436_NS="$2" R436_GRID=p8 bash run_arm.sh "$1" "$3" "$4" 2>&1 | tee -a "$LOG"
  echo "[done] $(date +%H:%M:%S) ARM=$1" | tee -a "$LOG"
}
run A   ""    48010 48012
run B   ""    48014 48016
run BRJ ""    48018 48020
echo "===== P8 DONE $(date +%H:%M:%S) =====" | tee -a "$LOG"
