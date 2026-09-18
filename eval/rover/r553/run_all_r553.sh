#!/usr/bin/env bash
# R553 顺序执行器: b0(剂量0, w60-62, p49201) -> b1(剂量1, w63-65, p49211) -> b2(剂量2, w66-68, p49221)
# 单变量与 R552 逐字同轴同二进制; 唯一器具差异 = 每窗起臂前 起手闸 C(契约面健康预检)。
# 预注册 prereg-r553.json 必须已落盘(各臂脚本内第 0 步机检 ⇒ 先写后跑)。
set -uo pipefail
REPO=/home/agentuser/AgentFramework
cd "$REPO" || exit 3
PREREG=$REPO/eval/rover/r553/prereg-r553.json
echo "[$(date -Is)] R553 顺序起臂: b0(w60-62,p49201) -> b1(w63-65,p49211) -> b2(w66-68,p49221)"
MAXPROBE=0 D=/tmp/r553v1_b0 PORT=49201 WIN0=60 TAG=R553b0 PREREG=$PREREG bash "$REPO/eval/rover/r553/run_r553.sh"; echo "ARM b0 rc=$?"
MAXPROBE=1 D=/tmp/r553v1_b1 PORT=49211 WIN0=63 TAG=R553b1 PREREG=$PREREG bash "$REPO/eval/rover/r553/run_r553.sh"; echo "ARM b1 rc=$?"
MAXPROBE=2 D=/tmp/r553v1_b2 PORT=49221 WIN0=66 TAG=R553b2 PREREG=$PREREG bash "$REPO/eval/rover/r553/run_r553.sh"; echo "ARM b2 rc=$?"
echo "[$(date -Is)] R553 三臂结束"
