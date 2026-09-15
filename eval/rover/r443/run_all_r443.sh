#!/usr/bin/env bash
# R443 全臂串行 — 同一网格 M20: A(分母) → BRJ(生产行为) → BRJRP(回放被跳轮内联块 = 消融臂)
# 串行原因: 本机 MemTotal 3.57 GiB, llama-server 单实例 RSS ~2.39 GB ⇒ 禁并发。
set -u
DIR=/home/agentuser/AgentFramework/eval/rover/r443
LOG=$DIR/run_all_s1.log
{
  echo "[$(date -Is)] R443 run_all_s1 start launcher_pid=$$"
  echo "[$(date -Is)] bin=$(ls -l --time-style=+%H:%M:%S /tmp/pub_r443/agenthost) sha=$(sha256sum /tmp/pub_r443/agenthost | cut -c1-16)"
  for arm in A BRJ BRJRP; do
    echo "[$(date -Is)] >>> arm=$arm grid=M20"
    R443_GRID=M20 R443_NS=-s1 bash "$DIR/run_arm_r443.sh" "$arm"
    echo "[$(date -Is)] <<< arm=$arm rc=$?"
  done
  echo "[$(date -Is)] R443 run_all_s1 done"
} 2>&1 | tee -a "$LOG"
