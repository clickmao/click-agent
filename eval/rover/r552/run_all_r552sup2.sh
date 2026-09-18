#!/usr/bin/env bash
# R552 sup2 补齐声明 n 执行器 (先写后跑: prereg-r552-sup2.json 已在盘)
# 窗号 sup2 = b0 w49-51 / b1 w52-54 / b2 w55-57; 阈值/判据不变; summary 件名已参数化(R552 器具自捕缺陷修复)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
PREREG=$REPO/eval/rover/r552/prereg-r552-sup2.json
echo "[$(date -Is)] R552sup2 补齐声明 n: b0(w49-51,p49131) -> b1(w52-54,p49141) -> b2(w55-57,p49151)"
MAXPROBE=0 D=/tmp/r552v2_b0 PORT=49131 WIN0=49 TAG=R552b0 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b0 rc=$?"
MAXPROBE=1 D=/tmp/r552v2_b1 PORT=49141 WIN0=52 TAG=R552b1 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b1 rc=$?"
MAXPROBE=2 D=/tmp/r552v2_b2 PORT=49151 WIN0=55 TAG=R552b2 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b2 rc=$?"
echo "[$(date -Is)] R552sup2 结束"
