#!/bin/bash
# R433 严格执行文档跑测链: exp14 探针复跑 (真机 agent) + 判别力负控 + 遥测快照
set -u
cd /home/agentuser/AgentFramework
export DOTNET_ROOT="$HOME/.dotnet"
export PROBE_AGENT_BIN=/tmp/pub_r433/agenthost
SNAP=eval/capability/r433/telemetry
run() {
  local label=$1; shift
  echo "=== [$label] start $(date +%H:%M:%S) ==="
  python3 eval/probe/run_probe.py "$@" --solve-timeout 300 2>&1 | tail -30
  if [ -f data/telemetry/host.jsonl ]; then
    cp data/telemetry/host.jsonl "$SNAP/host-$label.jsonl"
    echo "telemetry-snap[$label] lines=$(wc -l < "$SNAP/host-$label.jsonl") llm_call=$(grep -c llm_call "$SNAP/host-$label.jsonl" || true)"
  fi
  echo "=== [$label] end $(date +%H:%M:%S) ==="
}
run r433m6    --tasks data/probe/taskset-m6.json --solver agent --tag=r433m6
run r433as    --families topo_min,vm_run,json_mini --kind both --n 3 --seed 20260913 --solver agent --tag=r433as --dump-tasks /tmp/r433_taskset_as.json
run r433asctl --tasks /tmp/r433_taskset_as.json --solver mutation:json_loose --tag=r433asctl
echo "=== ALL DONE $(date +%H:%M:%S) ==="
