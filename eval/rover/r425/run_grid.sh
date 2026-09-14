#!/usr/bin/env bash
# R425 网格执行器 — 顺序跑 (k × 臂) 防 CPU/内存争用; 产物带 k 与批次后缀
# 用法: bash run_grid.sh [批次后缀 如 -b2] [role.rbin 绝对路径]
set -u
SFX=${1:--b2}
ROLE=${2:-/home/agentuser/AgentFramework/skeptic.rbin}
DIR=/home/agentuser/AgentFramework/eval/rover/r425
cd "$DIR"
export R425_NS="$SFX"
echo "[role] $ROLE sha256=$(sha256sum "$ROLE" | cut -d' ' -f1) bytes=$(stat -c %s "$ROLE")"
fail=0
for K in 1 2 4 6 8; do
  S=$((47900 + K * 10)); A=$((47901 + K * 10))
  for ARM in A B; do
    echo "===== R425 grid$SFX k=$K arm=$ARM $(date -Is) ====="
    bash "$DIR/run_arm.sh" "$ARM" "$K" "$S" "$A" "$ROLE" || { echo "[warn] arm=$ARM k=$K rc=$?"; fail=1; }
  done
done
echo "===== R425 负控臂 B\' (k=6, 模型缺) $(date -Is) ====="
bash "$DIR/run_arm.sh" BP 6 47936 47937 "$ROLE" || { echo "[warn] arm=BP rc=$?"; fail=1; }
echo "===== R425 grid$SFX done fail=$fail $(date -Is) ====="
exit $fail
