#!/usr/bin/env bash
# R452 三臂编排: RC(网格正控) → RP(真实·生产行为) → RJ(真实·判官强制)
set -u
ROOT=/home/agentuser/AgentFramework
DIR=$ROOT/eval/rover/r452
cd "$ROOT"
echo "=== [0] 内存/占用侦察 ==="
free -m | head -2
pgrep -a llama-server || echo "llama-server: 无"
dotnet build-server shutdown >/dev/null 2>&1 || true
pkill -f "[M]SBuild.dll" 2>/dev/null || true
sleep 2
free -m | head -2 | tail -1
cp -f "$ROOT/eval/rover/r450/grid/task-M20.json" "$DIR/grid/task-M20.json"
echo "M20 sha: $(sha256sum "$DIR/grid/task-M20.json" | cut -d' ' -f1)"

echo "=== [1] RC 臂 (M20 网格正控, 前置门开) ==="
R452_GRID=M20 R452_NS=-c1 R452_PREFILTER=1 bash "$DIR/run_arm_r452.sh" RC 48410 48412
echo "RC rc=$?"

echo "=== [2] RP 臂 (真实语料, 前置门开=生产行为) ==="
R452_GRID=REAL R452_NS=-p1 R452_PREFILTER=1 bash "$DIR/run_arm_r452.sh" RP 48420 48422
echo "RP rc=$?"

echo "=== [3] RJ 臂 (真实语料, 前置门关=判官强制) ==="
R452_GRID=REAL R452_NS=-j1 R452_PREFILTER=0 bash "$DIR/run_arm_r452.sh" RJ 48430 48432
echo "RJ rc=$?"

echo "=== [4] 收尾 ==="
pgrep -a llama-server || echo "llama-server: 已回收"
free -m | head -2 | tail -1
ls -la "$DIR" | head -20
