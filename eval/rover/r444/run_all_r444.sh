#!/usr/bin/env bash
# R444 批次: 前置门等价性/成本(M20 三臂) + 短档/单跳档真值补测(V2b/W8 各两臂)
# 串行理由: 本机 MemTotal 3.57GiB, 单臂 llama-server(-c 4608) RSS ≈ 2.39GB ⇒ 禁并发 (R443 结论)
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r444
export R444_NS="${R444_NS:--s4}"
LOG="$DIR/run_all_r444.log"
: > "$LOG"
echo "[$(date +%H:%M:%S)] R444 批次启动 NS=$R444_NS" | tee -a "$LOG"
for spec in "M20:A" "M20:BRJ" "M20:BRJL" "V2b:A" "V2b:BRJ" "W8:A" "W8:BRJ"; do
  grid="${spec%%:*}"; arm="${spec##*:}"
  echo "[$(date +%H:%M:%S)] >>> grid=$grid arm=$arm" | tee -a "$LOG"
  R444_GRID="$grid" bash "$DIR/run_arm_r444.sh" "$arm" >> "$LOG" 2>&1
  rc=$?
  echo "[$(date +%H:%M:%S)] <<< grid=$grid arm=$arm rc=$rc" | tee -a "$LOG"
done
echo "[$(date +%H:%M:%S)] R444 批次结束" | tee -a "$LOG"
pgrep -af "llama-server|agenthost" | head -5
