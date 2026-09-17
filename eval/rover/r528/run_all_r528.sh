#!/usr/bin/env bash
# R528 三窗口驱动: w1..w3 串行, 后续窗口把前窗 adapter 目录传给前缀机检 ⇒ 跨窗口常量前缀判定。
# 铁律: 禁 push; 禁多进程并发 (2 vCPU/3.57 GiB) ⇒ 窗口严格串行。
set -uo pipefail
R=/home/agentuser/AgentFramework/eval/rover/r528
DS=${1:-$(date +%m%d-%H%M%S)}
LOG=$R/logs-driver-$DS.txt
ALSO=""
for w in ${2:-w1 w2 w3}; do
  R528_WINDOW=$w R528_DS=$DS R528_RUN_DIR="$R/run-$DS-$w" R528_ALSO="$ALSO" \
    bash "$R/run_r528.sh" >> "$LOG" 2>&1
  rc=$?
  D="$R/run-$DS-$w"
  echo "[driver] window=$w rc=$rc run=$D" | tee -a "$LOG"
  [ -d "$D/adapter" ] && ALSO="$ALSO $D/adapter"
done
echo "[driver] ALL DONE ds=$DS" | tee -a "$LOG"
