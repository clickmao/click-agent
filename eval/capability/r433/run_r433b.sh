#!/bin/bash
# R433 第二段: 判别力负控（族专属注入, 本地不调 LLM）+ 臂1 复跑（可复现性）
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PROBE_AGENT_BIN=/tmp/pub_r433/agenthost
SNAP=eval/capability/r433/telemetry
run() {
  local label=$1; shift
  echo "=== [$label] start $(date +%H:%M:%S) ==="
  python3 eval/probe/run_probe.py "$@" --solve-timeout 300 2>&1 | tail -12
  if [ -f data/telemetry/host.jsonl ]; then cp data/telemetry/host.jsonl "$SNAP/host-$label.jsonl"; fi
  echo "=== [$label] end $(date +%H:%M:%S) ==="
}
run r433ctl-topo --families topo_min --kind both --n 3 --seed 20260913 --solver mutation:topo_dfs --tag=r433ctl-topo
run r433ctl-vm   --families vm_run   --kind both --n 3 --seed 20260913 --solver mutation:vm_noerr  --tag=r433ctl-vm
run r433ctl-json --families json_mini --kind both --n 3 --seed 20260913 --solver mutation:json_loose --tag=r433ctl-json
run r433m6r2     --tasks data/probe/taskset-m6.json --solver agent --tag=r433m6r2
echo "=== ALL DONE2 $(date +%H:%M:%S) ==="
