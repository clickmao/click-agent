#!/usr/bin/env bash
# R529 三窗口驱动: w1..w3 串行, 后续窗口把前窗 adapter 目录传给前缀机检 ⇒ 跨窗口常量前缀判定。
# 铁律: 禁 push; 禁多进程并发 (2 vCPU/3.57 GiB) ⇒ 窗口严格串行; 单窗读数=噪声 ⇒ reps>=3 且逐窗报。
set -uo pipefail
R=/home/agentuser/AgentFramework/eval/rover/r529
DS=${1:-$(date +%m%d-%H%M%S)}
LOG=$R/logs-driver-$DS.txt
ALSO=""
shift || true
WINLIST=("$@"); [ ${#WINLIST[@]} -eq 0 ] && WINLIST=(w1 w2 w3)
for w in "${WINLIST[@]}"; do
  R529_WINDOW=$w R529_DS=$DS R529_RUN_DIR="$R/run-$DS-$w" R529_ALSO="$ALSO" \
    bash "$R/run_r529.sh" >> "$LOG" 2>&1
  rc=$?
  D="$R/run-$DS-$w"
  echo "[driver] window=$w rc=$rc run=$D" | tee -a "$LOG"
  [ -d "$D/adapter" ] && ALSO="$ALSO $D/adapter"
done
echo "[driver] ALL DONE ds=$DS" | tee -a "$LOG"
