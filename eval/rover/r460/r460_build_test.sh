#!/usr/bin/env bash
# R460: 单测 (承接/精炼/菜单) —— 真名过滤 + 断言执行数 > 0 (防假绿)
set -uo pipefail
export DOTNET_ROOT="$HOME/.dotnet"
D="$HOME/.dotnet/dotnet"
A=/home/agentuser/AgentFramework
cd "$A"
"$D" build src/agent.tests/agentframework.tests.csproj -c Release 2>&1 | tail -4
echo "=== 过滤单测 (真名) ==="
"$D" test src/agent.tests/agentframework.tests.csproj -c Release --no-build \
  --filter "FullyQualifiedName~ContinuationBriefTests" 2>&1 | tail -12
