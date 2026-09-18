#!/usr/bin/env bash
# R552 v2 顺序执行器 (v1 因本侧驱动器漏复制 cases-r521.json ⇒ 0/0 VOID, 见 prereg-r552-v2.json "supersedes")
# 窗号 v2 = b0 w30-32 / b1 w33-35 / b2 w36-38; 运行树 /tmp/r552v2_b{0,1,2}; 阈值与判据**不变**。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
PREREG=$REPO/eval/rover/r552/prereg-r552-v2.json
echo "[$(date -Is)] R552v2 顺序起臂: b0(w30-32,p49071) -> b1(w33-35,p49081) -> b2(w36-38,p49091)"
MAXPROBE=0 D=/tmp/r552v2_b0 PORT=49071 WIN0=30 TAG=R552b0 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b0 rc=$?"
MAXPROBE=1 D=/tmp/r552v2_b1 PORT=49081 WIN0=33 TAG=R552b1 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b1 rc=$?"
MAXPROBE=2 D=/tmp/r552v2_b2 PORT=49091 WIN0=36 TAG=R552b2 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b2 rc=$?"
echo "[$(date -Is)] R552v2 三臂结束"
