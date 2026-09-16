#!/usr/bin/env bash
set -u
export DOTNET_ROOT="$HOME/.dotnet"
cd /home/agentuser/AgentFramework
LOG=/tmp/r501_test_focus.log
"$HOME/.dotnet/dotnet" test src/agent.tests/agentframework.tests.csproj -c Release --nologo \
  --filter "FullyQualifiedName~LocalTurnGateTests|FullyQualifiedName~FrontendAskSameConnTests" 2>&1 | tee "$LOG" | tail -12
grep -E "^(Passed|Failed)!" "$LOG" | tail -2
