#!/usr/bin/env bash
# R426 批次编排 — 顺序跑 7 格 (单进程串行, 不与其它作业并行)
# 用法: R426_NS=-r426b1 bash run_grid.sh [role.rbin]
set -u
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r426
export R426_NS=${R426_NS:--r426b1}
ROLE=${1:-$ROOT/skeptic.rbin}
export AGENTFRAMEWORK_HOST_BIN=${AGENTFRAMEWORK_HOST_BIN:-/tmp/aot-r426b/agenthost}
echo "[grid] NS=$R426_NS role=$ROLE sha256=$(sha256sum "$ROLE" | cut -d' ' -f1) bytes=$(stat -c %s "$ROLE")"
echo "[grid] host=$AGENTFRAMEWORK_HOST_BIN sha256=$(sha256sum "$AGENTFRAMEWORK_HOST_BIN" | cut -d' ' -f1)"
fail=0
for spec in A:6 C:6 B:6 D:6 A:8 C:8 B:8; do
  ARM=${spec%%:*}; K=${spec##*:}
  echo "=== [$(date +%T)] arm=$ARM k=$K ==="
  bash "$DIR/run_arm.sh" "$ARM" "$K" 47900 47901 "$ROLE" || { echo "[warn] arm=$ARM k=$K rc=$?"; fail=1; }
done
echo "[grid] done fail=$fail at $(date +%T)"
