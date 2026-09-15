#!/usr/bin/env bash
# R443-D4b: 无 NS 的 BRJ 同名臂 —— 目录名与 R441 归档一致 ⇒ 与 verdict-BRJ-M20.json 逐位对照 (零回归判据)
# 串行前置: run_all_r443.sh 结束后再跑 (本机单实例 llama-server, 3.57 GiB)。
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r443
LOG=$DIR/run_extra_s1.log
{
  echo "[$(date -Is)] R443-D4b start (无 NS 对照臂)"
  R443_GRID=M20 R443_NS="" bash "$DIR/run_arm_r443.sh" BRJ
  echo "[$(date -Is)] R443-D4b done rc=$?"
} 2>&1 | tee -a "$LOG"
