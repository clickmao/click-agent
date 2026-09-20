#!/usr/bin/env bash
# R595 后处理重跑（**只重跑后处理，不重测**）—— 器具自捕 #1 的修后行使。
# 缺陷: 派生时漏拷 `cases-r521.json`（sha 270128eb…）⇒ 判分器秒崩 ⇒ 12 跑次 cases.txt 全是
#       Traceback ⇒ kpi 读到 0/0、C1 在 0/0 上恒真（D=0 空心绿）、铁律 11 前置器 rc=1 同源。
# 处置: ① v1 证据已归档 (archive-v1-casesmissing/)，不删不翻案；② 补齐冻结用例集（同源 sha 已比对）；
#       ③ 只重跑判分与汇总（快照/近端读数逐字节不动）；④ 新读数落 v2 命名空间。
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
PDIR=eval/rover/r595
D="$HOME/.agentframework/harness/runs/r595"
SC="$PWD/$PDIR/cases/run_cases_r521.py"
SCRATCH=$(mktemp -d /tmp/r595-judge-XXXXXX)
export AGENTFRAMEWORK_GRADE_TIMEOUT=${GRADE_TMO:-10}
echo "[v2 判分] 开始 $(date +%H:%M:%S) scratch=$SCRATCH"
for W in w169 w170 w171; do
  for S in codex agentD-r1 agentD-r2 agentD-r3; do
    SRC="$PDIR/snapshots/$W/$S/g1"
    G="$D/$W/$S/g1"
    [ -d "$SRC" ] || { echo "  !! 缺快照 $SRC"; continue; }
    rm -rf "$SCRATCH/$W-$S"; mkdir -p "$SCRATCH/$W-$S"
    cp -a "$SRC/." "$SCRATCH/$W-$S/"
    t0=$(date +%s)
    ( cd "$SCRATCH/$W-$S" && env -u AGENTFRAMEWORK_PY_RUN python3 -I -B "$SC" ) > "$G/cases.txt" 2>&1
    rc=$?
    t1=$(date +%s)
    line=$(grep -o 'R521_CASES [0-9]*/[0-9]*' "$G/cases.txt" | tail -1)
    echo "  $W/$S rc=$rc ${line:-无汇总}  judge=$((t1-t0))s"
  done
done
rm -rf "$SCRATCH"
echo "[v2 判分] 完成 $(date +%H:%M:%S)"
# 汇总（后处理）
python3 "$PDIR/kpi_r595.py" --D "$D" --pd "$PDIR" 2>&1 | tail -3
python3 "$PDIR/pool_taskface_r595.py" 2>&1 | tail -8
python3 eval/rover/r507pre/exec_precondition.py --round r595 --out "$D/precond-r595-v2.json" 2>&1 | tail -6
echo "[v2] rc 落盘完成"
