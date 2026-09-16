#!/usr/bin/env bash
# FrontendAskSameConnTests 抖动取证: 同一二进制连跑 3 次 (单类), 记录逐次结果
set -u
export DOTNET_ROOT="$HOME/.dotnet"
cd /home/agentuser/AgentFramework
for i in 1 2 3; do
  "$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release --nologo \
    --filter "FullyQualifiedName~FrontendAskSameConnTests" 2>&1 | grep -E "^(Passed|Failed)!" | tail -1 | sed "s/^/run$i: /"
done
