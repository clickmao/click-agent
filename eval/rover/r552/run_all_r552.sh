#!/usr/bin/env bash
# R552 顺序执行器: 三臂(MAX_PROBE_REPAIR ∈ {0,1,2}) 依次跑; 各臂 **独立适配器/独立端口/独立 session**。
# 增量落盘: 每臂结束即写 <D>/summary.json ⇒ 中途中断也已保留已完成臂的读数(不末尾一次写盘)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
echo "[$(date -Is)] R552 顺序起臂: b0(轴0,w20-22,p49041) -> b1(轴1,w23-25,p49051) -> b2(轴2,w26-28,p49061)"
MAXPROBE=0 D=/tmp/r552_b0 PORT=49041 WIN0=20 TAG=R552b0 bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b0 rc=$?"
MAXPROBE=1 D=/tmp/r552_b1 PORT=49051 WIN0=23 TAG=R552b1 bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b1 rc=$?"
MAXPROBE=2 D=/tmp/r552_b2 PORT=49061 WIN0=26 TAG=R552b2 bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b2 rc=$?"
echo "[$(date -Is)] R552 三臂结束"
