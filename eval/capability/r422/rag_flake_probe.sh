#!/usr/bin/env bash
# R422 附带分诊: RagPruneAmortizeTests 的**进程内随机性**取证 (修复前/后各跑 N 次, 记录通过模式)
cd /home/agentuser/AgentFramework || exit 1
export DOTNET_ROOT="$HOME/.dotnet"
N="${1:-6}"
LOG="${2:-/tmp/r422_rag_flake.log}"
: > "$LOG"
for i in $(seq 1 "$N"); do
  out=$(env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR \
    "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release \
    --filter "FullyQualifiedName~RagPruneAmortizeTests" 2>&1 | grep -E 'Failed!|Passed!' | tail -1)
  echo "run$i: $out" | tee -a "$LOG"
done
echo "---- pattern ----"
grep -c 'Passed!' "$LOG"; grep -c 'Failed!' "$LOG"
