#!/usr/bin/env bash
# R497: 全量测试**屏蔽 R497 新测试类**各跑 2 次 ⇒ 判定 TelemetryPendingTests 波动是否与本轮新增类相关
set -u
export DOTNET_ROOT="$HOME/.dotnet"
DT="$HOME/.dotnet/dotnet"
cd /home/agentuser/AgentFramework || exit 1
T=src/agent.tests/agentframework.tests.csproj
for i in 1 2; do
  env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR "$DT" test "$T" -c Debug --nologo \
    --filter "FullyQualifiedName!~R497FingerprintAndSynonymTests" > "/tmp/r497_tests_noR497_$i.log" 2>&1
  echo "[no-R497 run$i] rc=$? $(grep -E '^(Passed!|Failed!)' "/tmp/r497_tests_noR497_$i.log" | head -1)"
  grep "  Failed " "/tmp/r497_tests_noR497_$i.log" | head -3
done
echo "done $(date +%H:%M:%S)"
