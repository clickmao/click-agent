#!/usr/bin/env bash
# R419 真机臂重跑 (判定器坏字节缺陷修复后; 控制臂沿用同批)
set -uo pipefail
cd /home/agentuser/AgentFramework || exit 3
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"; export PATH="$DOTNET_ROOT:$PATH"
NS=b09141437
python3 -u eval/probe/run_probe.py --kind program --families json_mini --n 3 --seed 419 \
    --turns 2 --correction onfail --solver agent --tag "r419bagent-$NS" \
    > "eval/rover/r419/logs/r419bagent-$NS.log" 2>&1
echo "STEP_EXIT_r419bagent=$?"
tail -4 "eval/rover/r419/logs/r419bagent-$NS.log"
echo "=== 多轮表 ==="
python3 eval/probe/process_metrics.py --multiturn --report > "eval/rover/r419/logs/process_metrics-$NS.out" 2>&1
cat "eval/rover/r419/logs/process_metrics-$NS.out"
echo "=== 判据检查 ==="
python3 eval/rover/r419/check_multiturn.py --ns "$NS" | tee "eval/rover/r419/logs/check-$NS.out"
echo "AGENT_RERUN_DONE=1"
