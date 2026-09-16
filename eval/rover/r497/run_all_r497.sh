#!/usr/bin/env bash
# R497 六臂顺序真机执行器 (STOP 哨兵可让行; 单臂失败不阻断后续臂, 但记 rc)
# 用法: bash run_all_r497.sh [B T0 T2 T1 T1n O1]
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r497
LOG=$DIR/runs-r497.log
ARMS=("$@")
if [ "${#ARMS[@]}" -eq 0 ]; then ARMS=(B T0 T2 T1 T1n O1); fi
: > "$LOG"
echo "[all] 起始 $(date '+%F %H:%M:%S') 臂=${ARMS[*]} STOP=$([ -f "$DIR/STOP" ] && echo 在位 || echo 无)" | tee -a "$LOG"
for A in "${ARMS[@]}"; do
  if [ -f "$DIR/STOP" ]; then
    echo "[stop $(date +%H:%M:%S)] STOP 哨兵在位 ⇒ 跳过臂 $A (让行)" | tee -a "$LOG"
    continue
  fi
  echo "[=== $(date '+%H:%M:%S') arm=$A START ==]" | tee -a "$LOG"
  bash "$DIR/run_arm_real_r497.sh" "$A" >> "$LOG" 2>&1
  rc=$?
  echo "[=== $(date '+%H:%M:%S') arm=$A END rc=$rc ==]" | tee -a "$LOG"
done
echo "[all] 结束 $(date '+%F %H:%M:%S')" | tee -a "$LOG"
grep -E "arm=.*(END rc|START)" "$LOG" | tail -14
