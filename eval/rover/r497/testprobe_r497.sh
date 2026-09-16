#!/usr/bin/env bash
# R497: 两/三类定向探针 —— 判定 TelemetryPendingTests 波动是否由 R497 测试类直接引起 (计时扰动 vs 语义)
set -u
export DOTNET_ROOT="$HOME/.dotnet"
DT="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework || exit 1
T=src/agent.tests/agentframework.tests.csproj
echo "--- A) TelemetryPendingTests + R497 同跑 x3"
for i in 1 2 3; do
  env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DT" test "$T" -c Debug --nologo \
    --filter "FullyQualifiedName~TelemetryPendingTests|FullyQualifiedName~R497Fingerprint" > "/tmp/r497_pairA_$i.log" 2>&1
  echo "  run$i rc=$? $(grep -E '^(Passed!|Failed!)' "/tmp/r497_pairA_$i.log" | head -1)"
done
echo "--- B) TelemetryPendingTests 单跑 x3 (基线)"
for i in 1 2 3; do
  env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DT" test "$T" -c Debug --nologo \
    --filter "FullyQualifiedName~TelemetryPendingTests" > "/tmp/r497_pairB_$i.log" 2>&1
  echo "  run$i rc=$? $(grep -E '^(Passed!|Failed!)' "/tmp/r497_pairB_$i.log" | head -1)"
done
echo "done $(date +%H:%M:%S)"
