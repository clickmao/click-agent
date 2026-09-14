#!/bin/bash
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PROBE_AGENT_BIN=/tmp/pub_r433/agenthost
mkdir -p eval/capability/r433/telemetry
python3 eval/probe/run_probe.py --tasks data/probe/taskset-m6.json --solver agent --tag=r433m6fix --solve-timeout 300 2>&1 | tail -20
cp data/telemetry/host.jsonl eval/capability/r433/telemetry/host-r433m6fix.jsonl
echo "=== FIX ARM DONE $(date +%H:%M:%S) ==="
