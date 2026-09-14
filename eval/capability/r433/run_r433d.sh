#!/bin/bash
# R433 最终权威臂: 修复后仪器 (0.25s 窗口) + 同 sha 冻结题集
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PROBE_AGENT_BIN=/tmp/pub_r433/agenthost
mkdir -p eval/capability/r433/telemetry
python3 eval/probe/run_probe.py --tasks data/probe/taskset-m6.json --solver agent --tag=r433m6fix2 --solve-timeout 300 2>&1 | tail -20
cp data/telemetry/host.jsonl eval/capability/r433/telemetry/host-r433m6fix2.jsonl
echo "=== FIX2 DONE $(date +%H:%M:%S) ==="
