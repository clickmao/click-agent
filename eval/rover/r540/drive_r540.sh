#!/usr/bin/env bash
# R540 两窗驱动: 串行起两窗 (w1 → w2), 各窗独立 adapter 端口/独立 run 目录/独立 claim。
# 单窗失败 ⇒ 记录并继续下一窗(不掩盖); 全窗结果由 R540_WINDOWS 显式声明, 缺窗按 fail-closed 记「未测」。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
R=$REPO/eval/rover/r540
WINDOWS="${R540_WINDOWS:-w1 w2}"
declare -A PORTMAP=( [w1]=48971 [w2]=48972 )
rcs=""
for W in $WINDOWS; do
  echo "=== R540 窗 $W 起 ($(date -Is)) ===" | tee -a "$R/logs/drive.txt"
  R540_WINDOW="$W" R540_ADAPTER_PORT="${PORTMAP[$W]}" R540_RUN_DIR="$R/run-$W" \
    bash "$R/run_r540.sh" >> "$R/logs/drive-$W.txt" 2>&1
  rc=$?
  echo "=== R540 窗 $W 收 rc=$rc ($(date -Is)) ===" | tee -a "$R/logs/drive.txt"
  rcs="$rcs $W=$rc"
  sleep 5
done
echo "R540 全部窗收口: $(date -Is) rc:$rcs" | tee -a "$R/logs/drive.txt"
[ "$rcs" = " w1=0 w2=0" ] || exit 1
exit 0
