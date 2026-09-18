#!/usr/bin/env bash
# R552 sup1 追加窗执行器 (先写后跑: prereg-r552-sup1.json 已在盘)
# 窗号 sup1 = b0 w39-41 / b1 w43-45 / b2 w46-48; 运行树 /tmp/r552v2_b{0,1,2} (与 v2 同树, 追加窗); 阈值不变。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
PREREG=$REPO/eval/rover/r552/prereg-r552-sup1.json
echo "[$(date -Is)] R552sup1 追加窗: b0(w39-41,p49101) -> b1(w43-45,p49111) -> b2(w46-48,p49121)"
MAXPROBE=0 D=/tmp/r552v2_b0 PORT=49101 WIN0=39 TAG=R552b0 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b0 rc=$?"
MAXPROBE=1 D=/tmp/r552v2_b1 PORT=49111 WIN0=43 TAG=R552b1 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b1 rc=$?"
MAXPROBE=2 D=/tmp/r552v2_b2 PORT=49121 WIN0=46 TAG=R552b2 PREREG=$PREREG bash "$REPO/eval/rover/r552/run_r552.sh"; echo "ARM b2 rc=$?"
echo "[$(date -Is)] R552sup1 追加窗结束"
